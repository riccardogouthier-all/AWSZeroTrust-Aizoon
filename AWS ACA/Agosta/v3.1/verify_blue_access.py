"""Validate Blue Team policies with IAM simulation; no infrastructure writes."""
import json
from datetime import datetime, timezone
from ops import ROOT, SESSION, outputs, CONFIG, checked_account

iam = SESSION.client("iam")
ssm = SESSION.client("ssm")
account = SESSION.client("sts").get_caller_identity()["Account"]
assert account == checked_account()
users = [iam.get_user(UserName=name)["User"] for name in ("blue-team", "blue-verifica")]
role = iam.get_role(RoleName=f"{CONFIG.get('project', 'aizoon-personal')}-BlueDefence")["Role"]
result = {"checked_at": datetime.now(timezone.utc).isoformat(), "checks": []}


def check(principal, action, resource, allowed, mfa=True, document_check=True):
    contexts = ([{"ContextKeyName": "aws:MultiFactorAuthPresent", "ContextKeyType": "boolean",
                  "ContextKeyValues": [str(mfa).lower()]}] if mfa is not None else [])
    if ":user/" in principal:
        contexts.append({"ContextKeyName": "aws:username", "ContextKeyType": "string",
                         "ContextKeyValues": [principal.rsplit("/", 1)[1]]})
    if action == "ssm:StartSession" and document_check is not None:
        contexts.append({"ContextKeyName": "ssm:SessionDocumentAccessCheck", "ContextKeyType": "boolean",
                         "ContextKeyValues": [str(document_check).lower()]})
    reply = iam.simulate_principal_policy(PolicySourceArn=principal, ActionNames=[action],
                                         ResourceArns=[resource], ContextEntries=contexts)["EvaluationResults"][0]
    decision = reply["EvalDecision"]
    assert (decision == "allowed") == allowed, (action, resource, mfa, decision, reply.get("MissingContextValues"))
    result["checks"].append({"principal": principal, "action": action, "resource": resource,
                              "mfa": mfa, "decision": decision})


ec2_arn = lambda name: f"arn:aws:ec2:{SESSION.region_name}:{account}:instance/" + outputs()["instances"][name]["id"]
document = lambda name: f"arn:aws:ssm:{SESSION.region_name}:{account}:document/" + name
log = f"arn:aws:logs:{SESSION.region_name}:{account}:log-group:/{CONFIG.get('project', 'aizoon-personal')}/system:log-stream:test"
for user in users:
    check(user["Arn"], "logs:GetLogEvents", log, True)
    check(user["Arn"], "logs:GetLogEvents", log, False, mfa=False)
    check(user["Arn"], "logs:GetLogEvents", log, False, mfa=None)
    check(user["Arn"], "logs:GetLogEvents", log.replace(f"/{CONFIG.get('project', 'aizoon-personal')}/system", "/unrelated"), False)
    check(user["Arn"], "s3:GetObject", f"arn:aws:s3:::{outputs()['logs_bucket']}/AWSLogs/{account}/test.log", True)
    check(user["Arn"], "s3:GetObject", "arn:aws:s3:::unrelated-bucket/private.txt", False)
    check(user["Arn"], "iam:ChangePassword", user["Arn"], True, mfa=False)
    check(user["Arn"], "iam:CreateVirtualMFADevice", f"arn:aws:iam::{account}:mfa/{user['UserName']}", True, mfa=False)
    check(user["Arn"], "sts:AssumeRole", role["Arn"], False)
    check(user["Arn"], "sts:AssumeRole", role["Arn"], False, mfa=False)
    check(user["Arn"], "ssm:StartSession", ec2_arn("siem"), True)
    check(user["Arn"], "ssm:StartSession", ec2_arn("waf"), True, document_check=None)
    check(user["Arn"], "ssm:StartSession", ec2_arn("web"), False)
    check(user["Arn"], "ssm:StartSession", ec2_arn("siem"), False, document_check=False)
    check(user["Arn"], "ssm:StartSession", document(f"{CONFIG.get('project', 'aizoon-personal')}-WazuhDashboard"), True)
    check(user["Arn"], "ssm:StartSession", document(f"SessionDocument-{CONFIG.get('project', 'aizoon-personal')}-BlueDefence"), True)
    check(user["Arn"], "ssm:StartSession", document("SSM-SessionManagerRunShell"), False)
for name in ("waf", "siem"):
    check(role["Arn"], "ssm:StartSession", ec2_arn(name), True)
check(role["Arn"], "ssm:StartSession", ec2_arn("web"), False)
check(role["Arn"], "ssm:StartSession", ec2_arn("waf"), False, document_check=False)
check(role["Arn"], "ssm:StartSession", document(f"SessionDocument-{CONFIG.get('project', 'aizoon-personal')}-BlueDefence"), True)
check(role["Arn"], "ssm:StartSession", document("SSM-SessionManagerRunShell"), False)
for principal in [*(user["Arn"] for user in users), role["Arn"]]:
    for action, resource in [
        ("iam:CreateAccessKey", user["Arn"]), ("iam:PutUserPolicy", user["Arn"]),
        ("ec2:StopInstances", ec2_arn("waf")), ("ec2:RunInstances", "*"),
        ("logs:DeleteLogGroup", log), ("ssm:SendCommand", "*"),
    ]:
        check(principal, action, resource, False)
dashboard = json.loads(ssm.get_document(Name=f"{CONFIG.get('project', 'aizoon-personal')}-WazuhDashboard")["Content"])
assert dashboard["sessionType"] == "Port" and dashboard["properties"]["portNumber"] == "443"
assert "portNumber" not in dashboard.get("parameters", {})
defence = json.loads(ssm.get_document(Name=f"SessionDocument-{CONFIG.get('project', 'aizoon-personal')}-BlueDefence")["Content"])
assert defence["sessionType"] == "Standard_Stream" and defence["inputs"]["cloudWatchStreamingEnabled"]
assert defence["inputs"]["maxSessionDuration"] == "60"
assert defence["inputs"]["shellProfile"]["linux"] == "exec /bin/bash"
for user in users:
    name = user["UserName"]
    iam.get_login_profile(UserName=name)
    assert not iam.list_access_keys(UserName=name)["AccessKeyMetadata"]
    assert [g["GroupName"] for g in iam.list_groups_for_user(UserName=name)["Groups"]] == ["BlueTeamLogs"]
result.update(users=[user["Arn"] for user in users], role=role["Arn"],
              access_keys_created=False,
              mfa_enrollment_pending=[user["UserName"] for user in users
                                      if not iam.list_mfa_devices(UserName=user["UserName"])["MFADevices"]],
              mfa_login_end_to_end_tested=False)
(ROOT / "evidence/blue-team-iam-verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(f"PASS: {len(result['checks'])} permission checks, fixed HTTPS tunnel, recorded defence sessions, no access keys.")
print("MFA enrolment and live session checks must be completed by the relevant user.")
