#!/usr/bin/env python3
"""
OneNote to Markdown Exporter

A CLI tool that exports OneNote notebooks to Markdown files with embedded images.
Uses Microsoft Graph API with device code flow authentication.
"""

import os
import sys
import json
import requests
import pathlib
import time
import re
import logging
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional, Tuple
from msal import PublicClientApplication
from html2text import HTML2Text

# Configuration
CLIENT_ID = os.getenv("ONENOTE_CLIENT_ID", "YOUR_CLIENT_ID_HERE")  # Set via environment variable or replace with your Azure AD app registration client ID
SCOPES = ["Notes.Read", "User.Read"]
OUTPUT_DIR = pathlib.Path("output")
MAX_RETRIES = 3
BASE_DELAY = 1  # seconds

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('onenote_export.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class OneNoteExporter:
    """Main class for exporting OneNote content to Markdown."""
    
    def __init__(self, client_id: str, scopes: List[str], output_dir: pathlib.Path):
        self.client_id = client_id
        self.scopes = scopes
        self.output_dir = output_dir
        self.token = None
        self.session = requests.Session()
        
    def get_token(self) -> str:
        """Authenticate using device code flow and return access token."""
        if self.token:
            return self.token
            
        # Use the correct authority for personal accounts
        app = PublicClientApplication(self.client_id, authority="https://login.microsoftonline.com/consumers")
        flow = app.initiate_device_flow(scopes=self.scopes)
        
        if not flow.get("user_code"):
            raise RuntimeError(f"Device code flow failed: {flow}")
            
        logger.info("Please authenticate using the device code flow:")
        print(flow["message"])
        
        result = app.acquire_token_by_device_flow(flow)
        
        if "access_token" not in result:
            raise RuntimeError(f"Failed to acquire token: {result.get('error_description', 'Unknown error')}")
            
        self.token = result["access_token"]
        # Set the correct headers for Microsoft Graph API
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
        logger.info("Successfully authenticated with Microsoft Graph")
        return self.token
    
    def call_graph_with_retry(self, url: str, max_retries: int = MAX_RETRIES) -> Dict:
        """Call Microsoft Graph API with exponential backoff retry logic."""
        for attempt in range(max_retries + 1):
            try:
                response = self.session.get(url)
                
                if response.status_code == 429:  # Rate limit
                    retry_after = int(response.headers.get('Retry-After', BASE_DELAY * (2 ** attempt)))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                    
                elif response.status_code >= 500:  # Server error
                    delay = BASE_DELAY * (2 ** attempt)
                    logger.warning(f"Server error {response.status_code}. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                    
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt == max_retries:
                    logger.error(f"Failed to call Graph API after {max_retries} retries: {e}")
                    raise
                delay = BASE_DELAY * (2 ** attempt)
                logger.warning(f"Request failed: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
    
    def call_graph_paginated(self, url: str) -> List[Dict]:
        """Call Microsoft Graph API and handle pagination."""
        data = self.call_graph_with_retry(url)
        results = data.get("value", [])
        
        # Handle pagination
        while "@odata.nextLink" in data:
            logger.info("Fetching next page...")
            data = self.call_graph_with_retry(data["@odata.nextLink"])
            results.extend(data.get("value", []))
            
        return results
    
    def download_media(self, media_url: str, output_path: pathlib.Path) -> str:
        """Download media file and return local filename."""
        try:
            response = self.session.get(media_url, stream=True)
            response.raise_for_status()
            
            # Extract filename from URL or use content-type
            parsed_url = urlparse(media_url)
            filename = os.path.basename(parsed_url.path)
            
            if not filename or '.' not in filename:
                content_type = response.headers.get('content-type', '')
                if 'image/' in content_type:
                    ext = content_type.split('/')[-1]
                    filename = f"image_{hash(media_url) % 10000}.{ext}"
                else:
                    filename = f"media_{hash(media_url) % 10000}.bin"
            
            file_path = output_path / filename
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            logger.info(f"Downloaded media: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Failed to download media {media_url}: {e}")
            return ""
    
    def process_html_content(self, html: str, output_path: pathlib.Path) -> str:
        """Process HTML content, download media, and convert to Markdown."""
        # Download embedded media
        media_files = {}
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
        
        for match in re.finditer(img_pattern, html):
            img_url = match.group(1)
            if img_url.startswith('http'):
                filename = self.download_media(img_url, output_path)
                if filename:
                    media_files[img_url] = filename
                    # Replace URL with local filename
                    html = html.replace(img_url, filename)
        
        # Convert HTML to Markdown
        h2m = HTML2Text()
        h2m.body_width = 0  # Don't wrap lines
        h2m.ignore_images = False
        h2m.ignore_emphasis = False
        h2m.ignore_links = False
        
        markdown = h2m.handle(html)
        
        return markdown
    
    def export_page(self, page: Dict, section_path: pathlib.Path) -> None:
        """Export a single OneNote page to Markdown."""
        try:
            # Get page content
            page_id = page['id']
            content_url = f"https://graph.microsoft.com/v1.0/me/onenote/pages/{page_id}/content"
            
            headers = {"Accept": "text/html"}
            response = self.session.get(content_url, headers=headers)
            response.raise_for_status()
            html_content = response.text
            
            # Process content and convert to Markdown
            markdown_content = self.process_html_content(html_content, section_path)
            
            # Create markdown file
            page_title = page.get("title", "Untitled")
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', page_title)
            if not safe_title.strip():
                safe_title = f"page_{page_id[:8]}"
                
            md_file = section_path / f"{safe_title}.md"
            
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(f"# {page_title}\n\n")
                f.write(f"*Exported from OneNote on {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                f.write("---\n\n")
                f.write(markdown_content)
            
            logger.info(f"Exported page: {page_title}")
            
        except Exception as e:
            logger.error(f"Failed to export page {page.get('title', 'Unknown')}: {e}")
    
    def export_notebooks(self) -> None:
        """Main export function that walks through all notebooks, sections, and pages."""
        try:
            # Get all notebooks using the correct endpoint for personal accounts
            logger.info("Fetching notebooks...")
            notebooks = self.call_graph_paginated("https://graph.microsoft.com/v1.0/me/onenote/notebooks")
            logger.info(f"Found {len(notebooks)} notebooks")
            
            for notebook in notebooks:
                notebook_name = notebook.get("displayName", "Untitled")
                safe_notebook_name = re.sub(r'[<>:"/\\|?*]', '_', notebook_name)
                notebook_path = self.output_dir / safe_notebook_name
                notebook_path.mkdir(parents=True, exist_ok=True)
                
                logger.info(f"Processing notebook: {notebook_name}")
                
                # Get sections for this notebook using the correct endpoint
                sections_url = f"https://graph.microsoft.com/v1.0/me/onenote/notebooks/{notebook['id']}/sections"
                sections = self.call_graph_paginated(sections_url)
                logger.info(f"Found {len(sections)} sections in {notebook_name}")
                
                for section in sections:
                    section_name = section.get("displayName", "Untitled")
                    safe_section_name = re.sub(r'[<>:"/\\|?*]', '_', section_name)
                    section_path = notebook_path / safe_section_name
                    section_path.mkdir(parents=True, exist_ok=True)
                    
                    logger.info(f"Processing section: {section_name}")
                    
                    # Get pages for this section using the correct endpoint
                    pages_url = f"https://graph.microsoft.com/v1.0/me/onenote/sections/{section['id']}/pages"
                    pages = self.call_graph_paginated(pages_url)
                    logger.info(f"Found {len(pages)} pages in {section_name}")
                    
                    for page in pages:
                        self.export_page(page, section_path)
                        
        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise


def main():
    """Main entry point."""
    if CLIENT_ID == "YOUR_CLIENT_ID_HERE":
        print("ERROR: Please set ONENOTE_CLIENT_ID environment variable or replace YOUR_CLIENT_ID_HERE with your actual Azure AD application client ID.")
        print("\nTo get a client ID:")
        print("1. Go to https://portal.azure.com")
        print("2. Navigate to Azure Active Directory > App registrations")
        print("3. Create a new registration or use an existing one")
        print("4. Copy the Application (client) ID")
        print("5. Add the following API permissions:")
        print("   - Microsoft Graph > Delegated > Notes.Read.All")
        print("6. Set ONENOTE_CLIENT_ID environment variable to this value")
        sys.exit(1)
    
    try:
        exporter = OneNoteExporter(CLIENT_ID, SCOPES, OUTPUT_DIR)
        exporter.get_token()
        exporter.export_notebooks()
        logger.info("Export completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Export interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Export failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 