#!/usr/bin/env python3
"""
Screenshot capture script for README documentation.
Run this against the live Heroku app or local dev server.
"""
import os
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright

# Configuration
BASE_URL = os.getenv("SCREENSHOT_URL", "https://reitz-wishlist-d7ae3288f979.herokuapp.com")
SCREENSHOTS_DIR = ROOT / "docs" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Test user credentials (create these users first or use existing ones)
TEST_EMAIL = os.getenv("TEST_EMAIL", "")


def take_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Desktop context
        desktop = browser.new_context(
            viewport={"width": 1280, "height": 800},
            device_scale_factor=2,  # Retina quality
        )

        # Mobile context
        mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
        )

        page = desktop.new_page()
        mobile_page = mobile.new_page()

        # Landing page (logged out)
        print("Capturing landing page...")
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        page.screenshot(path=SCREENSHOTS_DIR / "landing.png")

        if TEST_EMAIL:
            # Login
            print("Logging in...")
            page.goto(f"{BASE_URL}/login")
            page.fill('input[name="email"]', TEST_EMAIL)
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")

            # Dashboard
            print("Capturing dashboard...")
            page.goto(BASE_URL)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(500)  # Allow animations
            page.screenshot(path=SCREENSHOTS_DIR / "dashboard-full.png")

            # Cropped dashboard for hero
            page.screenshot(
                path=SCREENSHOTS_DIR / "dashboard.png",
                clip={"x": 0, "y": 0, "width": 1280, "height": 600}
            )

            # Items list
            print("Capturing items list...")
            page.goto(f"{BASE_URL}/items")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(500)
            page.screenshot(path=SCREENSHOTS_DIR / "items-list.png")

            # Quick View modal - find an item and click quick view
            print("Capturing quick view modal...")
            quick_view_btn = page.locator('button[title="Quick View"]').first
            if quick_view_btn.is_visible():
                quick_view_btn.click()
                page.wait_for_selector('#quickViewModal.show', timeout=5000)
                page.wait_for_timeout(300)
                page.screenshot(path=SCREENSHOTS_DIR / "quick-view.png")
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)

            # Events page
            print("Capturing events...")
            page.goto(f"{BASE_URL}/events")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(500)
            page.screenshot(path=SCREENSHOTS_DIR / "events.png")

            # My Claims page
            print("Capturing my claims...")
            page.goto(f"{BASE_URL}/my-claims")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(500)
            page.screenshot(path=SCREENSHOTS_DIR / "my-claims.png")

            # Mobile view
            print("Capturing mobile view...")
            mobile_page.goto(f"{BASE_URL}/login")
            mobile_page.fill('input[name="email"]', TEST_EMAIL)
            mobile_page.click('button[type="submit"]')
            mobile_page.wait_for_load_state("networkidle")
            mobile_page.goto(BASE_URL)
            mobile_page.wait_for_load_state("networkidle")
            mobile_page.wait_for_timeout(500)
            mobile_page.screenshot(path=SCREENSHOTS_DIR / "mobile.png")
        else:
            print("\nNo TEST_EMAIL set. Only captured landing page.")
            print("To capture all screenshots, run:")
            print(f"  TEST_EMAIL=your@email.com python {__file__}")

        browser.close()

    print(f"\nScreenshots saved to: {SCREENSHOTS_DIR}")
    print("Files created:")
    for f in sorted(SCREENSHOTS_DIR.glob("*.png")):
        print(f"  - {f.name}")


if __name__ == "__main__":
    take_screenshots()
