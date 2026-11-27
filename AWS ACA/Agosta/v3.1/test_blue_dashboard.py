"""Verify that a read-only user can open and refresh an agent via a pinned local tunnel."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import socket
import ssl
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

from ops import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8445)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--cert-sha256", required=True, help="Dashboard leaf fingerprint verified via SSM")
    parser.add_argument("--credentials", type=Path, default=ROOT / "private/blue-team-credentials.json")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9]{3,8}", args.agent_id) or not re.fullmatch(r"[0-9a-fA-F]{64}", args.cert_sha256):
        parser.error("Expected numeric agent ID and SHA-256 hex fingerprint")

    host = "127.0.0.1"
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    tls.check_hostname = False
    tls.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, args.port), timeout=10) as sock, tls.wrap_socket(sock) as conn:
        fingerprint = hashlib.sha256(conn.getpeercert(binary_form=True)).hexdigest()
    assert fingerprint == args.cert_sha256.lower(), "Dashboard TLS fingerprint mismatch"

    base = f"https://{host}:{args.port}"
    credentials = json.loads(args.credentials.read_text(encoding="utf-8"))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(ignore_https_errors=True)
        login = context.request.post(
            base + "/auth/login",
            data={"username": credentials["username"], "password": credentials["wazuh_password"]},
            headers={"osd-xsrf": "true"},
            timeout=15000,
        )
        assert login.status == 200, f"Wazuh login returned HTTP {login.status}"
        page = context.new_page()
        writes = []

        def check_request(request):
            path = urlsplit(request.url).path
            if request.method in {"POST", "PUT", "DELETE"} and path.startswith("/api/saved_objects/index-pattern/"):
                writes.append((request.method, path))

        page.on("request", check_request)
        page.goto(base + "/app/wz-home", wait_until="domcontentloaded")
        page.get_by_text("Threat Hunting", exact=True).first.wait_for(timeout=60000)
        route = f"/app/endpoints-summary#/agents?tab=welcome&agent={args.agent_id}"
        page.goto(base + route, wait_until="domcontentloaded")
        for phase in ("open", "refresh"):
            if phase == "refresh":
                page.reload(wait_until="domcontentloaded")
            page.wait_for_function(
                "(agent) => location.hash.includes('agent=' + agent) && /Operating system|Inventory/i.test(document.body.innerText)",
                arg=args.agent_id, timeout=60000,
            )
            page.wait_for_timeout(3000)
            assert not writes, f"Unexpected writes to saved index patterns: {writes}"
            body = page.locator("body").inner_text()
            assert not re.search(r"security_exception|no permissions|indices:data/write/index", body, re.I)
            print(f"PASS: read-only agent {phase}, no index-pattern writes", flush=True)
        browser.close()


if __name__ == "__main__":
    main()
