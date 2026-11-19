"""Update the defensive rules on the existing WAF and Wazuh manager."""
import base64

from ops import ROOT, send, wait


WAF_RULE = "/opt/blue-team/rules/REQUEST-900-BLUE-TEAM.conf"
SIEM_RULE = "/var/ossec/etc/rules/blue_team_ctf.xml"
RULE = (ROOT / "cyber/files/REQUEST-900-BLUE-TEAM.conf").read_text(encoding="utf-8-sig")
CLASSIFICATIONS = (ROOT / "cyber/roles/siem/files/blue_team_ctf.xml").read_text(encoding="utf-8-sig")


def stage(variable, content):
    encoded = base64.b64encode(content.encode()).decode()
    return f"base64 -d > \"${variable}\" <<'BLUE_RULE'\n{encoded}\nBLUE_RULE\n"

def siem_update():
    return f"target={SIEM_RULE}\n" + r'''
backup=$(mktemp -d)
previous="$backup/previous"
candidate="$backup/candidate"
if test -f "$target"; then cp -p "$target" "$previous"; fi
trap 'rm -f "$candidate" "$previous"; rmdir "$backup"' EXIT
''' + stage("candidate", CLASSIFICATIONS) + r'''
grep_status=0
duplicates=$(grep -Ern --include='*.xml' --exclude=blue_team_ctf.xml \
    "id[[:space:]]*=[[:space:]]*[\"']11021[1-7][\"']" \
    /var/ossec/etc/rules /var/ossec/ruleset/rules) || grep_status=$?
case "$grep_status" in
    0) printf 'Conflicting rule IDs:\n%s\n' "$duplicates" >&2; exit 1 ;;
    1) ;;
    *) exit 1 ;;
esac
install -o root -g wazuh -m 0640 "$candidate" "$target"
if ! /var/ossec/bin/wazuh-analysisd -t; then
    if test -f "$previous"; then cp -p "$previous" "$target"; else rm -f "$target"; fi
    exit 1
fi
if ! systemctl restart wazuh-manager || ! systemctl is-active wazuh-manager; then
    if test -f "$previous"; then cp -p "$previous" "$target"; else rm -f "$target"; fi
    systemctl restart wazuh-manager
    exit 1
fi
'''


def waf_update():
    return f"target={WAF_RULE}\n" + r'''
container=aizoon-waf
test -f "$target"
docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$container" |
    grep -Fx 'MODSEC_RULE_ENGINE=DetectionOnly'
docker inspect --format '{{range .Mounts}}{{println .Source}}{{end}}' "$container" |
    grep -Fx "$target"
docker exec "$container" nginx -t
backup=$(mktemp)
cp -p "$target" "$backup"
trap 'rm -f "$backup"' EXIT
# Preserve the inode currently bound into the container.
if ! (
''' + stage("target", RULE) + r'''
); then
    cat "$backup" > "$target"
    exit 1
fi
if ! docker exec "$container" nginx -t || ! docker exec "$container" nginx -s reload; then
    cat "$backup" > "$target"
    docker exec "$container" nginx -t && docker exec "$container" nginx -s reload
    exit 1
fi
'''


if __name__ == "__main__":
    wait("siem", send("siem", siem_update(), "Update Blue Team Wazuh classifications"))
    wait("waf", send("waf", waf_update(), "Update Blue Team ModSecurity rules"))
