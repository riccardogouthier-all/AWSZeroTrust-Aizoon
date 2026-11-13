"""Prova HTTP del solo backend Juice Shop, con bypass dei proxy di sistema."""
import argparse
import json
import ssl
import uuid
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def run(url, ca=None):
    target = urlsplit(url)
    if (target.scheme not in ("http", "https") or not target.hostname
            or target.path not in ("", "/") or target.query or target.fragment or target.username):
        raise ValueError("Usare l'origine del WAF, senza percorso o parametri")
    if target.scheme == "http" and target.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("Per la VM usare HTTPS e il certificato del WAF")
    opener = build_opener(ProxyHandler({}), NoRedirect(),
                          HTTPSHandler(context=ssl.create_default_context(cafile=ca)))
    root = url.rstrip("/") + "/"
    marker = "bt-" + uuid.uuid4().hex
    for endpoint in (root, root + "?" + urlencode({"bt_probe": marker})):
        with opener.open(endpoint, timeout=10) as response:
            body = response.read(1024 * 1024).lower()
            if response.status != 200 or b"juice shop" not in body or b"burp suite" in body:
                raise ValueError("Risposta inattesa: controllare backend, porta e proxy")
    return {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "bt_probe": marker, "baseline_http": 200, "probe_http": 200}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8088")
    parser.add_argument("--ca", help="Certificato pubblico del WAF o della CA")
    args = parser.parse_args()
    print(json.dumps(run(args.url, args.ca)))
