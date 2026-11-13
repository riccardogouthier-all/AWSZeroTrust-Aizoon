
# ---- siem.sh: Wazuh all-in-one (serie ${WAZUH_SERIES}) ----
cd /opt/aizoon
curl -fsSL -o wazuh-install.sh "https://packages.wazuh.com/${WAZUH_SERIES}/wazuh-install.sh"
chmod 700 wazuh-install.sh

# Output su file privato: le password generate non finiscono nei log cloud-init.
if [ ! -e /opt/aizoon/wazuh-install.complete ]; then
  bash /opt/aizoon/wazuh-install.sh -a > /opt/aizoon/wazuh-install-private.log 2>&1
  touch /opt/aizoon/wazuh-install.complete
fi

# Archivia tutti gli eventi JSON ricevuti.
sed -i 's#<logall_json>no</logall_json>#<logall_json>yes</logall_json>#' /var/ossec/etc/ossec.conf

cat > /var/ossec/etc/rules/aizoon_rules.xml <<'EOF'
<group name="aizoon,web,">
  <rule id="100100" level="7">
    <match>ModSecurity</match>
    <description>Aizoon lab WAF ModSecurity event</description>
  </rule>
</group>
EOF
chown root:wazuh /var/ossec/etc/rules/aizoon_rules.xml
chmod 640 /var/ossec/etc/rules/aizoon_rules.xml

# Nessun upgrade automatico del repository Wazuh.
sed -i 's/^deb /#deb /' /etc/apt/sources.list.d/wazuh.list

/var/ossec/bin/wazuh-analysisd -t
systemctl restart wazuh-manager
