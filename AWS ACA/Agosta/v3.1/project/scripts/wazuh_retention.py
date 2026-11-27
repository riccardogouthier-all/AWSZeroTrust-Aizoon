"""Install the SIEM retention policies, or prune rotated raw archives."""
import base64
import json
from pathlib import Path
import re
import ssl
import sys
import tarfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def prune(root, now):
    cutoff = now - 7 * 86400
    for path in root.glob("[0-9][0-9][0-9][0-9]/*/ossec-archive-*"):
        if not re.fullmatch(r"ossec-archive-[0-9]{2}\.(?:log|json)\.(?:gz|sum)", path.name):
            continue
        if root not in path.resolve().parents or path.is_symlink():
            continue
        if path.is_file() and path.stat().st_mtime < cutoff:
            path.unlink()


def configure():
    with tarfile.open("/opt/aizoon/wazuh-install-files.tar") as archive:
        member = next(m for m in archive.getmembers() if m.name.endswith("wazuh-passwords.txt"))
        content = archive.extractfile(member).read().decode()
    match = re.search(r"indexer_username:\s*'admin'\s+indexer_password:\s*'([^']+)'", content)
    if not match:
        raise RuntimeError("Missing protected indexer bootstrap credential")
    token = base64.b64encode(("admin:" + match[1]).encode()).decode()
    context = ssl.create_default_context(cafile="/etc/wazuh-indexer/certs/root-ca.pem")
    headers = {"Authorization": "Basic " + token, "Content-Type": "application/json"}

    for name, age in (("alerts", "30d"), ("archives", "7d")):
        pattern = f"wazuh-{name}-4.x-*"
        path = f"https://127.0.0.1:9200/_plugins/_ism/policies/aizoon-{name}-retention"
        transition = {"state_name": "expire", "conditions": {"min_index_age": age}}
        policy = {
            "description": f"Retain {pattern} for {age}",
            "default_state": "retain",
            "states": [
                {"name": "retain", "actions": [], "transitions": [transition]},
                {"name": "expire", "actions": [{"delete": {}}], "transitions": []},
            ],
            "ism_template": {"index_patterns": [pattern], "priority": 100},
        }
        try:
            with urlopen(Request(path, headers=headers), context=context, timeout=30) as response:
                current = json.load(response)["policy"]
        except HTTPError as err:
            if err.code != 404:
                raise
            err.close()
            with urlopen(Request(path, json.dumps({"policy": policy}).encode(), headers, method="PUT"),
                         context=context, timeout=30) as response:
                current = json.load(response)["policy"]
            print("Created retention policy:", name)
        templates = current["ism_template"]
        if isinstance(templates, dict):
            templates = [templates]
        states = current["states"]
        if ([(t["index_patterns"], t["priority"]) for t in templates] != [([pattern], 100)]
                or current["default_state"] != "retain"
                or len(states) != 2 or states[0]["name"] != "retain" or states[0]["actions"]
                or states[0]["transitions"] != [transition]
                or states[1]["name"] != "expire" or states[1]["transitions"]
                or [set(action) - {"retry", "timeout"} for action in states[1]["actions"]] != [{"delete"}]):
            raise RuntimeError(f"Unexpected policy for {pattern}, review before changing it")
        print("Verified index template:", pattern, age)


if __name__ == "__main__":
    if sys.argv[1:] == ["--prune"]:
        prune(Path("/var/ossec/logs/archives"), time.time())
    elif not sys.argv[1:]:
        configure()
    else:
        raise SystemExit("Expected no arguments or --prune")
