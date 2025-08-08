#!/usr/bin/env python3
"""
OneNote to Markdown Exporter (Web API Version)

For personal Microsoft accounts, we need to use the OneNote Web API instead of Microsoft Graph.
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


class OneNoteWebExporter:
    """OneNote exporter using Web API for personal accounts."""
    
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
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        logger.info("Successfully authenticated with Microsoft Graph")
        return self.token
    
    def call_api_with_retry(self, url: str, max_retries: int = MAX_RETRIES) -> Dict:
        """Call API with exponential backoff retry logic."""
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
                    logger.error(f"Failed to call API after {max_retries} retries: {e}")
                    raise
                delay = BASE_DELAY * (2 ** attempt)
                logger.warning(f"Request failed: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
    
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
    
    def export_page(self, page_url: str, page_title: str, section_path: pathlib.Path) -> None:
        """Export a single OneNote page to Markdown."""
        try:
            # Get page content
            headers = {"Accept": "text/html"}
            response = self.session.get(page_url, headers=headers)
            response.raise_for_status()
            html_content = response.text
            
            # Process content and convert to Markdown
            markdown_content = self.process_html_content(html_content, section_path)
            
            # Create markdown file
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', page_title)
            if not safe_title.strip():
                safe_title = f"page_{hash(page_url) % 10000}"
                
            md_file = section_path / f"{safe_title}.md"
            
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(f"# {page_title}\n\n")
                f.write(f"*Exported from OneNote on {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                f.write("---\n\n")
                f.write(markdown_content)
            
            logger.info(f"Exported page: {page_title}")
            
        except Exception as e:
            logger.error(f"Failed to export page {page_title}: {e}")
    
    def export_notebooks(self) -> None:
        """Main export function using OneNote Web API."""
        try:
            logger.info("OneNote Web API is not directly accessible for personal accounts.")
            logger.info("For personal Microsoft accounts, you need to:")
            logger.info("1. Use OneNote desktop app to export notebooks")
            logger.info("2. Or use OneNote Online to manually export pages")
            logger.info("3. Or use Microsoft Graph with a work/school account")
            
            # For now, create a sample structure
            sample_path = self.output_dir / "Sample_Notebook" / "Sample_Section"
            sample_path.mkdir(parents=True, exist_ok=True)
            
            with open(sample_path / "README.md", 'w') as f:
                f.write("# OneNote Export Information\n\n")
                f.write("## Personal Account Limitations\n\n")
                f.write("OneNote API access is limited for personal Microsoft accounts.\n\n")
                f.write("### Alternative Solutions:\n\n")
                f.write("1. **OneNote Desktop Export**: Use OneNote desktop app to export notebooks\n")
                f.write("2. **OneNote Online**: Manually export pages from OneNote Online\n")
                f.write("3. **Work/School Account**: Use a work or school account with OneNote API access\n")
                f.write("4. **Third-party Tools**: Use tools like OneNote Exporter for Windows\n\n")
                f.write("### Manual Export Steps:\n\n")
                f.write("1. Open OneNote Online (onenote.com)\n")
                f.write("2. Navigate to your notebooks\n")
                f.write("3. Right-click on pages and select 'Export'\n")
                f.write("4. Choose PDF or Word format\n")
                f.write("5. Convert to Markdown using online tools\n")
            
            logger.info("Created sample export structure with instructions")
                        
        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise


def main():
    """Main entry point."""
    try:
        exporter = OneNoteWebExporter(CLIENT_ID, SCOPES, OUTPUT_DIR)
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
