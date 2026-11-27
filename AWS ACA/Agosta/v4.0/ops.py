"""AWS personal account operations using the standard AWS credential chain."""
import json
import os
from pathlib import Path
import sys
import time

import boto3

ROOT = Path(__file__).resolve().parent
config_file = ROOT / "project" / "terraform.tfvars.json"
CONFIG = json.loads(config_file.read_text(encoding="utf-8-sig")) if config_file.exists() else {}
SESSION = boto3.Session(region_name=CONFIG.get("region", os.environ.get("AWS_DEFAULT_REGION", "us-east-1")))
SSM = SESSION.client("ssm")
(ROOT / "evidence").mkdir(exist_ok=True)


def outputs():
    data = json.loads((ROOT / "evidence" / "outputs.json").read_text(encoding="utf-8-sig"))
    return {key: value["value"] for key, value in data.items()}


def checked_account():
    expected = outputs()["account_id"]
    actual = SESSION.client("sts").get_caller_identity()["Account"]
    if actual != expected:
        raise RuntimeError("AWS profile does not match the account in Terraform outputs")
    return actual


def send(role, script, label):
    checked_account()
    instance = outputs()["instances"][role]["id"]
    result = SSM.send_command(
        InstanceIds=[instance], DocumentName="AWS-RunShellScript",
        Comment=label[:100], TimeoutSeconds=600,
        Parameters={"commands": ["bash <<'AIZOON_SCRIPT'\nset -euo pipefail\n" + script + "\nAIZOON_SCRIPT"], "executionTimeout": ["3600"]},
    )
    command_id = result["Command"]["CommandId"]
    manifest = ROOT / "evidence" / "commands.jsonl"
    with manifest.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"role": role, "id": command_id, "label": label}) + "\n")
    return command_id


def poll(role, command_id):
    result = SSM.get_command_invocation(CommandId=command_id, InstanceId=outputs()["instances"][role]["id"])
    result.pop("ResponseStartDateTime", None)
    result.pop("ResponseFinishDateTime", None)
    (ROOT / "evidence" / f"{command_id}.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps({key: result.get(key) for key in ["Status", "ResponseCode", "StandardOutputContent", "StandardErrorContent"]}, indent=2))


def wait(role, command_id, timeout=3600):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            result = SSM.get_command_invocation(CommandId=command_id, InstanceId=outputs()["instances"][role]["id"])
        except SSM.exceptions.InvocationDoesNotExist:
            time.sleep(5)
            continue
        if result["Status"] not in {"Pending", "InProgress", "Delayed"}:
            poll(role, command_id)
            if result["Status"] != "Success":
                raise RuntimeError(f"{role}: command {command_id} ended with {result['Status']}")
            return result["StandardOutputContent"]
        time.sleep(10)
    raise TimeoutError(f"{role}: inspect command {command_id}; execution may still be active")


if __name__ == "__main__":
    if sys.argv[1] == "send":
        print(send(sys.argv[2], Path(sys.argv[3]).read_text(encoding="utf-8-sig"), sys.argv[4]))
    elif sys.argv[1] == "poll":
        poll(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "nodes":
        print(json.dumps(SSM.describe_instance_information()["InstanceInformationList"], indent=2, default=str))
    elif sys.argv[1] == "exec":
        role = sys.argv[2]
        command_id = send(role, sys.stdin.read(), "Private lab verification")
        print("CommandId=" + command_id)
        for _ in range(20):
            time.sleep(1)
            try:
                result = SSM.get_command_invocation(CommandId=command_id, InstanceId=outputs()["instances"][role]["id"])
            except SSM.exceptions.InvocationDoesNotExist:
                continue
            if result["Status"] not in {"Pending", "InProgress", "Delayed"}:
                poll(role, command_id)
                break
        else:
            print("Still running; inspect using poll.")
    else:
        raise SystemExit("Use send ROLE FILE LABEL, poll ROLE COMMAND_ID, or nodes")
