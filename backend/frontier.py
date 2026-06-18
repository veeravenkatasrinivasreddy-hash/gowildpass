"""
Frontier Airlines GoWild Pass flight search and booking via Playwright.
"""

import os
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

EMAIL = os.getenv("FRONTIER_EMAIL")
PASSWORD = os.getenv("FRONTIER_PASSWORD")

FRONTIER_URL = "https://www.flyfrontier.com"


def search_flights(origin: str, destination: str, date: str) -> list[dict]:
    """
    Search GoWild Pass flights from origin to destination on a given date.
    date format: YYYY-MM-DD
    Returns list of flight dicts: {flight, departure, arrival, price, bookable}
    """
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headless=False so you can watch it
        context = browser.new_context()
        page = context.new_page()

        try:
            # 1. Go to Frontier
            page.goto(FRONTIER_URL, timeout=30000)
            page.wait_for_load_state("networkidle")

            # 2. Log in
            _login(page)

            # 3. Search for flights
            results = _search(page, origin, destination, date)

        except PlaywrightTimeout as e:
            print(f"Timeout error: {e}")
        finally:
            browser.close()

    return results


def book_flight(origin: str, destination: str, date: str, flight_index: int) -> dict:
    """
    Book the flight at flight_index from a search result.
    Returns {success: bool, message: str, confirmation: str}
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        try:
            page.goto(FRONTIER_URL, timeout=30000)
            page.wait_for_load_state("networkidle")
            _login(page)
            result = _search_and_book(page, origin, destination, date, flight_index)
            return result
        except PlaywrightTimeout as e:
            return {"success": False, "message": f"Timeout: {e}", "confirmation": ""}
        finally:
            browser.close()


def _login(page):
    """Log in to Frontier account."""
    # Click Sign In
    page.click("text=Sign In", timeout=10000)
    page.wait_for_load_state("networkidle")

    # Fill credentials
    page.fill('input[type="email"], input[name="email"], #email', EMAIL)
    page.fill('input[type="password"], input[name="password"], #password', PASSWORD)
    page.click('button[type="submit"], button:has-text("Sign In")')
    page.wait_for_load_state("networkidle")
    time.sleep(2)


def _search(page, origin: str, destination: str, date: str) -> list[dict]:
    """Fill in flight search form and return results."""
    results = []

    # Navigate to booking page
    page.goto(f"{FRONTIER_URL}/booking/flights", timeout=30000)
    page.wait_for_load_state("networkidle")

    # Fill origin
    origin_input = page.locator('input[placeholder*="From"], input[aria-label*="origin" i]').first
    origin_input.click()
    origin_input.fill(origin)
    time.sleep(1)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")

    # Fill destination
    dest_input = page.locator('input[placeholder*="To"], input[aria-label*="destination" i]').first
    dest_input.click()
    dest_input.fill(destination)
    time.sleep(1)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")

    # Fill date
    date_input = page.locator('input[placeholder*="Depart"], input[aria-label*="depart" i]').first
    date_input.click()
    date_input.fill(date)
    time.sleep(1)

    # Search
    page.click('button:has-text("Search"), button[type="submit"]')
    page.wait_for_load_state("networkidle")
    time.sleep(3)

    # Scrape results — filter for GoWild $16 flights
    flight_cards = page.locator('.flight-card, [data-testid*="flight"], .flight-result').all()
    for i, card in enumerate(flight_cards):
        text = card.inner_text()
        price_match = "$16" in text or "16.00" in text or "GoWild" in text.lower()
        results.append({
            "index": i,
            "raw": text[:200],
            "is_gowild": price_match,
            "price": "$16" if price_match else "N/A",
        })

    return [r for r in results if r["is_gowild"]]


def _search_and_book(page, origin, destination, date, flight_index) -> dict:
    """Search and select a specific flight to book."""
    _search(page, origin, destination, date)

    # Click the chosen flight
    flight_cards = page.locator('.flight-card, [data-testid*="flight"], .flight-result').all()
    if flight_index >= len(flight_cards):
        return {"success": False, "message": "Flight no longer available", "confirmation": ""}

    flight_cards[flight_index].click()
    time.sleep(2)

    # Continue through booking flow
    page.click('button:has-text("Continue"), button:has-text("Select")')
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # Skip extras / seats if prompted
    for skip_text in ["No thanks", "Skip", "Continue"]:
        btn = page.locator(f'button:has-text("{skip_text}")').first
        if btn.is_visible():
            btn.click()
            time.sleep(1)

    # Final purchase
    page.click('button:has-text("Purchase"), button:has-text("Confirm"), button:has-text("Book")')
    page.wait_for_load_state("networkidle")
    time.sleep(3)

    # Grab confirmation number
    confirmation = ""
    conf_el = page.locator('[class*="confirmation"], [data-testid*="confirmation"]').first
    if conf_el.is_visible():
        confirmation = conf_el.inner_text()

    return {
        "success": True,
        "message": "Booking complete!",
        "confirmation": confirmation,
    }
