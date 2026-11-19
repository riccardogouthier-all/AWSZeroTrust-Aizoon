"""Fixture statiche su input già decodificati. I motori reali si provano in staging."""
import csv
import re
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_challenges import MATRIX, compare
from check_public_assets import findings


class ChallengeTests(unittest.TestCase):
    def test_catalog_completeness(self):
        with MATRIX.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 118)
        self.assertEqual(len({row["key"] for row in rows}), len(rows))
        self.assertEqual(sum(row["docker_disabilitata"] == "si" for row in rows), 18)
        self.assertTrue(all(all(row.values()) for row in rows))
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "challenges.yml"
            source.write_text("\n".join("  key: " + row["key"] for row in rows))
            self.assertEqual(compare(source), ([], []))
            source.write_text("  key: newChallenge\n")
            added, missing = compare(source)
            self.assertEqual(added, ["newChallenge"])
            self.assertEqual(len(missing), 118)

    def test_asset_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ftp").mkdir()
            (root / "ftp/legal.md").touch()
            self.assertEqual(list(findings(root)), [])
            (root / "ftp/copy.bak").touch()
            (root / "main.tf").touch()
            self.assertEqual({p.as_posix() for p, _ in findings(root)},
                             {"ftp/copy.bak", "main.tf"})

    def test_siem_classification(self):
        rules = ElementTree.parse(ROOT / "roles/siem/files/blue_team_ctf.xml").findall("rule")
        expected = dict(zip(("110211", "110212", "110213", "110214", "110215", "110216", "110217"),
                            ("942100", "941100", "10011", "10012", "10013", "10014", "10015")))
        self.assertEqual({r.get("id") for r in rules}, expected.keys())
        for rule in rules:
            for key, waf_id in expected.items():
                event = f'ModSecurity: Warning. [id "{waf_id}"]'
                self.assertEqual(bool(re.search(rule.findtext("match"), event)), key == rule.get("id"))
            self.assertRegex("/opt/aizoon/logs/error.log", rule.findtext("location"))
            self.assertRegex("/opt/blue-team/logs/error.log", rule.findtext("location"))
            self.assertNotRegex("/opt/blue-team/logs/access.log", rule.findtext("location"))

    def test_waf_scope(self):
        conf = (ROOT / "files/REQUEST-900-BLUE-TEAM.conf").read_text(encoding="utf-8")
        ids = re.findall(r"\bid:(\d+)", conf)
        self.assertEqual(ids, ["10001", "10011", "10012", "10013", "10014", "10015"])
        self.assertNotRegex(conf.lower(), "score-board|api/challenges|10002")
        blocks = {re.search(r"id:(\d+)", block)[1]: block for block in
                  re.split(r"(?=^SecRule )", conf, flags=re.M) if re.search(r"id:\d+", block)}
        examples = {"10011": "/ftp/demo.txt", "10012": "/support/logs/demo",
                    "10013": "/metrics", "10014": "/api/Users/", "10015": "/api/BasketItems/42"}
        for key, example in examples.items():
            pattern = re.search(r'REQUEST_FILENAME "@rx ([^"]+)"', blocks[key])[1]
            self.assertRegex(example, pattern)
            self.assertNotRegex("/api/Challenges", pattern)
            self.assertNotRegex(example.replace("/", "/other/", 1), pattern)
        self.assertIn('"!@streq /ftp/legal.md"', blocks["10011"])
        self.assertIn('REQUEST_METHOD "@streq POST"', blocks["10014"])
        self.assertIn("ARGS:json.role|ARGS:role", blocks["10014"])
        qty = re.search(r'ARGS:json.quantity\|ARGS:quantity "@rx ([^"]+)"', blocks["10015"])[1]
        self.assertRegex("-1", qty)
        self.assertNotRegex("1", qty)
