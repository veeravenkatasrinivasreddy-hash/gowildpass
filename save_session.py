"""
Run this once to log in manually and save your session.
After this, the app won't need to log in again (until cookies expire).
"""
import sys, time
sys.path.insert(0, "backend")
from dotenv import load_dotenv
import os, json
load_dotenv()

EMAIL = os.getenv("FRONTIER_EMAIL")
PASSWORD = os.getenv("FRONTIER_PASSWORD")
SESSION_FILE = "frontier_session.json"

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        permissions=["geolocation"],
        geolocation={"latitude": 39.1, "longitude": -84.5},
    )
    page = context.new_page()

    page.goto("https://www.flyfrontier.com", timeout=30000)
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # Open login modal
    signin = page.locator("span:has-text('ACCOUNT SIGN IN'), span:has-text('account sign in')").first
    signin.locator("xpath=..").click()
    time.sleep(2)

    # Fill credentials
    page.locator('input[name="email"][data-vv-scope="login-fields"]').fill(EMAIL)
    time.sleep(0.5)
    pwd = page.locator('input[name="password"][data-vv-scope="login-fields"]')
    pwd.fill(PASSWORD)
    pwd.press("Enter")
    time.sleep(3)

    # Check for MFA
    try:
        mfa = page.locator('input[data-vv-scope="mfa"]').first
        if mfa.is_visible(timeout=5000):
            print("\n*** CHECK YOUR EMAIL for the one-time code ***")
            print("*** Enter it in the browser window, then come back and press Enter ***")
            input("Press Enter once you've entered the code...")
            time.sleep(2)
    except:
        pass

    page.wait_for_load_state("networkidle")
    time.sleep(2)
    print(f"Logged in! URL: {page.url}")

    # Save cookies and storage to file
    cookies = context.cookies()
    storage = page.evaluate("() => JSON.stringify(localStorage)")
    session = {"cookies": cookies, "localStorage": storage}
    with open(SESSION_FILE, "w") as f:
        json.dump(session, f)

    print(f"\nSession saved to {SESSION_FILE}")
    print("You won't need to log in again until this session expires.")
    browser.close()
