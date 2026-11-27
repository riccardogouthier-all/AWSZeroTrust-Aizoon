# Rilascio AWS 4.0

**Stato al 27 novembre 2026.** Codice e guide per ricreare l'ambiente nel nuovo account AWS con Terraform e Ansible, con dati, log, account Blue Team, indirizzi e CA nuovi.

| Area | Intervento e verifica |
|---|---|
| Backup | Quattro slot al giorno, 7 giorni di retention, obiettivo RPO 12 ore. Avviati manualmente tre job il 27 novembre. Tutti `COMPLETED` alle 18:12 CET. Un recovery point per nodo, tre AMI disponibili e tre snapshot EBS cifrati e completati. L'allarme CloudWatch dei job è attivo. |
| Restore | Ripristinati tutti e tre i nodi da backup precedenti in una VPC isolata. Verificati HTTPS, applicazione, servizi Wazuh e arrivo in SIEM di un marker innocuo dal WAF ripristinato. Rimosse le risorse temporanee. |
| Stato del lab dopo il backup | Tre EC2 in esecuzione, status checks EC2 OK, tre nodi SSM Online, HTTPS 200 con CA verificata e quattro servizi Wazuh attivi. |
| Terraform e IAM | State Free migrato su S3 cifrato, versionato e con lock nativo. Ruoli delle EC2 con diniego alle letture Parameter Store, verificato mantenendo operativo SSM. Il nuovo account ricrea i ruoli e parte con un backend proprio. |
| Ansible e Wazuh | Bootstrap su tre EC2 nuove con Wazuh 4.14.11. Il profilo Blue Team readonly ha aperto e ricaricato la vista WEB senza tentare scritture sugli indici. Il Free in servizio usa 4.14.10. |
| WEB | Bridge Docker dedicato con filtro egress. Su EC2 temporanea accesso dal WAF e blocco in uscita sono passati prima e dopo il riavvio Docker. Corretto lo shebang nel pacchetto SSM e coperto con test locale. |
| TLS | CA privata, IP nel SAN, scadenza 13 dicembre 2026 UTC. Sei prove desktop e viewport mobile in Chromium, Firefox e WebKit senza bypass. |
| SIEM | 2 vCPU e 8 GiB per il carico misurato. A 2 marker al secondo, 80/80 ricevuti, p95 1,58 secondi, RAM disponibile circa 5 GiB, disco 40%, iowait massimo 3%. Il Free ha rifiutato l'istanza per il confronto a 4 vCPU. |
| Retention | 7 giorni per i backup e i file di archivio ruotati, 30 giorni per gli indici Wazuh degli alert. Policy ISM e timer provati sul SIEM di collaudo. |
| Checkov e costi | [Scansione completa](CHECKOV.md) e [stima prudenziale](STIMA_COSTI_AWS.md). |

## Verifiche rinviate

Prima sessione di backup automatico con il nuovo calendario. Deploy completo nel nuovo account, prova del pacchetto SSM corretto su EC2 nuova e osservazione della scadenza effettiva degli indici e archivi. Approvazione e OIDC di GitHub Actions sospesi. La correzione delle viste Wazuh vanno ricontrollate con la versione dell'installer usata al deploy.
