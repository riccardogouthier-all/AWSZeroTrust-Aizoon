"""Functional browser checks; TLS identity is verified separately with lab-ca.crt."""
import json
import ssl
import urllib.request

from playwright.sync_api import sync_playwright
from ops import ROOT, outputs

url = "https://" + outputs()["waf_ip"]
context = ssl.create_default_context(cafile=str(ROOT / "lab-ca.crt"))
with urllib.request.urlopen(url + "/rest/products/search?q=apple", context=context, timeout=20) as response:
    products = json.load(response)
assert products["status"] == "success" and products["data"], "Product search failed with verified TLS"

results = []
with sync_playwright() as playwright:
    for engine in ["chromium", "firefox", "webkit"]:
        browser = getattr(playwright, engine).launch()
        for mobile in [False, True]:
            # Keep the generated CA out of the user's operating-system trust store.
            # Browser contexts bypass CA trust only; urllib above verifies chain and IP SAN.
            session = browser.new_context(ignore_https_errors=True, viewport={"width": 390 if mobile else 1440, "height": 844 if mobile else 1000})
            page = session.new_page()
            failures = []
            page.on("pageerror", lambda error: failures.append(str(error)))
            response = page.goto(url, wait_until="networkidle", timeout=60000)
            assert response.status == 200
            assert "Juice Shop" in page.title()
            dismiss = page.locator("button").filter(has_text="Dismiss").first
            dismiss.wait_for(state="visible", timeout=15000)
            dismiss.click()
            page.locator("mat-dialog-container").wait_for(state="hidden")
            page.get_by_text("Me want it!", exact=True).click(timeout=15000)
            page.get_by_text("All Products", exact=True).wait_for(timeout=30000)
            assert page.locator("mat-card").count() > 0, "No product cards rendered"
            product_count = page.locator("mat-card").count()
            screenshot = ROOT / "evidence" / f"{engine}-{'mobile' if mobile else 'desktop'}.png"
            page.screenshot(path=str(screenshot), full_page=True)
            page.goto(url + "/#/login", wait_until="networkidle")
            page.locator("#email").wait_for(state="visible")
            assert page.locator("#password").is_visible()
            result = {"engine": engine, "viewport": "mobile" if mobile else "desktop", "status": response.status, "title": page.title(), "product_cards": product_count, "login_form": True, "javascript_errors": failures, "screenshot": screenshot.name, "browser_ca_trust_bypassed": True}
            results.append(result)
            print(json.dumps(result), flush=True)
            session.close()
        browser.close()
(ROOT / "evidence" / "browser-results.json").write_text(json.dumps({"tls_chain_and_ip_verified": True, "search_api_passed": True, "results": results}, indent=2), encoding="utf-8")
