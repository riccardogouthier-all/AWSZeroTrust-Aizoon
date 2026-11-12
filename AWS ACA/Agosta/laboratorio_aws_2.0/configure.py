"""Run local Ansible playbooks on managed EC2 nodes through SSM."""
import argparse
import base64
import json
from pathlib import Path

from ops import ROOT, outputs, send, wait


def render_playbook(content, role, state, images):
    replacements = {
        "LAB_WAF_IP": state["waf_ip"],
        "LAB_WEB_IP": state["instances"]["web"]["private_ip"],
        "LAB_SIEM_IP": state["instances"]["siem"]["private_ip"],
        "LAB_ROLE": role,
        "LAB_REGION": state["region"],
        "LAB_PROJECT": state["project"],
        "LAB_JUICE_IMAGE": images["juice_shop"],
        "LAB_WAF_IMAGE": images["waf"],
    }
    for token, value in replacements.items():
        content = content.replace(token, value)
    return content


def configure(role, playbook=None):
    playbook = Path(playbook) if playbook else ROOT / "configuration" / f"{role}.yml"
    images = json.loads((ROOT / "images.lock.json").read_text())
    content = render_playbook(playbook.read_text(encoding="utf-8"), role, outputs(), images)
    encoded = base64.b64encode(content.encode()).decode()
    script = """export DEBIAN_FRONTEND=noninteractive
cloud-init status --wait >/dev/null
apt-get -o DPkg::Lock::Timeout=180 update -qq
apt-get -o DPkg::Lock::Timeout=180 install -y -qq ansible-core curl jq
mkdir -p /opt/aizoon
chmod 700 /opt/aizoon
"""
    script += f"printf '%s' '{encoded}' | base64 -d > /opt/aizoon/{playbook.name}\n"
    script += f"ansible-playbook -i localhost, /opt/aizoon/{playbook.name}\n"
    return send(role, script, f"Ansible {playbook.name} on {role}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=["web", "waf", "siem"])
    parser.add_argument("playbook", nargs="?")
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()
    command = configure(args.role, args.playbook)
    print(command, flush=True)
    if args.wait:
        wait(args.role, command)
