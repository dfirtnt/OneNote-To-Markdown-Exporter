#!/usr/bin/env python3
"""
Debug script to examine token and understand OneNote API access
"""

import requests
import json
from msal import PublicClientApplication
import os

CLIENT_ID = os.getenv("ONENOTE_CLIENT_ID", "YOUR_CLIENT_ID_HERE")  # Set via environment variable or replace with your Azure AD app registration client ID
SCOPES = ["Notes.Read", "User.Read"]

def debug_token():
    """Debug the token and API access."""
    
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
    print(f"Expires in: {result.get('expires_in', 'Unknown')}")
    
    # Decode token (if possible)
    try:
        import jwt
        # Note: This might not work if the token is encrypted
        decoded = jwt.decode(token, options={"verify_signature": False})
        print(f"\n🔍 Token details:")
        print(f"  Audience (aud): {decoded.get('aud', 'Unknown')}")
        print(f"  Issuer (iss): {decoded.get('iss', 'Unknown')}")
        print(f"  Scopes (scp): {decoded.get('scp', 'Unknown')}")
        print(f"  Roles (roles): {decoded.get('roles', 'Unknown')}")
    except Exception as e:
        print(f"Could not decode token: {e}")
    
    # Test different endpoints
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Test User.Read
    print("\n🔍 Testing User.Read permission...")
    try:
        response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ User.Read works! User: {user_data.get('displayName', 'Unknown')}")
        else:
            print(f"❌ User.Read failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ User.Read error: {e}")
    
    # Test OneNote endpoints
    print("\n🔍 Testing OneNote endpoints...")
    endpoints = [
        "https://graph.microsoft.com/v1.0/me/onenote/notebooks",
        "https://graph.microsoft.com/v1.0/me/onenote/sections", 
        "https://graph.microsoft.com/v1.0/me/onenote/pages"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"\nTesting: {endpoint}")
            response = requests.get(endpoint, headers=headers)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('value', []))
                print(f"  ✅ Success! Found {count} items")
            else:
                print(f"  ❌ Failed: {response.text}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    debug_token()
