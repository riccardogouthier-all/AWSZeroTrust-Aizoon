"""Validate Blue Team policies with IAM simulation; no infrastructure writes."""
import json
from datetime import datetime, timezone
from ops import ROOT, SESSION, outputs, CONFIG, checked_account

iam = SESSION.client("iam")
ssm = SESSION.client("ssm")
account = SESSION.client("sts").get_caller_identity()["Account"]
assert account == checked_account()
user = iam.get_user(UserName="blue-team")["User"]
role = iam.get_role(RoleName=f"{CONFIG.get('project', 'aizoon-personal')}-BlueDefence")["Role"]
result = {"checked_at": datetime.now(timezone.utc).isoformat(), "checks": []}


def check(principal, action, resource, allowed, mfa=True, document_check=True):
    contexts = ([{"ContextKeyName": "aws:MultiFactorAuthPresent", "ContextKeyType": "boolean",
                  "ContextKeyValues": [str(mfa).lower()]}] if mfa is not None else [])
    if action == "ssm:StartSession":
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
check(user["Arn"], "logs:GetLogEvents", log, True)
check(user["Arn"], "logs:GetLogEvents", log, False, mfa=False)
check(user["Arn"], "logs:GetLogEvents", log, False, mfa=None)
check(user["Arn"], "logs:GetLogEvents", log.replace(f"/{CONFIG.get('project', 'aizoon-personal')}/system", "/unrelated"), False)
check(user["Arn"], "s3:GetObject", f"arn:aws:s3:::{outputs()['logs_bucket']}/AWSLogs/{account}/test.log", True)
check(user["Arn"], "s3:GetObject", "arn:aws:s3:::unrelated-bucket/private.txt", False)
check(user["Arn"], "iam:ChangePassword", user["Arn"], True, mfa=False)
check(user["Arn"], "iam:CreateVirtualMFADevice", f"arn:aws:iam::{account}:mfa/blue-team", True, mfa=False)
check(user["Arn"], "sts:AssumeRole", role["Arn"], True)
check(user["Arn"], "sts:AssumeRole", role["Arn"], False, mfa=False)
check(user["Arn"], "ssm:StartSession", ec2_arn("siem"), True)
check(user["Arn"], "ssm:StartSession", ec2_arn("waf"), False)
check(user["Arn"], "ssm:StartSession", ec2_arn("siem"), False, document_check=False)
check(user["Arn"], "ssm:StartSession", document(f"{CONFIG.get('project', 'aizoon-personal')}-WazuhDashboard"), True)
check(user["Arn"], "ssm:StartSession", document(f"SessionDocument-{CONFIG.get('project', 'aizoon-personal')}-BlueDefence"), False)
check(user["Arn"], "ssm:StartSession", document("SSM-SessionManagerRunShell"), False)
for name in ("waf", "siem"):
    check(role["Arn"], "ssm:StartSession", ec2_arn(name), True)
check(role["Arn"], "ssm:StartSession", ec2_arn("web"), False)
check(role["Arn"], "ssm:StartSession", ec2_arn("waf"), False, document_check=False)
check(role["Arn"], "ssm:StartSession", document(f"SessionDocument-{CONFIG.get('project', 'aizoon-personal')}-BlueDefence"), True)
check(role["Arn"], "ssm:StartSession", document("SSM-SessionManagerRunShell"), False)
for principal in (user["Arn"], role["Arn"]):
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
trust = role["AssumeRolePolicyDocument"]["Statement"][0]
assert trust["Principal"]["AWS"] == user["Arn"]
assert trust["Condition"]["Bool"]["aws:MultiFactorAuthPresent"] == "true"
assert set(trust["Condition"]["StringEquals"]["sts:RoleSessionName"]) == {"blue-team", "blue-team-live"}
assert iam.get_login_profile(UserName="blue-team")["LoginProfile"]["PasswordResetRequired"]
assert not iam.list_access_keys(UserName="blue-team")["AccessKeyMetadata"]
assert [g["GroupName"] for g in iam.list_groups_for_user(UserName="blue-team")["Groups"]] == ["BlueTeamLogs"]
result.update(user=user["Arn"], role=role["Arn"], password_reset_required=True,
              access_keys_created=False, mfa_enrollment_pending=not iam.list_mfa_devices(UserName="blue-team")["MFADevices"],
              mfa_login_end_to_end_tested=False)
(ROOT / "evidence/blue-team-iam-verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(f"PASS: {len(result['checks'])} permission checks, fixed HTTPS tunnel, recorded defence sessions, password reset, no access keys.")
print("MFA activation and end-user login remain to be completed by the Blue Team member.")
