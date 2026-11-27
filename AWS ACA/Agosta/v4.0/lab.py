"""Local operator helpers: EC2 start/stop/status, exports and private login setup."""
import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import time
from decimal import Decimal

from botocore.exceptions import ClientError

from ops import ROOT, SESSION, SSM, checked_account, outputs, send


def power(command, role="all", dry_run=False):
    account = checked_account()
    state = outputs()
    if SESSION.region_name != state["region"]:
        raise RuntimeError("AWS region does not match Terraform outputs")
    roles = [role] if role != "all" else ["waf", "web", "siem"]
    ids = [state["instances"][name]["id"] for name in roles]
    if len(set(ids)) != len(ids):
        raise RuntimeError("Duplicate instance IDs in Terraform outputs")
    ec2 = SESSION.client("ec2")
    reply = ec2.describe_instances(InstanceIds=ids)
    instances = {host["InstanceId"]: host for reservation in reply["Reservations"] for host in reservation["Instances"]}
    if set(instances) != set(ids):
        raise RuntimeError("Not all configured instances were returned by EC2")
    for name, instance_id in zip(roles, ids):
        host = instances[instance_id]
        tags = {tag["Key"]: tag["Value"] for tag in host.get("Tags", [])}
        if tags.get("Project") != state["project"] or tags.get("Role") != name:
            raise RuntimeError(f"Instance {instance_id} does not match project/role tags")
        print(f"{name}: {instance_id} - {host['State']['Name']}")
        if command != "status" and (host.get("RootDeviceType") != "ebs" or host["State"]["Name"] not in {"running", "stopped"}):
            raise RuntimeError(f"{name}: wait for a stable EBS-backed instance; no changes requested")
    if command == "status":
        return
    wanted = "running" if command == "start" else "stopped"
    change = [instance_id for instance_id in ids if instances[instance_id]["State"]["Name"] != wanted]
    if not change:
        print("Already in the requested state; no changes.")
        return
    if command == "start":
        budget = SESSION.client("budgets").describe_budget(
            AccountId=account, BudgetName=state["project"] + "-cost-budget")["Budget"]
        if budget["CostTypes"]["IncludeCredit"] or budget["CostTypes"]["IncludeRefund"] or budget["BudgetLimit"]["Unit"] != "USD":
            raise RuntimeError("Unexpected budget configuration; start refused")
        spend = budget.get("CalculatedSpend", {}).get("ActualSpend")
        if not spend:
            raise RuntimeError("Budget spend is not available yet; start refused")
        if Decimal(spend["Amount"]) >= Decimal(budget["BudgetLimit"]["Amount"]):
            raise RuntimeError("Monthly budget reached; start refused to preserve cost protection")
    method = ec2.start_instances if command == "start" else ec2.stop_instances
    try:
        method(InstanceIds=change, DryRun=dry_run)
    except ClientError as error:
        if dry_run and error.response["Error"]["Code"] == "DryRunOperation":
            print(f"Dry run passed: {command} permitted for {len(change)} instance(s); nothing changed.")
            return
        raise
    if dry_run:
        raise RuntimeError("Unexpected EC2 dry-run response")
    print(f"{command} requested for {len(change)} instance(s). Run 'python lab.py status' to check completion.")


def openssl(*args):
    binary = shutil.which("openssl")
    if binary:
        command = [binary] + [str(arg) for arg in args]
    elif os.name == "nt" and shutil.which("wsl"):
        def converted(arg):
            if isinstance(arg, Path):
                path = arg.resolve().as_posix()
                return "/mnt/" + path[0].lower() + path[2:]
            return str(arg)
        command = ["wsl", "-d", "Ubuntu", "--", "openssl"] + [converted(arg) for arg in args]
    else:
        raise RuntimeError("Install OpenSSL or use the existing Ubuntu WSL OpenSSL")
    return subprocess.run(command, check=True, capture_output=True).stdout


def secure_private():
    private = ROOT / "private"
    private.mkdir(exist_ok=True, mode=0o700)
    if os.name == "nt":
        owner = subprocess.check_output(["whoami"], text=True).strip()
        subprocess.run(["icacls", str(private), "/inheritance:r", "/grant:r",
                        owner + ":(OI)(CI)F", "*S-1-5-18:(OI)(CI)F", "*S-1-5-32-544:(OI)(CI)F"],
                       check=True, capture_output=True)
    else:
        private.chmod(0o700)
    return private


