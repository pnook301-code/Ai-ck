#!/usr/bin/env python3
"""
CK-NEXUS AI Web Master
ใช้ AI ควบคุมเบราว์เซอร์ เข้าเว็บ สมัครสมาชิก อัปเดตข้อมูลอัตโนมัติ
ใช้: python3 ai_web_master.py [URL] [username] [email] [password]
"""

import os
import sys
import json
import asyncio
import urllib.request
from datetime import datetime

SD_PATH = "/workspace/ck-nexus"
CONFIG_PATH = "/root/.ck-nexus/config.json"
ENV_PATH = "/workspace/ck-nexus/auto-vps-agent/.env"


def load_gemini_key():
    """Load Gemini API key from .env or config"""
    # Try .env first
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    return line.strip().split("=", 1)[1]
    
    # Try config
    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
            return config.get("gemini", {}).get("key", "")
    except:
        pass
    return ""


def call_gemini(prompt: str) -> str:
    """Call Gemini API directly"""
    api_key = load_gemini_key()
    if not api_key:
        return "ERROR: No Gemini API key found"
    
    try:
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}]
        }).encode()
        
        req = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"ERROR: {e}"


async def ai_web_master_task(url: str, username: str, email: str, password: str):
    """Execute AI Web Master task using browser-use"""
    print("╔══════════════════════════════════════════════════╗")
    print("║  🤖 CK-NEXUS AI WEB MASTER                      ║")
    print("╠══════════════════════════════════════════════════╣")
    print("║  🧠 AI: Gemini Flash                             ║")
    print("║  🌐 Browser: Playwright (Full Control)           ║")
    print("║  🎯 Task: Auto Register + Profile Update         ║")
    print("╚══════════════════════════════════════════════════╝")
    print()
    
    # Check if browser-use is available
    try:
        from browser_use import Agent, Browser, BrowserConfig
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        print("✅ browser-use package found, using full automation...")
        
        # Configure browser
        config = BrowserConfig(
            headless=True,  # Run headless on server
            disable_security=True
        )
        browser = Browser(config=config)
        
        # Configure AI
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=load_gemini_key()
        )
        
        # Task command
        task = f"""
1. Go to {url}
2. Find and click 'Register' or 'Sign Up' button
3. Fill in the registration form:
   - Username: {username}
   - Email: {email}
   - Password: {password}
4. Submit the registration form
5. Wait for page to load
6. Find 'Profile Settings' or 'Edit Profile'
7. Update Bio to: 'CK-NEXUS AI Agent - Automated by CK-NEXUS v1.4'
8. Save changes
"""
        
        print(f"🚀 Starting browser automation on {url}...")
        agent = Agent(task=task, llm=llm, browser=browser)
        result = await agent.run()
        
        print(f"🎉 Task completed! Result: {result}")
        await browser.close()
        
        return {"status": "SUCCESS", "method": "browser-use", "result": str(result)}
        
    except ImportError:
        print("⚠️ browser-use not installed, using fallback method...")
        return await fallback_web_master(url, username, email, password)


async def fallback_web_master(url: str, username: str, email: str, password: str):
    """Fallback method using Gemini AI analysis"""
    print("🧠 Using Gemini AI to analyze target website...")
    
    # Analyze the target URL
    analysis_prompt = f"""
Analyze this registration page: {url}

Tell me in JSON format:
{{
  "has_registration": true/false,
  "form_fields": ["field1", "field2"],
  "registration_url": "direct link to register",
  "tips": "any tips for registration"
}}
"""
    
    analysis = call_gemini(analysis_prompt)
    print(f"📊 Website Analysis:\n{analysis}")
    
    # Generate step-by-step instructions
    instructions_prompt = f"""
Create detailed step-by-step instructions for registering on {url} with:
- Username: {username}
- Email: {email}
- Password: {password}

Include CSS selectors or XPath if possible.
"""
    
    instructions = call_gemini(instructions_prompt)
    print(f"\n📋 Step-by-step Instructions:\n{instructions}")
    
    # Save instructions
    result_path = os.path.join(SD_PATH, f"web_master_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(result_path, "w") as f:
        json.dump({
            "url": url,
            "username": username,
            "email": email,
            "analysis": analysis,
            "instructions": instructions,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Instructions saved to: {result_path}")
    print("📋 Manual execution required - follow the instructions above")
    
    return {"status": "INSTRUCTIONS_GENERATED", "file": result_path}


def main():
    # Parse arguments
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    username = sys.argv[2] if len(sys.argv) > 2 else "cknexus_agent2026"
    email = sys.argv[3] if len(sys.argv) > 3 else "nexus_worker@openclaw.ai"
    password = sys.argv[4] if len(sys.argv) > 4 else "SecurePassword99!"
    
    print(f"🎯 Target: {url}")
    print(f"👤 Username: {username}")
    print(f"📧 Email: {email}")
    print(f"🔑 Password: {'*' * len(password)}")
    print()
    
    # Run the task
    asyncio.run(ai_web_master_task(url, username, email, password))


if __name__ == "__main__":
    main()
