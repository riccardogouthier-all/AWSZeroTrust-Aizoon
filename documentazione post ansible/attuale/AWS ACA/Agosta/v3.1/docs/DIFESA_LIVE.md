# Difesa live

[Accessi AWS/Wazuh](../../../../Cyber%20CYS/Defence/ACCESSO_BLUE_TEAM_v3.1.md). Baseline DetectionOnly. Concordare finestra, marker e traffico normale di controllo.

## WAF — sessione SSM BlueDefence con sudo

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

L’utente Blue Team con MFA apre direttamente la sessione SSM `SessionDocument-…-BlueDefence`. Ha sudo su WAF/SIEM, con registrazione CloudWatch e durata massima di un’ora. Il login web Wazuh resta in sola lettura. Conservare le modifiche approvate nell’IaC prima di ricreare i nodi.

Su un nuovo SIEM, `blue-init` inizializza le viste degli indici disponibili. Impostare `checks.fields: false` in `/usr/share/wazuh-dashboard/data/wazuh/config/wazuh.yml` e riavviare `wazuh-dashboard` per evitare scritture automatiche delle viste all'accesso. Se cambiano i mapping, aggiornare i campi delle viste con un account amministrativo.

Su Wazuh 4.14.10 eseguire [`patch_wazuh_readonly.sh`](../../../../../../AWS%20ACA/Agosta/v3.1/patch_wazuh_readonly.sh) sul SIEM come root. La selezione delle viste aggiorna i campi in memoria e lascia la scrittura delle viste all'amministratore. Lo script salva i tre file originali sotto `/root/wazuh-readonly-*` per il ripristino. Dopo un aggiornamento di Wazuh, verificare apertura e refresh di WEB con un utente Blue Team.
