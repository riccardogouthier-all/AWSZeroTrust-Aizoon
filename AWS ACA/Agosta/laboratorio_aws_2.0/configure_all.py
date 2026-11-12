"""Configure the three hosts, agents, metrics, audit logs and public CA export."""
import time

from configure import configure
from ops import ROOT, SSM, outputs, send, wait


def main():
    expected = {host["id"] for host in outputs()["instances"].values()}
    deadline = time.monotonic() + 900
    while True:
        online = {node["InstanceId"] for node in SSM.describe_instance_information()["InstanceInformationList"] if node["PingStatus"] == "Online"}
        if expected <= online:
            break
        if time.monotonic() >= deadline:
            raise TimeoutError("EC2 not Online in SSM; check IAM profile, routing and SSM agent")
        print("Waiting for the three SSM nodes...", flush=True)
        time.sleep(15)
    jobs = {role: configure(role) for role in ["siem", "web", "waf"]}
    for role, command in jobs.items():
        print(f"Waiting for {role}: {command}", flush=True)
        wait(role, command)
    for role, name in [("web", "agents"), ("waf", "agents"), ("waf", "audit-logs"), ("siem", "siem-metrics"), ("waf", "https-monitor")]:
        print(f"Configuring {role}: {name}", flush=True)
        wait(role, configure(role, ROOT / "configuration" / f"{name}.yml"))
    certificate = wait("waf", send("waf", "cat /opt/aizoon/tls/lab-ca.crt", "Export public lab CA"))
    if "-----BEGIN CERTIFICATE-----" not in certificate or "PRIVATE KEY" in certificate:
        raise RuntimeError("Unexpected CA export content")
    (ROOT / "lab-ca.crt").write_text(certificate, encoding="ascii")
    print("Configuration complete. WAF: https://" + outputs()["waf_ip"])


if __name__ == "__main__":
    main()
