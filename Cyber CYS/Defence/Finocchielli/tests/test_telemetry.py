import copy
import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from check_evidence import inspect, search
from probe import run

MARK = "bt-" + "a" * 32
SAMPLE = {"transaction": {"unique_id": "synthetic-id", "request": {"uri": "/?bt_probe=" + MARK},
          "response": {"http_code": 200}, "producer": {"secrules_engine": "DetectionOnly",
          "components": ["OWASP_CRS/fixture"]}, "messages": [{"details": {"ruleId": "10001"}}]}}


def archive(record):
    return {"agent": {"name": "waf"}, "location": "/opt/blue-team/logs/modsec_audit.log",
            "full_log": "bt_waf_audit " + json.dumps(record)}


class Telemetry(unittest.TestCase):
    def test_audit_and_archive(self):
        self.assertEqual(inspect(SAMPLE, MARK)["transaction_id"],
                         inspect(archive(SAMPLE), MARK, manager=True)["transaction_id"])

    def test_require_mode_crs_rule_and_status(self):
        for section, key, value in [("producer", "secrules_engine", "Enabled"),
                                    ("producer", "components", []),
                                    ("response", "http_code", 403),
                                    ("request", "uri", "/?bt_probe=other")]:
            sample = copy.deepcopy(SAMPLE)
            sample["transaction"][section][key] = value
            self.assertIsNone(inspect(sample, MARK))
        sample = copy.deepcopy(SAMPLE)
        sample["transaction"]["messages"] = []
        self.assertIsNone(inspect(sample, MARK))

    def test_archive_provenance(self):
        for key, value in [("agent", {"name": "web"}), ("full_log", json.dumps(SAMPLE)),
                           ("location", "/tmp/other.log")]:
            self.assertIsNone(inspect(dict(archive(SAMPLE), **{key: value}), MARK, True))

    def test_file_with_partial_line(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit"
            path.write_text(MARK + "\n" + json.dumps(SAMPLE), encoding="utf-8")
            self.assertEqual(search(path, MARK)["rule_id"], 10001)
            self.assertIsNone(search(path, "bt-" + "b" * 32))

    def test_http_responses_offline(self):
        with patch("probe.build_opener") as builder:
            response = builder.return_value.open.return_value.__enter__.return_value
            response.status = 200
            response.read.return_value = b"<title>OWASP Juice Shop</title>"
            marker = run("http://127.0.0.1:8088")["bt_probe"]
            self.assertEqual(builder.return_value.open.call_args.args[0],
                             "http://127.0.0.1:8088/?bt_probe=" + marker)
            response.read.return_value = b"<title>Burp Suite</title>"
            with self.assertRaises(ValueError):
                run("http://127.0.0.1:8088")
            response.status = 403
            response.read.return_value = b"Juice Shop"
            with self.assertRaises(ValueError):
                run("http://127.0.0.1:8088")

    def test_http_control(self):
        class Handler(BaseHTTPRequestHandler):
            content = b"<title>OWASP Juice Shop</title>"
            force_block = False

            def do_GET(self):
                self.send_response(403 if self.force_block and "?" in self.path else 200)
                self.end_headers()
                self.wfile.write(self.content)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        url = f"http://127.0.0.1:{server.server_port}"
        try:
            try:
                result = run(url)
            except URLError as exc:
                if getattr(exc.reason, "winerror", None) == 10013:
                    self.skipTest("Windows nega la connessione loopback (10013)")
                raise
            self.assertRegex(result["bt_probe"], r"^bt-[a-f0-9]{32}$")
            Handler.force_block = True
            with self.assertRaises(HTTPError):
                run(url)
            Handler.content = b"<title>Burp Suite</title>"
            with self.assertRaises(ValueError):
                run(url)
        finally:
            server.shutdown()
            worker.join()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
