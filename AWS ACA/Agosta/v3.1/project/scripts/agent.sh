
# ---- agent.sh: agent Wazuh su web e WAF ----
# Il SIEM impiega diversi minuti: attende la porta di registrazione (max ~60 min).
for _ in $(seq 1 360); do
  (exec 3<>/dev/tcp/"${SIEM_PRIVATE}"/1515) 2>/dev/null && break
  sleep 10
done

curl -fsSL https://packages.wazuh.com/key/GPG-KEY-WAZUH | gpg --dearmor --yes -o /usr/share/keyrings/wazuh.gpg
echo 'deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main' > /etc/apt/sources.list.d/wazuh.list
$APT update
version=$(apt-cache madison wazuh-agent | awk -v series="${WAZUH_SERIES}." -v exact="${WAZUH_VERSION:-}" '
    !found && ((exact != "" && index($3, exact "-") == 1) || (exact == "" && index($3, series) == 1)) {
        print $3
        found=1
    }')
test -n "$version"
WAZUH_MANAGER="${SIEM_PRIVATE}" WAZUH_AGENT_NAME="${ROLE}" $APT install "wazuh-agent=$version"
echo "$version" > /opt/aizoon/wazuh-agent-version

# Raccolta log container; sul WAF anche access/error/audit ModSecurity.
inputs='<localfile><log_format>json</log_format><location>/var/lib/docker/containers/*/*-json.log</location></localfile>'
if [ "$ROLE" = waf ]; then
  inputs="${inputs}<localfile><log_format>apache</log_format><location>/opt/aizoon/logs/access.log</location></localfile>"
  inputs="${inputs}<localfile><log_format>syslog</log_format><location>/opt/aizoon/logs/error.log</location></localfile>"
  inputs="${inputs}<localfile><log_format>json</log_format><location>/opt/aizoon/logs/modsec_audit.log</location></localfile>"
fi
sed -i "s#</ossec_config>#${inputs}</ossec_config>#" /var/ossec/etc/ossec.conf

systemctl enable wazuh-agent
systemctl restart wazuh-agent
