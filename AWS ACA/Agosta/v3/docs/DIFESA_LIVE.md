# Blue Team: difesa durante le prove

Per entrare nella console e in Wazuh seguire la [guida breve in Defence](../../../../Cyber%20CYS/Defence/ACCESSO_BLUE_TEAM_v3.md). Le credenziali vengono consegnate privatamente dal titolare.

Il profilo normale consulta log e dashboard. Il ruolo `aizoon-personal-BlueDefence`, con MFA, permette `sudo` sulle sole VM WAF e SIEM tramite un documento SSM dedicato. Non attribuisce amministrazione IAM, fatturazione o creazione EC2. L'amministrazione locale può modificare file e fermare servizi: usarla per gli interventi concordati durante la prova.

## Prima della prova

Concordare finestra, identificatore delle richieste e modalità sincrona o asincrona. Se serve conservare anche tutti gli eventi grezzi, sul SIEM:

```bash
sudo sed -i 's#<logall_json>no</logall_json>#<logall_json>yes</logall_json>#' /var/ossec/etc/ossec.conf
sudo /var/ossec/bin/wazuh-analysisd -t && sudo systemctl restart wazuh-manager
```

## WAF: blocco e nuove regole

Sul WAF, per attivare il blocco:

```bash
sudo /opt/aizoon/set-waf-mode.sh On
sudo docker exec aizoon-waf nginx -t
```

Il file custom montato nel container è `/opt/blue-team/rules/REQUEST-900-BLUE-TEAM.conf`. Conservare una copia prima di modificarlo e usare ID di regola univoci. Per un nuovo file occorre aggiungere il mount in `/opt/aizoon/start-waf.sh`. Dopo una modifica ricreare il container tramite lo script di cambio modalità, verificare `nginx -t` e provare una richiesta normale. Le modifiche fatte soltanto dentro il container non sopravvivono alla ricreazione.

Per tornare alla baseline:

```bash
sudo /opt/aizoon/set-waf-mode.sh DetectionOnly
```

## SIEM: regole di rilevamento

Le regole locali Wazuh sono in `/var/ossec/etc/rules/`. Dopo una modifica validare prima di riavviare:

```bash
sudo /var/ossec/bin/wazuh-analysisd -t
sudo systemctl restart wazuh-manager
sudo /var/ossec/bin/agent_control -lc
```

L'account web Wazuh `blue-team` rimane in lettura. Il ruolo operativo amministra lo stack dal sistema operativo; un eventuale nuovo ruolo di scrittura nella dashboard deve essere assegnato esplicitamente.

## Alla fine

Conservare evidenze minimizzate e le configurazioni approvate; ripristinare DetectionOnly se la prova è terminata. Chiudere la raccolta grezza:

```bash
sudo sed -i 's#<logall_json>yes</logall_json>#<logall_json>no</logall_json>#' /var/ossec/etc/ossec.conf
sudo /var/ossec/bin/wazuh-analysisd -t && sudo systemctl restart wazuh-manager
```

Questo non cancella gli archivi già raccolti. Le sessioni amministrative sono configurate per inviare gli output a `/aizoon-personal/blue-team-sessions`: non stampare password o chiavi. Le modifiche live non rientrano automaticamente nel Terraform; riportare quelle approvate nei file replicabili prima di ricreare una VM.
