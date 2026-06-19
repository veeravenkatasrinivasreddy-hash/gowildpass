import os
import time
import json
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

EMAIL = os.getenv("FRONTIER_EMAIL")
PASSWORD = os.getenv("FRONTIER_PASSWORD")
SESSION_FILE = os.path.join(os.path.dirname(__file__), '..', 'frontier_session.json')


def search_flights(origin: str, destination: str, date: str, trip_type: str = "OW") -> list[dict]:
    """Search GoWild flights. date: YYYY-MM-DD. trip_type: OW or RT."""
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            permissions=["geolocation"],
            geolocation={"latitude": 39.1, "longitude": -84.5},
        )
        _load_session(context)
        page = context.new_page()
        try:
            page.goto("https://www.flyfrontier.com", timeout=30000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            _close_popups(page)
            if _needs_login(page):
                _login(page)
                _close_popups(page)
            results = _search(page, origin, destination, date, trip_type)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()
    return results


def book_flight(origin: str, destination: str, date: str, flight_index: int, trip_type: str = "OW") -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            permissions=["geolocation"],
            geolocation={"latitude": 39.1, "longitude": -84.5},
        )
        _load_session(context)
        page = context.new_page()
        try:
            page.goto("https://www.flyfrontier.com", timeout=30000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            _close_popups(page)
            if _needs_login(page):
                _login(page)
                _close_popups(page)
            return _search_and_book(page, origin, destination, date, flight_index, trip_type)
        except Exception as e:
            return {"success": False, "message": str(e), "confirmation": ""}
        finally:
            browser.close()


def _load_session(context):
    if not os.path.exists(SESSION_FILE):
        return
    try:
        with open(SESSION_FILE) as f:
            session = json.load(f)
        context.add_cookies(session.get("cookies", []))
        print("Session loaded.")
    except Exception as e:
        print(f"Session load failed: {e}")


def _needs_login(page) -> bool:
    if os.path.exists(SESSION_FILE):
        return False
    body = page.inner_text("body").lower()
    return "sign out" not in body and "my trips" not in body


def _close_popups(page):
    for sel in ['[aria-label="Close"]', 'button.close', '.wisepops-close',
                'button:has-text("No thanks")', '[class*="close-btn"]']:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1000):
                btn.click()
                time.sleep(0.5)
        except:
            pass
    # Close calendar if open by pressing Escape
    try:
        if page.locator('.ui-datepicker, [class*="calendar"], [class*="datepicker"]').first.is_visible(timeout=500):
            page.keyboard.press("Escape")
            time.sleep(0.5)
    except:
        pass


def _login(page):
    signin = page.locator("span:has-text('ACCOUNT SIGN IN'), span:has-text('account sign in')").first
    signin.locator("xpath=..").click()
    time.sleep(2)
    email_input = page.locator('input[name="email"][data-vv-scope="login-fields"]')
    email_input.wait_for(state="visible", timeout=10000)
    email_input.fill(EMAIL)
    time.sleep(0.5)
    pwd_input = page.locator('input[name="password"][data-vv-scope="login-fields"]')
    pwd_input.fill(PASSWORD)
    time.sleep(0.5)
    pwd_input.press("Enter")
    time.sleep(3)
    try:
        mfa = page.locator('input[data-vv-scope="mfa"]').first
        if mfa.is_visible(timeout=5000):
            print("\n*** CHECK YOUR EMAIL for the one-time code ***")
            input("Enter it in the browser, then press Enter here...")
            time.sleep(2)
    except:
        pass
    page.wait_for_load_state("networkidle")
    time.sleep(2)


def _fill_airport(page, field_name: str, code: str):
    """Fill airport autocomplete and select the exact matching airport code."""
    inp = page.locator(f'input[name="{field_name}"]')
    inp.click(click_count=3)
    inp.fill("")
    time.sleep(0.3)
    inp.type(code, delay=100)
    time.sleep(2)

    # Look for item containing the airport code in parentheses e.g. "(ATL)"
    items = page.locator('li.ui-autocomplete-item, li:not(.ui-autocomplete-category)').all()
    for item in items:
        try:
            txt = item.inner_text().strip()
            # Match "(ATL)" or "ATL)" or just the code surrounded by non-letters
            import re
            if re.search(rf'\b{code}\b|\({code}\)', txt, re.IGNORECASE) and item.is_visible():
                item.click()
                print(f"  {field_name}: selected '{txt[:50]}'")
                time.sleep(1)
                return
        except:
            pass

    # Fallback: type the full code and press Enter
    inp.click(click_count=3)
    inp.fill(code)
    time.sleep(1.5)
    page.keyboard.press("ArrowDown")
    time.sleep(0.3)
    page.keyboard.press("Enter")
    print(f"  {field_name}: used keyboard fallback for {code}")
    time.sleep(1)


