"""Verifica righe audit v3 locali o archives.json sul SIEM. Output minimizzato."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


def inspect(record, marker, manager=False, agent="waf"):
    if not isinstance(record, dict):
        return None
    if manager:
        if record.get("agent", {}).get("name") != agent:
            return None
        if record.get("location") != "/opt/blue-team/logs/modsec_audit.log":
            return None
        prefix = "bt_waf_audit "
        raw = record.get("full_log", "")
        if not raw.startswith(prefix):
            return None
        record = json.loads(raw[len(prefix):])
    tx = record.get("transaction", {})
    uri = tx.get("request", {}).get("uri", "")
    if parse_qs(urlsplit(uri).query).get("bt_probe") != [marker]:
        return None
    producer = tx.get("producer", {})
    components = producer.get("components", [])
    ids = [str(msg.get("details", {}).get("ruleId", "")) for msg in tx.get("messages", [])]
    if (producer.get("secrules_engine") != "DetectionOnly" or "10001" not in ids
            or tx.get("response", {}).get("http_code") != 200
            or not any("CRS" in part.upper() for part in components)
            or not tx.get("unique_id")):
        return None
    return {"bt_probe": marker, "transaction_id": tx["unique_id"],
            "http": 200, "mode": "DetectionOnly", "rule_id": 10001,
            "crs": [part for part in components if "CRS" in part.upper()],
            "source": "manager" if manager else "waf"}


def search(path, marker, manager=False, agent="waf"):
    if not re.fullmatch("bt-[0-9a-f]{32}", marker):
        raise ValueError("Identificatore sonda non valido")
    with Path(path).open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if marker not in line:
                continue
            try:
                match = inspect(json.loads(line), marker, manager, agent)
            except (ValueError, TypeError, AttributeError):
                continue
            if match:
                return match
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file")
    parser.add_argument("marker")
    parser.add_argument("--manager", action="store_true")
    parser.add_argument("--agent", default="waf")
    args = parser.parse_args()
    evidence = search(args.file, args.marker, args.manager, args.agent)
    if not evidence:
        parser.exit(1, "Evento completo assente. Verificare origine, formato e ritardo di consegna.\n")
    print(json.dumps(evidence))
