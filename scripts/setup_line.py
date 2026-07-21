#!/usr/bin/env python3
"""CK-NEXUS LINE Setup Wizard"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.line_auth import LineAuthManager
from core.oauth_server import OAuthServer

def print_header():
    print("""
╔══════════════════════════════════════════════════════════╗
║              LINE Setup Wizard for CK-NEXUS             ║
╚══════════════════════════════════════════════════════════╝
""")

def print_step(step, title):
    print(f"\n{'='*50}")
    print(f"Step {step}: {title}")
    print('='*50)

def main():
    print_header()

    config_path = os.path.expanduser("~/.ck-nexus/config.json")
    with open(config_path) as f:
        config = json.load(f)

    auth = LineAuthManager()

    print_step(1, "LINE Developers Console")
    print("""
1. Go to: https://developers.line.biz/console/
2. Create a new provider (or use existing)
3. Create a Messaging API channel
4. Note down:
   - Channel ID (numeric)
   - Channel Secret (alphanumeric)
   - Channel Access Token (long-lived)
""")

    print_step(2, "Enter Credentials")
    channel_id = input("Channel ID (numeric): ").strip()
    channel_secret = input("Channel Secret: ").strip()
    channel_token = input("Channel Access Token (optional, press Enter to skip): ").strip()

    if channel_id:
        config["line"]["channel_id"] = channel_id
    if channel_secret:
        config["line"]["channel_secret"] = channel_secret
    if channel_token:
        config["line"]["channel_access_token"] = channel_token
        config["line"]["enabled"] = True

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print("\n✓ Credentials saved!")

    if channel_token:
        print_step(3, "Testing Direct Connection")
        from providers.line_provider import LineProvider
        line = LineProvider(channel_token)
        ok, msg = line.test_connection()
        if ok:
            print(f"✓ Connected! {msg}")
        else:
            print(f"✗ Connection failed: {msg}")
            print("\nYou can try OAuth2 authentication instead.")
    else:
        print_step(3, "OAuth2 Authentication")
        print("""
To get a Channel Access Token via OAuth2:

1. Set up a web server to handle callbacks
2. Open this URL in your browser:
""")

        auth_result = auth.auto_connect(channel_id, channel_secret)
        print(f"   {auth_result['auth_url']}")
        print("""
3. Login to LINE and authorize the app
4. You'll be redirected to: http://localhost:8088/callback
5. Copy the 'code' from the URL
6. Run this command in CK-NEXUS:

   /line code code=<YOUR_CODE> secret=<CHANNEL_SECRET>

Or use the direct token method:

   /line connect token=<YOUR_TOKEN>
""")

    print_step(4, "Verify Connection")
    print("""
After connecting, verify with:

   /line test
   /line profile

Send messages with:

   /send to=<USER_ID> msg=Hello!
   /notify This is a test notification
""")

    print("\nSetup complete!")

if __name__ == "__main__":
    main()
