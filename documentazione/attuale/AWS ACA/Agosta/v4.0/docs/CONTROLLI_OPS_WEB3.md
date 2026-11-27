# Controlli OPS e WEB3

Perimetro AWS 4.0 e otto righe OPS/WEB3 di `sfide.csv`. Sul lab Free solo il WAF ha IP pubblico, con ingresso TCP 443. WEB riceve 3000 dal security group WAF. SIEM riceve 1514–1515 dai gruppi WEB e WAF. Tutti e tre richiedono IMDSv2 con hop limit 1. L'uscita 80/443 degli host rimane disponibile per bootstrap e servizi esterni.

| Righe della matrice | Evidenza e decisione |
|---|---|
| OPS · fetch remoto | Il container attivo sul lab Free può uscire in HTTPS. Sui nuovi WEB Ansible configura un bridge dedicato che rifiuta le nuove connessioni in uscita dal container, anche verso l'host. Su una EC2 di prova, HTTPS dall'host e l'accesso dal WAF hanno funzionato prima e dopo il riavvio di Docker. Seconda esecuzione Ansible con zero modifiche. |
| OPS · chiavi esposte e segreti in IaC | IAM Simulator ha negato accesso al backend S3, lettura Secrets Manager e creazione ruoli dal profilo EC2. La policy Terraform nega le letture di Parameter Store. Il diniego è stato applicato e verificato da WAF, WEB e SIEM nel lab Free, con SSM operativo. Il collaudo del deploy GitHub con OIDC e approvazione è sospeso in attesa del repository. |
| OPS · documenti e immagini | Usare materiale di test senza dati personali. Verificare il contenuto e i metadati prima della pubblicazione. |
| WEB3 · seed phrase | Nessuna seed o chiave wallet nei file del lab, nelle immagini o nello state. Eventuali credenziali di test appartengono al gestore dei segreti e richiedono una regola di accesso dedicata. |
| WEB3 · mint e saldo | I controlli di idoneità, uso singolo della prova e invarianti contabili appartengono ai contratti. I test vanno eseguiti su contratti e asset di prova. |

Prima del nuovo deploy verificare il diniego Parameter Store insieme al funzionamento di SSM e CloudWatch. Il ruolo infrastrutturale resta separato da quello dell'operatore Blue. Git e i log pubblici devono contenere solo evidenze minimizzate.
