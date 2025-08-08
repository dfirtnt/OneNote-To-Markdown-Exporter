#!/usr/bin/env python3
"""
Simple test for OneNote API access
"""

import os
import requests
from msal import PublicClientApplication

CLIENT_ID = os.getenv("ONENOTE_CLIENT_ID", "YOUR_CLIENT_ID_HERE")  # Set via environment variable or replace with your Azure AD app registration client ID
SCOPES = ["Notes.Read", "User.Read"]

def test_onenote():
    """Test OneNote API access."""
    
    print("🔍 Testing OneNote API access for personal accounts...")
    print("Based on Microsoft documentation: https://learn.microsoft.com/en-us/graph/api/resources/onenote-api-overview?view=graph-rest-1.0")
    print()
    
    # Initialize the app
    app = PublicClientApplication(CLIENT_ID, authority="https://login.microsoftonline.com/consumers")
    
    # Get device flow
    flow = app.initiate_device_flow(scopes=SCOPES)
    if not flow.get("user_code"):
        print("❌ Device code flow failed")
        return
    
    print("📱 Please authenticate using the device code flow:")
    print(flow["message"])
    print()
    
    # Acquire token
    result = app.acquire_token_by_device_flow(flow)
    
    if "access_token" not in result:
        print(f"❌ Failed to acquire token: {result}")
        return
    
    token = result["access_token"]
    print(f"✅ Successfully authenticated!")
    print(f"   Scopes granted: {result.get('scope', 'Not specified')}")
    print()
    
    # Test endpoints
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 1: User.Read (should work)
    print("🔍 Test 1: User.Read permission...")
    try:
        response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            print(f"   ✅ User.Read works! User: {user_data.get('displayName', 'Unknown')}")
        else:
            print(f"   ❌ User.Read failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ User.Read error: {e}")
    
    print()
    
    # Test 2: OneNote notebooks (the main test)
    print("🔍 Test 2: OneNote notebooks...")
    print("   Endpoint: https://graph.microsoft.com/v1.0/me/onenote/notebooks")
    try:
        response = requests.get("https://graph.microsoft.com/v1.0/me/onenote/notebooks", headers=headers)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            notebooks = response.json()
            count = len(notebooks.get('value', []))
            print(f"   ✅ Success! Found {count} notebooks")
            
            # Show first few notebooks
            for i, nb in enumerate(notebooks.get('value', [])[:3]):
                print(f"      {i+1}. {nb.get('displayName', 'Unknown')}")
                
        else:
            print(f"   ❌ Failed: {response.text}")
            
            # Check if it's a permission issue
            if "401" in str(response.status_code):
                print("   💡 This might be a permission or consent issue.")
                print("   💡 Try granting admin consent in Azure Portal.")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    print("📋 Summary:")
    print("   - If Test 1 works but Test 2 fails: Permission/consent issue")
    print("   - If both fail: Authentication issue")
    print("   - If both work: OneNote API is accessible!")

if __name__ == "__main__":
    test_onenote()
