# Difesa live

[Accessi AWS/Wazuh](../../../../Cyber%20CYS/Defence/ACCESSO_BLUE_TEAM_v3.1.md). Baseline DetectionOnly. Concordare finestra, marker e traffico normale di controllo.

## WAF — ruolo BlueDefence, sudo

```bash
sudo /opt/aizoon/set-waf-mode.sh On
sudo docker exec aizoon-waf nginx -t
# Rollback
sudo /opt/aizoon/set-waf-mode.sh DetectionOnly
```

File montato: /opt/blue-team/rules/REQUEST-900-BLUE-TEAM.conf. Backup prima di modificare; ID di regola univoci. Nuovi file: aggiungere mount in /opt/aizoon/start-waf.sh. Ricreare tramite lo script di modalità, nginx -t e smoke test. Modifiche solo dentro il container sono effimere.

## SIEM — raccolta e regole

Prima della finestra:

```bash
sudo sed -i 's#<logall_json>no</logall_json>#<logall_json>yes</logall_json>#' /var/ossec/etc/ossec.conf
sudo /var/ossec/bin/wazuh-analysisd -t && sudo systemctl restart wazuh-manager
```

Regole locali in /var/ossec/etc/rules/. Validare prima del restart; verificare agenti con /var/ossec/bin/agent_control -lc. A fine finestra ripetere la sostituzione yes→no e validazione/restart: gli archivi esistenti restano disponibili.

Fonti: /opt/blue-team/logs/{access.log,error.log,modsec_audit.log}; manager archives/archives.json e alerts/alerts.json sotto /var/ossec/logs. Inoltro audit: syslog con bt_waf_audit; archivi grezzi distinti dagli alert indicizzati.

Il ruolo operativo ha sudo su WAF/SIEM, sessioni registrate e durata massima un'ora; niente password nei terminali. Il login web Wazuh resta readonly. Conservare configurazioni/evidenze approvate e riportare le modifiche live nell'IaC prima di ricreare i nodi. Budget e switch restano separati dalle difese.
