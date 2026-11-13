"""Apply Finocchielli's config to the existing Gouthier nodes via SSM.
Preserve the current CA, container name and agent enrollment; no second stack.
"""
import base64,json
from ops import ROOT,send,wait

rule=(ROOT/'cyber/files/REQUEST-900-BLUE-TEAM.conf').read_text(encoding='utf-8-sig')
template=(ROOT/'cyber/roles/agents/templates/inputs.xml.j2').read_text(encoding='utf-8-sig')
assert 'id:10001' in rule and '{% else %}' in template and '{% endif %}' in template
check=(ROOT/'cyber/tools/check_evidence.py').read_text(encoding='utf-8-sig')
def remote(code):return "python3 <<'PY'\n"+code+"\nPY\n"
def transfer(path,text):
 return f"from pathlib import Path\nimport base64\np=Path({path!r});p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode({base64.b64encode(text.encode()).decode()!r}))\n"

# Do not race cloud-init or reconfigure a partially installed manager.
for role in ('waf','web','siem'):
 wait(role,send(role,'cloud-init status --wait >/dev/null\ncloud-init status --long','Cyber preflight cloud-init'))

code=transfer('/opt/blue-team/rules/REQUEST-900-BLUE-TEAM.conf',rule)+transfer('/opt/blue-team/check_evidence.py',check)+r'''
import shutil
root=Path('/opt/aizoon');backup=root/'pre-cyber';backup.mkdir(exist_ok=True,mode=0o700)
for name in ('waf.env','start-waf.sh'):
 if not (backup/name).exists():shutil.copy2(root/name,backup/name)
logs=Path('/opt/blue-team/logs')
if not logs.exists():logs.symlink_to(root/'logs',target_is_directory=True)
assert logs.resolve()==(root/'logs').resolve()
p=root/'waf.env';text=p.read_text();values=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
values.update(MODSEC_RULE_ENGINE='DetectionOnly',MODSEC_AUDIT_LOG_TYPE='Serial',MODSEC_AUDIT_LOG_PARTS='AHZ')
p.write_text(''.join(k+'='+v+'\n' for k,v in values.items()))
p=root/'start-waf.sh';text=p.read_text();mount='    -v /opt/blue-team/rules/REQUEST-900-BLUE-TEAM.conf:/etc/modsecurity.d/owasp-crs/rules/REQUEST-900-BLUE-TEAM.conf:ro '+chr(92)+chr(10)
if '/opt/blue-team/rules/REQUEST-900-BLUE-TEAM.conf:' not in text:
 lines=text.splitlines(keepends=True);index=next(i for i,l in enumerate(lines) if '-v /opt/aizoon/logs:' in l);lines.insert(index+1,mount);text=''.join(lines)
text=text.replace('--log-opt max-size=10m --log-opt max-file=3','--log-opt max-size=5m --log-opt max-file=2').replace('-p 443:8443','-p 10.20.1.10:443:8443')
p.write_text(text)
'''
# Configuration is validated before restarting the original container.
script=remote(code)+"""
bash -n /opt/aizoon/start-waf.sh
chown 101:adm /opt/aizoon/logs
chmod 2750 /opt/aizoon/logs
chgrp 101 /opt/aizoon/tls/server.key
chmod 640 /opt/aizoon/tls/server.key
cat > /etc/logrotate.d/blue-team-waf <<'EOF'
/opt/blue-team/logs/*.log {
    su root adm
    daily
    maxsize 20M
    rotate 4
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
}
EOF
docker rm -f aizoon-waf
/opt/aizoon/start-waf.sh
sleep 4
docker exec aizoon-waf nginx -t
logrotate -d /etc/logrotate.d/blue-team-waf
"""
wait('waf',send('waf',script,'Apply cyber WAF rule, audit and rotation'))
for role in ('waf','web'):
 block=template.split('%}',1)[1].split('{% else %}',1)[0] if role=='waf' else template.split('{% else %}',1)[1].split('{% endif %}',1)[0]
 code=transfer('/opt/blue-team/check_evidence.py',check)+r'''
import re,shutil,subprocess
p=Path('/var/ossec/etc/ossec.conf');backup=p.with_name('ossec.conf.pre-cyber')
if not backup.exists():shutil.copy2(p,backup)
text=p.read_text()
text=re.sub(r'<!-- BEGIN BLUE TEAM INPUTS -->.*?<!-- END BLUE TEAM INPUTS -->','',text,flags=re.S)
def retain(match):
 part=match.group();return '' if any(x in part for x in ('/var/lib/docker/containers/','/opt/aizoon/logs/','/opt/blue-team/logs/')) else part
text=re.sub(r'<localfile>.*?</localfile>',retain,text,flags=re.S)
'''+f"block={block!r}\n"
 if role=='web':code+="logpath=subprocess.check_output(['docker','inspect','--format','{{.LogPath}}','juice-shop'],text=True).strip();assert logpath.startswith('/var/lib/docker/containers/') and logpath.endswith('-json.log');block=block.replace(\"{{ bt_docker_log.stdout.split(' ', 1)[1] | e }}\",logpath)\n"
 code+="assert '{{' not in block and '{%' not in block\ntext=text.replace('</ossec_config>','<!-- BEGIN BLUE TEAM INPUTS -->'+block+'<!-- END BLUE TEAM INPUTS -->\\n</ossec_config>',1);p.write_text(text)\n"
 script=remote(code)+"/var/ossec/bin/wazuh-logcollector -t || { cp /var/ossec/etc/ossec.conf.pre-cyber /var/ossec/etc/ossec.conf; exit 1; }\napt-mark hold wazuh-agent\nsystemctl restart wazuh-agent\nsystemctl is-active wazuh-agent\n"
 wait(role,send(role,script,'Apply cyber agent inputs '+role))
script=remote(transfer('/opt/blue-team/check_evidence.py',check))+"""
for package in wazuh-manager wazuh-indexer wazuh-dashboard; do
 test "$(dpkg-query -W -f='${Version}' "$package" | cut -d- -f1)" = 4.14.10
done
apt-mark hold wazuh-manager wazuh-indexer wazuh-dashboard filebeat
sed -i 's#<logall_json>no</logall_json>#<logall_json>yes</logall_json>#' /var/ossec/etc/ossec.conf
/var/ossec/bin/wazuh-analysisd -t
systemctl restart wazuh-manager
systemctl is-active wazuh-manager wazuh-indexer wazuh-dashboard filebeat
"""
wait('siem',send('siem',script,'Adopt cyber SIEM settings without reinstall'))
print('Cyber configuration applied; archives enabled for verification window.')