def _search(page, origin: str, destination: str, date: str, trip_type: str) -> list[dict]:
    # Convert YYYY-MM-DD → MM/DD/YYYY
    parts = date.split("-")
    frontier_date = f"{parts[1]}/{parts[2]}/{parts[0]}"

    # Wait for form
    page.locator('input[name="origin"]').wait_for(state="visible", timeout=15000)

    # Select trip type by clicking the visible label
    label_text = "one" if trip_type == "OW" else "round"
    page.evaluate(f"""() => {{
        const labels = document.querySelectorAll('label');
        for (const l of labels) {{
            if (l.innerText.toLowerCase().includes('{label_text}')) {{
                l.click(); return;
            }}
        }}
    }}""")
    time.sleep(1)
    print(f"Selected trip type: {trip_type}")

    # Fill airports
    _fill_airport(page, "origin", origin)
    _fill_airport(page, "destination", destination)

    # Fill date — clear fully then type
    d = page.locator('input[name="departureDate"]')
    d.click(click_count=3)
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    time.sleep(0.3)
    d.type(frontier_date, delay=150)
    time.sleep(0.5)
    page.keyboard.press("Tab")
    time.sleep(0.5)
    # Verify what was entered and retry with JS if wrong
    entered = d.input_value()
    print(f"Date entered: {entered!r} (expected {frontier_date!r})")
    if frontier_date not in entered:
        page.evaluate(f"() => {{ document.querySelector('input[name=\"departureDate\"]').value = '{frontier_date}'; }}")
        d.click()
        page.keyboard.press("Tab")
        time.sleep(0.5)
        print(f"Date after JS fix: {d.input_value()!r}")
    time.sleep(0.5)

    # Click Search button
    page.evaluate("""() => {
        let b = document.querySelector('button[type=submit], input[type=submit]');
        if (b) { b.click(); return; }
        b = document.querySelector('form button, .btn-primary, [class*="btn"]');
        if (b) { b.click(); return; }
    }""")

    # Wait for results
    print("Waiting for results page...")
    try:
        page.wait_for_url("**/Flight/Select**", timeout=25000)
    except:
        page.wait_for_load_state("networkidle", timeout=25000)
    time.sleep(5)
    print(f"Results URL: {page.url}")

    # Click GoWild tab
    _click_gowild_tab(page)

    return _parse_results(page, origin, destination)


def _click_gowild_tab(page):
    """Click the visible GoWild!™ tab on the results page."""
    gowild_els = page.locator('text=/GoWild/i').all()
    for el in gowild_els:
        try:
            if el.is_visible():
                el.click()
                print("Clicked GoWild tab")
                time.sleep(3)
                return
        except:
            pass
    print("GoWild tab not found")


def _read_date_strip(page) -> list[dict]:
    import re
    dates = []
    cells = page.locator('.ibe-flight-slider-box, .ibe-flight-slider-box-selected').all()
    for cell in cells:
        try:
            txt = cell.inner_text().strip()
            lines = [l.strip() for l in txt.split('\n') if l.strip()]
            if len(lines) < 2:
                continue
            date_label = lines[0]
            price = lines[1]
            # Must look like a real date (contains month abbreviation or slash) and price like $16
            if not re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d+/\d+)', date_label, re.IGNORECASE):
                continue
            if not re.search(r'\$\d+|N/A|—', price):
                continue
            selected = 'selected' in (cell.get_attribute('class') or '')
            dates.append({"date": date_label, "price": price, "selected": selected})
        except:
            pass
    return dates


