"""Runs on SIEM as administrator. Password leaves the node only RSA-encrypted."""
import base64
import json
from pathlib import Path
import re
import secrets
import ssl
import tarfile
import time
import urllib.error
import urllib.request
from urllib.parse import quote, urlencode

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

USER = "blue-team"
ROOT = Path("/opt/blue-team")
ROOT.mkdir(mode=0o700, exist_ok=True)
envelope = ROOT / "blue-team-handoff.enc"
with tarfile.open("/opt/aizoon/wazuh-install-files.tar") as archive:
    member = next(m for m in archive.getmembers() if m.name.endswith("wazuh-passwords.txt"))
    password_file = archive.extractfile(member).read().decode()


def credential(kind, user):
    match = re.search(rf"{kind}_username:\s*'{re.escape(user)}'\s+{kind}_password:\s*'([^']+)'", password_file)
    assert match, "Missing protected bootstrap credential"
    return match.group(1)


index_context = ssl.create_default_context(cafile="/etc/wazuh-indexer/certs/root-ca.pem")
api_context = ssl.create_default_context(cafile="/var/ossec/api/configuration/ssl/server.crt")
# The API's generated certificate is pinned locally; it does not name 127.0.0.1.
api_context.check_hostname = False


def basic(user, password):
    return "Basic " + base64.b64encode((user + ":" + password).encode()).decode()


