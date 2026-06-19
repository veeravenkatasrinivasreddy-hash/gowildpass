import sys, time, os, json
sys.path.insert(0, "backend")
from playwright.sync_api import sync_playwright

SESSION_FILE = "frontier_session.json"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    with open(SESSION_FILE) as f:
        session = json.load(f)
    context.add_cookies(session["cookies"])

    page = context.new_page()
    page.goto("https://www.flyfrontier.com", timeout=30000)
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # 1. One-way
    page.evaluate("""() => {
        for (const l of document.querySelectorAll('label')) {
            if (l.innerText.toLowerCase().includes('one')) { l.click(); return; }
        }
    }""")
    time.sleep(1)
    print("One-way selected")

    # 2. Origin CVG
    inp = page.locator('input[name="origin"]')
    inp.click(click_count=3)
    inp.fill("")
    inp.type("CVG", delay=100)
    time.sleep(2)
    for item in page.locator("li").all():
        try:
            txt = item.inner_text().strip()
            if "CVG" in txt and item.is_visible():
                item.click()
                print(f"Origin: {txt[:40]}")
                break
        except:
            pass
    time.sleep(1)

    # 3. Destination ATL
    inp = page.locator('input[name="destination"]')
    inp.click(click_count=3)
    inp.fill("")
    inp.type("ATL", delay=100)
    time.sleep(2)
    import re
    for item in page.locator("li").all():
        try:
            txt = item.inner_text().strip()
            if re.search(r'\bATL\b|\(ATL\)', txt) and item.is_visible():
                item.click()
                print(f"Destination: {txt[:40]}")
                break
        except:
            pass
    time.sleep(1)

    # 4. Date
    d = page.locator('input[name="departureDate"]')
    d.click(click_count=3)
    d.type("06/18/2026", delay=100)
    page.keyboard.press("Tab")
    time.sleep(1)
    print(f"Date: {d.input_value()}")

    # 5. Click SEARCH button - try multiple approaches
    clicked = page.evaluate("""() => {
        // Try by type=submit
        let b = document.querySelector('button[type=submit], input[type=submit]');
        if (b) { b.click(); return 'submit: ' + b.innerText; }
        // Try by class containing 'search'
        b = document.querySelector('[class*="search" i] button, button[class*="search" i]');
        if (b) { b.click(); return 'class: ' + b.innerText; }
        // Try any green/primary button in the form
        b = document.querySelector('form button, .btn-primary, [class*="btn"]');
        if (b) { b.click(); return 'form btn: ' + b.innerText; }
        return 'not found';
    }""")
    print(f"Search click: {clicked}")
    # Also try Playwright locator as fallback
    if "not found" in clicked:
        try:
            page.locator('button:has-text("Search"), [class*="search-btn"], .search-button').first.click(timeout=3000)
            print("Clicked via Playwright locator")
        except:
            # Last resort: press Enter on the form
            page.locator('input[name="departureDate"]').press("Enter")
            print("Pressed Enter fallback")

    # Wait for results
    try:
        page.wait_for_url("**/Flight/Select**", timeout=25000)
    except:
        page.wait_for_load_state("networkidle", timeout=25000)
    time.sleep(5)
    print(f"Results URL: {page.url}")

    # 6. Find and click GoWild tab
    print("\n=== GoWild elements ===")
    gowild_els = page.locator('text=/GoWild/i').all()
    print(f"Found {len(gowild_els)} GoWild elements")
    for el in gowild_els:
        try:
            print(f"  tag={el.evaluate('e=>e.tagName')} text='{el.inner_text().strip()[:60]}' visible={el.is_visible()}")
        except:
            pass

    # Click the GoWild tab
    for el in gowild_els:
        try:
            if el.is_visible():
                el.click()
                print("Clicked GoWild element")
                time.sleep(3)
                break
        except:
            pass

    page.screenshot(path="debug_results.png")

    # 7. Find flight rows - dump all distinct class names
    print("\n=== All visible divs/rows (looking for flight containers) ===")
    result = page.evaluate("""() => {
        const els = document.querySelectorAll('[class]');
        const classes = new Set();
        for (const el of els) {
            if (el.offsetParent !== null) {  // visible
                for (const c of el.classList) {
                    if (c.toLowerCase().includes('flight') || c.toLowerCase().includes('row') ||
                        c.toLowerCase().includes('trip') || c.toLowerCase().includes('fare')) {
                        classes.add(c);
                    }
                }
            }
        }
        return Array.from(classes);
    }""")
    print("Relevant classes found:", result)

    # 8. Try broad selectors
    for sel in ['tr', '[class*="flight"]', '[class*="trip"]', '[class*="fare"]', '[class*="row"]']:
        els = page.locator(sel).all()
        visible = [e for e in els if e.is_visible()]
        if visible:
            print(f"\n  Selector '{sel}': {len(visible)} visible")
            for e in visible[:2]:
                try:
                    print(f"    {e.inner_text().strip()[:80]}")
                except:
                    pass

    page.screenshot(path="debug_results.png")
    input("\nPress Enter to close...")
    browser.close()
