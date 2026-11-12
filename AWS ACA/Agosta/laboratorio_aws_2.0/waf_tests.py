"""Controlled CRS detection/blocking check against this lab, then restore baseline."""
import json
import ssl
import time
import urllib.error
import urllib.request

from ops import ROOT, SSM, outputs, send

state = outputs()
base = "https://" + state["waf_ip"]
context = ssl.create_default_context(cafile=str(ROOT / "lab-ca.crt"))
probe = "/rest/products/search?q=%3Cscript%3Ealert%281%29%3C%2Fscript%3E"


def request(path):
    for attempt in range(15):
        try:
            with urllib.request.urlopen(base + path, context=context, timeout=15) as response:
                response.read()
                return response.status
        except urllib.error.HTTPError as error:
            return error.code
        except (urllib.error.URLError, TimeoutError):
            if attempt == 14:
                raise
            time.sleep(2)


def mode(value):
    command = send("waf", "/opt/aizoon/set-waf-mode.sh " + value, "Controlled WAF mode " + value)
    for _ in range(30):
        time.sleep(1)
        try:
            result = SSM.get_command_invocation(CommandId=command, InstanceId=state["instances"]["waf"]["id"])
        except SSM.exceptions.InvocationDoesNotExist:
            continue
        if result["Status"] == "Success":
            return command
        if result["Status"] not in {"Pending", "InProgress", "Delayed"}:
            raise RuntimeError(result["StandardErrorContent"])
    raise TimeoutError("WAF mode command did not finish")


results = {}
try:
    results["detection_only_probe_status"] = request(probe)
    assert results["detection_only_probe_status"] == 200
    results["blocking_command"] = mode("On")
    results["blocking_probe_status"] = request(probe)
    results["blocking_normal_page_status"] = request("/")
    assert results["blocking_probe_status"] == 403
    assert results["blocking_normal_page_status"] == 200
finally:
    results["restore_baseline_command"] = mode("DetectionOnly")
    results["final_normal_page_status"] = request("/")
    results["final_mode"] = "DetectionOnly"
    (ROOT / "evidence" / "waf-test-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(json.dumps(results, indent=2))