def completed(role, command):
    for _ in range(120):
        try:
            result = SSM.get_command_invocation(CommandId=command, InstanceId=outputs()["instances"][role]["id"])
        except SSM.exceptions.InvocationDoesNotExist:
            time.sleep(2)
            continue
        if result["Status"] == "Success":
            return result["StandardOutputContent"]
        if result["Status"] not in {"Pending", "Delayed", "InProgress"}:
            # Do not print full remote output: blue-init returns an encrypted secret.
            raise RuntimeError(f"SSM command {command}: {result['Status']}; inspect privately")
        time.sleep(2)
    raise TimeoutError(f"SSM command {command} still running; inspect before retrying")


def blue_init(username="blue-team"):
    if username not in {"blue-team", "blue-verifica"}:
        raise ValueError("Unsupported Blue Team username")
    account = checked_account()
    private = secure_private()
    path = private / f"{username}-credentials.json"
    iam = SESSION.client("iam")
    try:
        iam.get_login_profile(UserName=username)
        exists = True
    except iam.exceptions.NoSuchEntityException:
        exists = False
    if exists and not path.exists():
        raise RuntimeError("Existing console login: recover the original private files; no password reset performed")
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
        "username": username, "account_id": account,
        "console_url": f"https://{account}.signin.aws.amazon.com/console/",
        "aws_initial_password": "Bt9!" + secrets.token_urlsafe(24),
    }
    assert data["account_id"] == account and data["username"] == username
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    key, public = private / f"{username}-handoff.key", private / f"{username}-handoff.pub"
    if not key.exists():
        if exists:
            raise RuntimeError("Recover the original handoff private key before continuing")
        openssl("genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072", "-out", key)
    public.write_bytes(openssl("pkey", "-in", key, "-pubout"))
    if not exists:
        iam.create_login_profile(UserName=username, Password=data["aws_initial_password"], PasswordResetRequired=True)
    script = "python3 <<'PY'\nfrom pathlib import Path\nimport base64\n"
    remote_root = "/opt/blue-team" if username == "blue-team" else f"/opt/blue-team/{username}"
    script += f"p=Path({remote_root!r});p.mkdir(mode=0o700,parents=True,exist_ok=True)\n"
    script += f"BLUE_USERNAME={username!r}\n"
    script += f"(p/'handoff-public.pem').write_bytes(base64.b64decode({base64.b64encode(public.read_bytes()).decode()!r}))\n"
    source = base64.b64encode((ROOT / "provision_wazuh_blue.py").read_bytes()).decode()
    script += f"exec(compile(base64.b64decode({source!r}),'<blue-team-bootstrap>','exec'))\nPY\n"
    remote = json.loads(completed("siem", send("siem", script, "Create Blue Team Wazuh login with encrypted handoff")))
    cipher = private / ("wazuh-password.enc" if username == "blue-team" else f"{username}-wazuh-password.enc")
    cipher.write_bytes(base64.b64decode(remote["encrypted_password"]))
    data["wazuh_password"] = openssl("pkeyutl", "-decrypt", "-inkey", key, "-in", cipher,
                                       "-pkeyopt", "rsa_padding_mode:oaep", "-pkeyopt", "rsa_oaep_md:sha256").decode()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    (ROOT / f"evidence/{username}-wazuh-verification.json").write_text(json.dumps(remote["verification"], indent=2), encoding="utf-8")
    print(f"Logins initialized. Credentials are in private/{path.name}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["outputs", "ca", "blue-init", "status", "start", "stop"])
    parser.add_argument("--role", choices=["all", "waf", "web", "siem"], default="all", help="EC2 power commands only")
    parser.add_argument("--dry-run", action="store_true", help="Check EC2 permissions without changing instance state")
    parser.add_argument("--blue-user", choices=["blue-team", "blue-verifica"], default="blue-team", help="Login to initialize with blue-init")
    args = parser.parse_args()
    if args.command != "blue-init" and args.blue_user != "blue-team":
        parser.error("--blue-user is only available for blue-init")
    if args.command in {"status", "start", "stop"}:
        power(args.command, args.role, args.dry_run)
    elif args.role != "all" or args.dry_run:
        parser.error("--role and --dry-run are only available for EC2 power commands")
    elif args.command == "outputs":
        result = subprocess.run(["terraform", "-chdir=project", "output", "-json"], cwd=ROOT,
                                capture_output=True, text=True, check=True)
        json.loads(result.stdout)
        (ROOT / "evidence/outputs.json").write_text(result.stdout, encoding="utf-8")
        print("Terraform outputs exported to evidence/outputs.json")
    elif args.command == "ca":
        certificate = completed("waf", send("waf", "cat /opt/aizoon/tls/lab-ca.crt", "Export public WAF CA"))
        assert certificate.startswith("-----BEGIN CERTIFICATE-----")
        (ROOT / "lab-ca.crt").write_text(certificate, encoding="ascii")
        print("Public WAF CA exported. No private key exported.")
    else:
        blue_init(args.blue_user)


if __name__ == "__main__":
    os.umask(0o077)
    main()
