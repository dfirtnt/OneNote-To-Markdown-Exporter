#!/usr/bin/env python3
"""
Test script to check Microsoft Graph permissions
"""

import os
import requests
from msal import PublicClientApplication

CLIENT_ID = os.getenv("ONENOTE_CLIENT_ID", "YOUR_CLIENT_ID_HERE")  # Set via environment variable or replace with your Azure AD app registration client ID
SCOPES = ["Notes.Read", "User.Read"]

def test_permissions():
    """Test what permissions we have access to."""
    
    # Initialize the app
    app = PublicClientApplication(CLIENT_ID, authority="https://login.microsoftonline.com/consumers")
    
    # Get device flow
    flow = app.initiate_device_flow(scopes=SCOPES)
    if not flow.get("user_code"):
        print("Device code flow failed")
        return
    
    print("Please authenticate using the device code flow:")
    print(flow["message"])
    
    # Acquire token
    result = app.acquire_token_by_device_flow(flow)
    
    if "access_token" not in result:
        print(f"Failed to acquire token: {result}")
        return
    
    token = result["access_token"]
    print(f"✅ Successfully got token")
    print(f"Scopes granted: {result.get('scope', 'Not specified')}")
    print(f"Token type: {result.get('token_type', 'Unknown')}")
    
    # Test different endpoints
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test User.Read
    print("\n🔍 Testing User.Read permission...")
    try:
        response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ User.Read works! User: {user_data.get('displayName', 'Unknown')}")
            print(f"   User ID: {user_data.get('id', 'Unknown')}")
            print(f"   User Principal Name: {user_data.get('userPrincipalName', 'Unknown')}")
        else:
            print(f"❌ User.Read failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ User.Read error: {e}")
    
    # Test OneNote endpoints based on Microsoft documentation
    print("\n🔍 Testing OneNote endpoints (personal account)...")
    try:
        # Test notebooks endpoint
        print("Testing /me/onenote/notebooks...")
        response = requests.get("https://graph.microsoft.com/v1.0/me/onenote/notebooks", headers=headers)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            notebooks = response.json()
            print(f"  ✅ Success! Found {len(notebooks.get('value', []))} notebooks")
            for nb in notebooks.get('value', [])[:3]:  # Show first 3
                print(f"    - {nb.get('displayName', 'Unknown')} (ID: {nb.get('id', 'Unknown')[:8]}...)")
        else:
            print(f"  ❌ Failed: {response.text}")
        
        # Test sections endpoint
        print("\nTesting /me/onenote/sections...")
        response_sections = requests.get("https://graph.microsoft.com/v1.0/me/onenote/sections", headers=headers)
        print(f"  Status: {response_sections.status_code}")
        if response_sections.status_code == 200:
            sections = response_sections.json()
            print(f"  ✅ Success! Found {len(sections.get('value', []))} sections")
        else:
            print(f"  ❌ Failed: {response_sections.text}")
            
        # Test pages endpoint
        print("\nTesting /me/onenote/pages...")
        response_pages = requests.get("https://graph.microsoft.com/v1.0/me/onenote/pages", headers=headers)
        print(f"  Status: {response_pages.status_code}")
        if response_pages.status_code == 200:
            pages = response_pages.json()
            print(f"  ✅ Success! Found {len(pages.get('value', []))} pages")
        else:
            print(f"  ❌ Failed: {response_pages.text}")
            
    except Exception as e:
        print(f"❌ OneNote test error: {e}")
    
    # Test with different headers
    print("\n🔍 Testing with different headers...")
    try:
        headers_with_accept = headers.copy()
        headers_with_accept["Accept"] = "application/json"
        headers_with_accept["Content-Type"] = "application/json"
        
        response = requests.get("https://graph.microsoft.com/v1.0/me/onenote/notebooks", headers=headers_with_accept)
        print(f"With Accept header: {response.status_code}")
        if response.status_code != 200:
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Header test error: {e}")

if __name__ == "__main__":
    test_permissions()
