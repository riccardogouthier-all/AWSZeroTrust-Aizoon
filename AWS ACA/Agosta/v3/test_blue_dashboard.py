"""Check the real read-only Wazuh login through an already-open local tunnel."""

def main():
    import json
    from playwright.sync_api import sync_playwright
    from ops import ROOT

    credentials = json.loads((ROOT / "private/blue-team-credentials.json").read_text(encoding="utf-8"))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(ignore_https_errors=True)
        page.goto("https://localhost:8445", wait_until="networkidle", timeout=60000)
        page.locator("input[type=text]").first.fill("blue-team")
        page.locator("input[type=password]").fill(credentials["wazuh_password"])
        page.locator("button[type=submit]").click()
        page.get_by_text("Threat Hunting", exact=True).first.wait_for(timeout=60000)
        assert "Application Not Found" not in page.locator("body").inner_text()
        page.screenshot(path=str(ROOT / "evidence/blue-team-wazuh-overview.png"))
        page.get_by_text("Threat Hunting", exact=True).first.click()
        page.wait_for_timeout(10000)
        body = page.locator("body").inner_text()
        assert "Application Not Found" not in body and "/auth/login" not in page.url
        page.screenshot(path=str(ROOT / "evidence/blue-team-wazuh-events.png"))
        result = {"authenticated": True, "overview_loaded": True, "events_url": page.url,
                  "events_view_loaded": "Threat Hunting" in body, "body_summary": body[:4000],
                  "tls_ca_trust_bypassed_for_test": True,
                  "aws_mfa_login_tested": False}
        (ROOT / "evidence/blue-team-browser-verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