def request(base, path, auth, context, method="GET", data=None, expected=(200,)):
    headers = {"Authorization": auth, "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(base + path, body, headers, method=method)
    try:
        with urllib.request.urlopen(req, context=context, timeout=30) as response:
            status = response.status
            result = json.loads(response.read())
    except urllib.error.HTTPError as error:
        status = error.code
        error.close()
        result = {}
    assert status in expected, f"{method} {path}: HTTP {status}"
    if result.get("error") and isinstance(result["error"], int):
        raise RuntimeError(f"Wazuh API error {result['error']}")
    return status, result


index_base = "https://127.0.0.1:9200"
index_admin = basic("admin", credential("indexer", "admin"))


def index(path, method="GET", data=None, expected=(200,)):
    return request(index_base, path, index_admin, index_context, method, data, expected)


status, existing = index("/_plugins/_security/api/internalusers/" + USER, expected=(200, 404))
assert status == 404 or envelope.exists(), "Existing user has no matching handoff; do not reset it"
index("/_plugins/_security/api/roles/blue_team_logs_ro", "PUT", {
    "cluster_permissions": ["cluster_composite_ops_ro"],
    "index_permissions": [{
        "index_patterns": ["wazuh-*", ".kibana*", ".opensearch_dashboards*"],
        "allowed_actions": ["read"],
    }],
    "tenant_permissions": [{"tenant_patterns": ["global_tenant"], "allowed_actions": ["kibana_all_read"]}],
}, expected=(200, 201))

new_password = None
if status == 404:
    new_password = "Bt9!" + secrets.token_urlsafe(24)
    public_key = serialization.load_pem_public_key((ROOT / "handoff-public.pem").read_bytes())
    encrypted = public_key.encrypt(new_password.encode(), padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    envelope.write_bytes(encrypted)
    envelope.chmod(0o600)
    index("/_plugins/_security/api/internalusers/" + USER, "PUT", {
        "password": new_password,
        "backend_roles": ["blue_team_readonly"],
        "opendistro_security_roles": ["blue_team_logs_ro"],
        "attributes": {"display_name": "Blue Team"},
    }, expected=(200, 201))
else:
    assert set(existing[USER].get("opendistro_security_roles", [])) <= {"blue_team_logs_ro", "kibana_read_only"}
    index("/_plugins/_security/api/internalusers/" + USER, "PATCH", [
        {"op": "replace", "path": "/opendistro_security_roles", "value": ["blue_team_logs_ro"]},
    ])

# The first dashboard visit must not require granting writes to the reader.
dashboard_context = ssl.create_default_context(cafile="/etc/wazuh-indexer/certs/root-ca.pem")
dashboard_context.check_hostname = False
dashboard_headers = {"Authorization": index_admin, "osd-xsrf": "true", "Content-Type": "application/json"}
for pattern in ("wazuh-alerts-*", "wazuh-monitoring-*", "wazuh-statistics-*"):
    saved_url = "https://127.0.0.1/api/saved_objects/index-pattern/" + quote(pattern, safe="")
    try:
        with urllib.request.urlopen(urllib.request.Request(saved_url, headers=dashboard_headers),
                                    context=dashboard_context, timeout=30) as response:
            assert json.load(response)["attributes"]["title"] == pattern
        continue
    except urllib.error.HTTPError as error:
        assert error.code == 404, f"Dashboard pattern lookup: HTTP {error.code}"
        error.close()
    fields_url = "https://127.0.0.1/api/index_patterns/_fields_for_wildcard?" + urlencode({"pattern": pattern})
    with urllib.request.urlopen(urllib.request.Request(fields_url, headers=dashboard_headers),
                                context=dashboard_context, timeout=30) as response:
        fields = json.load(response)["fields"]
    attributes = {"title": pattern, "fields": json.dumps(fields)}
    if pattern == "wazuh-alerts-*":
        attributes["timeFieldName"] = "timestamp"
    req = urllib.request.Request(saved_url, json.dumps({"attributes": attributes}).encode(),
                                 dashboard_headers, method="POST")
    with urllib.request.urlopen(req, context=dashboard_context, timeout=30) as response:
        assert response.status in (200, 201)

api_base = "https://127.0.0.1:55000"
api_admin = basic("wazuh-wui", credential("api", "wazuh-wui"))
_, login = request(api_base, "/security/user/authenticate", api_admin, api_context)
api_token = "Bearer " + login["data"]["token"]


def api(path, method="GET", data=None):
    return request(api_base, path, api_token, api_context, method, data)[1]


roles = api("/security/roles")["data"]["affected_items"]
readonly = next(role for role in roles if role["name"] == "readonly")
rules = api("/security/rules")["data"]["affected_items"]
# Match the same context key used by this installed dashboard's admin mapping.
context_key = next(key for rule in rules for key in ("user_name", "username")
                   if rule.get("rule", {}).get("FIND", {}).get(key) == "admin")
match_rule = next((rule for rule in rules if rule["name"] == "blue_team_readonly"), None)
desired_rule = {"FIND": {context_key: USER}}
if match_rule is None:
    match_rule = api("/security/rules", "POST", {"name": "blue_team_readonly", "rule": desired_rule})["data"]["affected_items"][0]
else:
    assert match_rule["rule"] == desired_rule
assert set(match_rule.get("roles", [])) <= {readonly["id"]}, "Unexpected privileged mapping"
if readonly["id"] not in match_rule.get("roles", []):
    api(f"/security/roles/{readonly['id']}/rules?rule_ids={match_rule['id']}", "POST")

for attempt in range(10):
    _, assumed = request(api_base, "/security/user/authenticate/run_as", api_admin, api_context,
                         "POST", {context_key: USER, "backend_roles": ["blue_team_readonly"],
                                  "roles": ["blue_team_logs_ro"]})
    readonly_token = "Bearer " + assumed["data"]["token"]
    status, agents = request(api_base, "/agents?select=id,name,status", readonly_token, api_context, expected=(200, 401))
    if status == 200:
        break
    # New RBAC mappings can briefly invalidate tokens across the API workers.
    time.sleep(2)
else:
    raise RuntimeError("Read-only mapping did not become available")
denied, _ = request(api_base, f"/security/rules/{match_rule['id']}", readonly_token, api_context,
                    "PUT", {"name": "blue_team_readonly", "rule": desired_rule}, expected=(403,))
verification = {"manager_role": "readonly", "agents_read": agents["data"]["total_affected_items"],
                "security_administration_denied": denied == 403}
if new_password:
    auth = basic(USER, new_password)
    _, auth_info = request(index_base, "/_plugins/_security/authinfo", auth, index_context)
    assert set(auth_info["roles"]) <= {"blue_team_logs_ro", "own_index"}
    _, count = request(index_base, "/wazuh-alerts-*/_count", auth, index_context)
    denied, _ = request(index_base, "/_plugins/_security/api/internalusers", auth, index_context, expected=(403,))
    verification.update(index_roles=auth_info["roles"], readable_alerts=count["count"], index_admin_denied=denied == 403)
assert verification["agents_read"] >= 3
print(json.dumps({"user": USER, "encrypted_password": base64.b64encode(envelope.read_bytes()).decode(),
                  "verification": verification}))
