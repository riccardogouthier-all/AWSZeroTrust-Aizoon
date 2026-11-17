# Blue Team — WAF / SIEM

Stack: nginx + ModSecurity/CRS, Juice Shop, Wazuh 4.14.10. Obiettivo di integrazione: stesso marker e transaction ID nell'audit WAF e nell'archivio manager; regola 10001, HTTP 200 in DetectionOnly.

| Documento | Contenuto |
|---|---|
| [Difese per sfida](DIFESE-SFIDE.md) · [Matrice](sfide.csv) | 118 criteri di verifica e regole WAF/SIEM per le operazioni coperte |
| [Accessi 3.1](../ACCESSO_BLUE_TEAM_v3.1.md) | AWS, Wazuh e ruolo operativo |
| [Runbook](RUNBOOK.md) | Stack esistente, Compose locale, Ansible su VM dedicate |
| [Flussi](SPIEGAZIONE-TEAM.md) | Log, correlazione e distinzione archivi/alert |
| [Compatibilità](AUDIT.md) | Varianti Cloud e confini dei playbook |
| [Validazione](VALIDAZIONE.md) | Prove eseguite e limiti |

Il codice Ansible è per VM Ubuntu dedicate. Sul laboratorio AWS già configurato usare l'adattatore [3.1](../../../AWS%20ACA/Agosta/v3.1/README.md): non avviare un secondo WAF sulla 443 né reinstallare il manager.
