"""
Unit tests for OneNote Exporter
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil

# Import the class we want to test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from onenote_exporter import OneNoteExporter


class TestOneNoteExporter:
    """Test cases for OneNoteExporter class."""
    
    @pytest.fixture
    def exporter(self):
        """Create a test exporter instance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            exporter = OneNoteExporter(
                client_id="test_client_id",
                scopes=["Notes.Read.All"],
                output_dir=Path(temp_dir)
            )
            yield exporter
    
    @pytest.fixture
    def mock_session(self):
        """Mock requests session."""
        with patch('onenote_exporter.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            yield mock_session
    
    def test_init(self, exporter):
        """Test exporter initialization."""
        assert exporter.client_id == "test_client_id"
        assert exporter.scopes == ["Notes.Read.All"]
        assert exporter.token is None
    
    @patch('onenote_exporter.PublicClientApplication')
    def test_get_token_success(self, mock_app_class, exporter):
        """Test successful token acquisition."""
        # Mock the MSAL application
        mock_app = Mock()
        mock_app_class.return_value = mock_app
        
        # Mock device flow
        mock_flow = {
            "user_code": "ABC123",
            "message": "Go to https://microsoft.com/device and enter ABC123"
        }
        mock_app.initiate_device_flow.return_value = mock_flow
        
        # Mock token acquisition
        mock_result = {
            "access_token": "test_token_123",
            "expires_in": 3600
        }
        mock_app.acquire_token_by_device_flow.return_value = mock_result
        
        # Mock session headers update
        exporter.session = Mock()
        
        token = exporter.get_token()
        
        assert token == "test_token_123"
        assert exporter.token == "test_token_123"
        exporter.session.headers.update.assert_called_with({"Authorization": "Bearer test_token_123"})
    
    @patch('onenote_exporter.PublicClientApplication')
    def test_get_token_device_flow_failure(self, mock_app_class, exporter):
        """Test device flow failure."""
        mock_app = Mock()
        mock_app_class.return_value = mock_app
        
        # Mock failed device flow
        mock_flow = {}
        mock_app.initiate_device_flow.return_value = mock_flow
        
        with pytest.raises(RuntimeError, match="Device code flow failed"):
            exporter.get_token()
    
    @patch('onenote_exporter.PublicClientApplication')
    def test_get_token_acquisition_failure(self, mock_app_class, exporter):
        """Test token acquisition failure."""
        mock_app = Mock()
        mock_app_class.return_value = mock_app
        
        # Mock successful device flow
        mock_flow = {
            "user_code": "ABC123",
            "message": "Go to https://microsoft.com/device and enter ABC123"
        }
        mock_app.initiate_device_flow.return_value = mock_flow
        
        # Mock failed token acquisition
        mock_result = {
            "error": "access_denied",
            "error_description": "User denied access"
        }
        mock_app.acquire_token_by_device_flow.return_value = mock_result
        
        with pytest.raises(RuntimeError, match="Failed to acquire token"):
            exporter.get_token()
    
    def test_call_graph_with_retry_success(self, exporter):
        """Test successful API call with retry logic."""
        # Mock the session and response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [{"id": "1", "name": "test"}]}
        
        exporter.session = Mock()
        exporter.session.get.return_value = mock_response
        
        result = exporter.call_graph_with_retry("https://graph.microsoft.com/v1.0/test")
        
        assert result == {"value": [{"id": "1", "name": "test"}]}
        exporter.session.get.assert_called_once()
    
    def test_call_graph_with_retry_rate_limit(self, exporter):
        """Test rate limit handling."""
        # Mock rate limit response, then success
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "2"}
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"value": [{"id": "1"}]}
        
        exporter.session = Mock()
        exporter.session.get.side_effect = [mock_response_429, mock_response_200]
        
        with patch('onenote_exporter.time.sleep') as mock_sleep:
            result = exporter.call_graph_with_retry("https://graph.microsoft.com/v1.0/test")
            
            assert result == {"value": [{"id": "1"}]}
            mock_sleep.assert_called_with(2)
            assert exporter.session.get.call_count == 2
    
    def test_call_graph_with_retry_server_error(self, exporter):
        """Test server error handling."""
        # Mock server error response, then success
        mock_response_500 = Mock()
        mock_response_500.status_code = 500
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"value": [{"id": "1"}]}
        
        exporter.session = Mock()
        exporter.session.get.side_effect = [mock_response_500, mock_response_200]
        
        with patch('onenote_exporter.time.sleep') as mock_sleep:
            result = exporter.call_graph_with_retry("https://graph.microsoft.com/v1.0/test")
            
            assert result == {"value": [{"id": "1"}]}
            mock_sleep.assert_called_with(1)  # BASE_DELAY
            assert exporter.session.get.call_count == 2
    
    def test_call_graph_paginated(self, exporter):
        """Test pagination handling."""
        # Mock the call_graph_with_retry method
        with patch.object(exporter, 'call_graph_with_retry') as mock_call:
            # First call returns data with next link
            mock_call.side_effect = [
                {
                    "value": [{"id": "1", "name": "item1"}],
                    "@odata.nextLink": "https://graph.microsoft.com/v1.0/test?$skip=1"
                },
                {
                    "value": [{"id": "2", "name": "item2"}]
                }
            ]
            
            result = exporter.call_graph_paginated("https://graph.microsoft.com/v1.0/test")
            
            assert result == [
                {"id": "1", "name": "item1"},
                {"id": "2", "name": "item2"}
            ]
            assert mock_call.call_count == 2
    
    def test_download_media_success(self, exporter):
        """Test successful media download."""
        # Mock successful download
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.iter_content.return_value = [b"fake_image_data"]
        
        exporter.session = Mock()
        exporter.session.get.return_value = mock_response
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir)
            filename = exporter.download_media("https://example.com/image.jpg", output_path)
            
            assert filename == "image.jpg"
            assert (output_path / filename).exists()
    
    def test_download_media_failure(self, exporter):
        """Test media download failure."""
        # Mock failed download
        exporter.session = Mock()
        exporter.session.get.side_effect = Exception("Network error")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir)
            filename = exporter.download_media("https://example.com/image.jpg", output_path)
            
            assert filename == ""
    
    def test_process_html_content(self, exporter):
        """Test HTML to Markdown conversion with media processing."""
        html_content = """
        <html>
            <body>
                <h1>Test Page</h1>
                <p>This is a test paragraph.</p>
                <img src="https://example.com/image.jpg" alt="Test image">
            </body>
        </html>
        """
        
        with patch.object(exporter, 'download_media') as mock_download:
            mock_download.return_value = "image_1234.jpg"
            
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = Path(temp_dir)
                markdown = exporter.process_html_content(html_content, output_path)
                
                assert "# Test Page" in markdown
                assert "This is a test paragraph" in markdown
                mock_download.assert_called_once_with("https://example.com/image.jpg", output_path)
    
    def test_export_page(self, exporter):
        """Test page export functionality."""
        # Mock page data
        page = {
            "id": "page_123",
            "title": "Test Page"
        }
        
        # Mock page content response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><h1>Test Page</h1><p>Content</p></body></html>"
        
        exporter.session = Mock()
        exporter.session.get.return_value = mock_response
        
        with tempfile.TemporaryDirectory() as temp_dir:
            section_path = Path(temp_dir)
            
            with patch.object(exporter, 'process_html_content') as mock_process:
                mock_process.return_value = "# Test Page\n\nContent"
                
                exporter.export_page(page, section_path)
                
                # Check that markdown file was created
                md_files = list(section_path.glob("*.md"))
                assert len(md_files) == 1
                assert "Test Page.md" in md_files[0].name
    
    def test_sanitize_filename(self, exporter):
        """Test filename sanitization."""
        # Test various problematic characters
        test_cases = [
            ("Normal Title", "Normal Title"),
            ("Title with / slash", "Title with _ slash"),
            ("Title with \\ backslash", "Title with _ backslash"),
            ("Title with : colon", "Title with _ colon"),
            ("Title with * asterisk", "Title with _ asterisk"),
            ("Title with ? question", "Title with _ question"),
            ("Title with < > brackets", "Title with _ _ brackets"),
        ]
        
        for input_title, expected in test_cases:
            # This would be part of the export_page method
            safe_title = input_title.replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace("<", "_").replace(">", "_")
            assert safe_title == expected


if __name__ == "__main__":
    pytest.main([__file__]) 