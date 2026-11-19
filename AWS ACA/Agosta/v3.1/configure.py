"""Run the v3.1 Ansible playbook locally on each EC2 through SSM."""
import argparse
import base64
import json
import re
import zlib

from ops import ROOT, SESSION, checked_account, outputs, send, wait


def payload(role, settings, verify_only):
    files = {"site.yml": (ROOT / "ansible/site.yml").read_text(encoding="utf-8")}
    if not verify_only:
        scripts = {"web": ["agent.sh"], "waf": ["waf.sh", "waf-health.sh", "agent.sh"], "siem": []}
        for name in scripts[role]:
            files[name] = "set -euo pipefail\n" + (ROOT / "project/scripts" / name).read_text(encoding="utf-8")
    files["vars.json"] = json.dumps({"node_role": role, "bootstrap": settings, "verify_only": verify_only})
    bundle = base64.b64encode(zlib.compress(json.dumps(files).encode())).decode()
    return f"""cloud-init status --wait >/dev/null
if ! command -v ansible-playbook >/dev/null; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get -o DPkg::Lock::Timeout=180 -qq update
    apt-get -o DPkg::Lock::Timeout=180 -qq -y --no-install-recommends install ansible-core
fi
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
cd "$work"
python3 <<'PY'
import base64, json, zlib
from pathlib import Path
for name, text in json.loads(zlib.decompress(base64.b64decode({bundle!r}))).items():
    Path(name).write_text(text, encoding="utf-8")
PY
ansible-playbook -i localhost, site.yml --extra-vars @vars.json
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Check existing nodes without running service bootstrap")
    parser.add_argument("--wazuh-installer-sha256", help="SHA-256 of the reviewed official Wazuh installer")
    args = parser.parse_args()
    checked_account()
    state = outputs()
    settings = state.get("ansible_bootstrap")
    if not args.verify_only and not settings:
        parser.error("Use Terraform outputs from the Ansible deployment profile, or --verify-only on an existing lab.")
    if not args.verify_only:
        if not re.fullmatch(r"[0-9a-fA-F]{64}", args.wazuh_installer_sha256 or ""):
            parser.error("Provide the reviewed installer SHA-256 with --wazuh-installer-sha256.")
        settings = {**settings, "WAZUH_INSTALLER_SHA256": args.wazuh_installer_sha256.lower()}
    if SESSION.region_name != state["region"]:
        raise RuntimeError("AWS region does not match Terraform outputs")
    roles = ("siem", "web", "waf")
    ids = [state["instances"][role]["id"] for role in roles]
    reservations = SESSION.client("ec2").describe_instances(InstanceIds=ids)["Reservations"]
    hosts = {host["InstanceId"]: host for reservation in reservations for host in reservation["Instances"]}
    if len(set(ids)) != len(roles) or set(hosts) != set(ids):
        raise RuntimeError("Expected three distinct EC2 from Terraform outputs")
    for role, instance_id in zip(roles, ids):
        host = hosts[instance_id]
        tags = {tag["Key"]: tag["Value"] for tag in host.get("Tags", [])}
        if host["State"]["Name"] != "running" or tags.get("Project") != state["project"] or tags.get("Role") != role:
            raise RuntimeError(f"{role}: unexpected instance state or tags")
    online = SESSION.client("ssm").describe_instance_information(
        Filters=[{"Key": "InstanceIds", "Values": ids}]
    )["InstanceInformationList"]
    if {host["InstanceId"] for host in online if host["PingStatus"] == "Online"} != set(ids):
        raise RuntimeError("Wait for all three EC2 to be online in SSM")
    for role in roles:
        wait(role, send(role, payload(role, settings or {}, args.verify_only), f"Ansible {'verify' if args.verify_only else 'configure'} {role}"))


if __name__ == "__main__":
    main()
