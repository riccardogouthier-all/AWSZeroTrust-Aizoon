"""Local operator helpers. blue-init creates logins; outputs/ca export metadata."""
import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import time

from ops import ROOT, SESSION, SSM, checked_account, outputs, send


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


def blue_init():
    account = checked_account()
    private = secure_private()
    path = private / "blue-team-credentials.json"
    iam = SESSION.client("iam")
    try:
        iam.get_login_profile(UserName="blue-team")
        exists = True
    except iam.exceptions.NoSuchEntityException:
        exists = False
    if exists and not path.exists():
        raise RuntimeError("Existing console login: recover the original private files; no password reset performed")
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
        "username": "blue-team", "account_id": account,
        "console_url": f"https://{account}.signin.aws.amazon.com/console/",
        "aws_initial_password": "Bt9!" + secrets.token_urlsafe(24),
    }
    assert data["account_id"] == account
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    key, public = private / "blue-team-handoff.key", private / "blue-team-handoff.pub"
    if not key.exists():
        if exists:
            raise RuntimeError("Recover the original handoff private key before continuing")
        openssl("genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072", "-out", key)
    public.write_bytes(openssl("pkey", "-in", key, "-pubout"))
    if not exists:
        iam.create_login_profile(UserName="blue-team", Password=data["aws_initial_password"], PasswordResetRequired=True)
    script = "python3 <<'PY'\nfrom pathlib import Path\nimport base64\n"
    script += "p=Path('/opt/blue-team');p.mkdir(mode=0o700,exist_ok=True)\n"
    script += f"(p/'handoff-public.pem').write_bytes(base64.b64decode({base64.b64encode(public.read_bytes()).decode()!r}))\n"
    source = base64.b64encode((ROOT / "provision_wazuh_blue.py").read_bytes()).decode()
    script += f"exec(compile(base64.b64decode({source!r}),'<blue-team-bootstrap>','exec'))\nPY\n"
    remote = json.loads(completed("siem", send("siem", script, "Create Blue Team Wazuh login with encrypted handoff")))
    cipher = private / "wazuh-password.enc"
    cipher.write_bytes(base64.b64decode(remote["encrypted_password"]))
    data["wazuh_password"] = openssl("pkeyutl", "-decrypt", "-inkey", key, "-in", cipher,
                                       "-pkeyopt", "rsa_padding_mode:oaep", "-pkeyopt", "rsa_oaep_md:sha256").decode()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    (ROOT / "evidence/blue-team-wazuh-verification.json").write_text(json.dumps(remote["verification"], indent=2), encoding="utf-8")
    print("Logins initialized. Credentials are in private/blue-team-credentials.json; no password printed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["outputs", "ca", "blue-init"])
    args = parser.parse_args()
    if args.command == "outputs":
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
        blue_init()


if __name__ == "__main__":
    os.umask(0o077)
    main()
