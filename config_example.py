#!/usr/bin/env python3
"""
Configuration example for OneNote to Markdown Exporter

This file shows how to configure the exporter. Copy this to config.py
and update with your actual values, or use environment variables.
"""

import os

# Azure AD Application Configuration
# Option 1: Environment variable (recommended)
CLIENT_ID = os.getenv("ONENOTE_CLIENT_ID", "YOUR_CLIENT_ID_HERE")

# Option 2: Direct configuration (not recommended for security)
# CLIENT_ID = "your-actual-client-id-here"

# API Scopes
SCOPES = ["Notes.Read", "User.Read"]

# Output configuration
OUTPUT_DIR = "output"  # Directory where exported files will be saved

# Rate limiting configuration
MAX_RETRIES = 3
BASE_DELAY = 1  # seconds

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FILE = "onenote_export.log"

# Media Download Configuration
MAX_MEDIA_SIZE = 10 * 1024 * 1024  # 10MB maximum file size for media downloads
MEDIA_TIMEOUT = 30  # Timeout in seconds for media downloads

# HTML to Markdown Configuration
HTML2TEXT_CONFIG = {
    "body_width": 0,  # Don't wrap lines
    "ignore_images": False,
    "ignore_emphasis": False,
    "ignore_links": False,
    "ignore_tables": False,
    "ignore_anchors": False,
} 