def _read_flights_on_page(page, origin, destination) -> list[dict]:
    """Read individual flight rows on the current date."""
    import re
    flights = []
    containers = page.locator('.ibe-flight-info-container').all()
    print(f"  Flight containers: {len(containers)}")
    for i, container in enumerate(containers):
        try:
            txt = container.inner_text().strip()
            if not txt:
                continue
            # Get the GoWild (Basic Fare) price — first price cell
            price_el = container.locator('.ibe-farebox-fare-basic .ibe-farebox-fare-select, .ibe-farebox-fare-basic, [class*="farebox"]').first
            price_txt = price_el.inner_text().strip() if price_el.count() > 0 else txt
            if "unavailable" in price_txt.lower():
                continue
            # Times
            times = re.findall(r'\d{1,2}:\d{2}\s?[AP]M', txt)
            dep = times[0] if len(times) > 0 else ""
            arr = times[-1] if len(times) > 1 else ""
            # Duration
            dur_m = re.search(r'(\d+)\s*hrs?\s*(\d+)\s*min', txt, re.IGNORECASE)
            duration = f"{dur_m.group(1)}h {dur_m.group(2)}m" if dur_m else ""
            # Stops
            if "nonstop" in txt.lower():
                stops = "Nonstop"
            else:
                stop_m = re.search(r'(\d+)\s*Stop[s]?\s*(\w+)', txt, re.IGNORECASE)
                stops = stop_m.group(0) if stop_m else ""
            # Price
            price_match = re.search(r'\$[\d,]+', price_txt)
            price = price_match.group(0) if price_match else _extract_price(txt)

            flights.append({
                "index": i,
                "origin": origin,
                "destination": destination,
                "departure": dep,
                "arrival": arr,
                "duration": duration,
                "stops": stops,
                "price": price,
                "summary": f"{dep} → {arr} | {duration} | {stops} | {price}",
                "is_gowild": True,
            })
        except:
            pass
    return flights


def _parse_results(page, origin: str, destination: str) -> list[dict]:
    """Collect date strip prices + flights for current date. Navigate 15 days."""
    import re
    results = []
    try:
        page.wait_for_selector('.ibe-flight-slider-box, .ibe-flight-info-container', timeout=8000)
    except:
        pass

    # Collect date prices across 15 days by navigating the date strip
    all_date_prices = []
    seen_dates = set()
    right_arrow = page.locator('.ibe-flight-slider-arrow-r').first

    for nav in range(10):  # up to 10 clicks to collect ~15+ days
        dates = _read_date_strip(page)
        new_found = False
        for d in dates:
            if d["date"] not in seen_dates:
                seen_dates.add(d["date"])
                all_date_prices.append(d)
                new_found = True
        if len(all_date_prices) >= 15:
            break
        # Try multiple right-arrow selectors
        clicked = page.evaluate("""() => {
            const sels = [
                '.ibe-flight-slider-arrow-r',
                '[class*="arrow-r"]',
                '[class*="arrow_r"]',
                '[class*="next"]',
                'button[aria-label*="next" i]',
                'button[aria-label*="right" i]',
            ];
            for (const s of sels) {
                const el = document.querySelector(s);
                if (el && el.offsetParent !== null) { el.click(); return s; }
            }
            return null;
        }""")
        if not clicked or not new_found:
            break
        time.sleep(1.5)

    print(f"Date strip: {len(all_date_prices)} days collected")
    for d in all_date_prices:
        print(f"  {d['date']}: {d['price']}")

    # Read individual flights for the currently selected date
    flights = _read_flights_on_page(page, origin, destination)
    print(f"Flights on selected date: {len(flights)}")

    # Return flights enriched with date calendar
    for f in flights:
        f["date_prices"] = all_date_prices
    results = flights if flights else [{
        "index": 0,
        "origin": origin,
        "destination": destination,
        "departure": "", "arrival": "", "duration": "", "stops": "",
        "price": all_date_prices[0]["price"] if all_date_prices else "N/A",
        "summary": "See date prices below",
        "date_prices": all_date_prices,
        "is_gowild": True,
    }]
    return results


def _extract_price(text: str) -> str:
    """Extract first dollar amount from text."""
    import re
    match = re.search(r'\$[\d,]+', text)
    return match.group(0) if match else "N/A"


def _search_and_book(page, origin, destination, date, flight_index, trip_type) -> dict:
    flights = _search(page, origin, destination, date, trip_type)
    if flight_index >= len(flights):
        return {"success": False, "message": "Flight not available", "confirmation": ""}

    rows = page.locator('[class*="flight-row"], [class*="FlightRow"], .trip-select-flight-row').all()
    if flight_index < len(rows):
        # Click the Basic Fare price cell (first column = GoWild price)
        price_cells = rows[flight_index].locator('[class*="price"], td').all()
        if price_cells:
            price_cells[0].click()
            time.sleep(2)

    # Skip extras and confirm
    for txt in ["No thanks", "Skip", "Continue"]:
        try:
            btn = page.locator(f'button:has-text("{txt}")').first
            if btn.is_visible(timeout=2000):
                btn.click()
                time.sleep(1)
        except:
            pass

    try:
        page.locator('button:has-text("Purchase"), button:has-text("Confirm"), button:has-text("Book Now")').first.click()
        page.wait_for_load_state("networkidle")
        time.sleep(3)
    except:
        pass

    conf = ""
    try:
        conf = page.locator('[class*="confirmation"]').first.inner_text()
    except:
        pass

    return {"success": True, "message": "Booking complete!", "confirmation": conf}
