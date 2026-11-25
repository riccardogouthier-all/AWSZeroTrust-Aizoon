# Progressi progetto — Laboratorio AWS v3.1

**Perimetro:** solo la versione 3.1 (`AWS ACA/Agosta/v3.1`), la versione finale su cui si faranno tutte le modifiche, con i contributi Cyber che vi sono integrati (`Cyber CYS/Defence/Finocchielli`) · **Stato al:** 25 novembre 2026 (ultimo lavoro nel repository: 19 novembre) · **Redatto da:** coordinamento progetto

## 1. Sintesi

Il laboratorio v3.1 è distribuito e verificato sull'account personale: tre EC2 (WAF, WEB, SIEM), telemetria, backup, protezione costi, switch di accensione/spegnimento, configurazione con Ansible via SSM e difese Cyber integrate. Il 19 novembre le tre EC2 sono state verificate operative e poi fermate (`stopped`). Il WAF è in `DetectionOnly`: osserva e segnala, non blocca. Restano aperte le prove sulle regole rimaste, il passaggio al blocco, il bootstrap su EC2 nuove, la revisione dei finding Checkov e gli interventi di ridondanza e sicurezza (sezione 7).

## 2. Architettura

| Risorsa | Configurazione |
|---|---|
| Rete | us-east-1, una AZ, VPC 10.20/16; subnet pubblica 10.20.1/24 e privata 10.20.2/24; IGW, NAT, endpoint S3 |
| WAF | t3.small, 20 GiB, 10.20.1.10 + EIP; nginx/ModSecurity/CRS, HTTPS pubblico, `DetectionOnly`; container `aizoon-waf` |
| WEB | t3.small, 20 GiB, 10.20.2.10; Juice Shop:3000 da digest Terraform; nessun IP pubblico |
| SIEM | m7i-flex.large (2 vCPU/8 GiB/50 GiB), 10.20.2.11; Wazuh 4.14.10; nessun IP pubblico |
| Gestione | SSM, SSH chiuso, IMDSv2, EBS cifrati, ruoli EC2/Backup dedicati |
| Telemetria | 13 allarmi, metriche memoria/disco/HTTPS, syslog CloudWatch, Flow Logs su S3, SNS→SQS |
| Backup | Tre EC2, giornaliero 02:00 UTC, retention un giorno |
| Costi | Budget 35 USD/mese prima dei crediti, stop automatico delle tre EC2 riarmato |

Flussi: Internet→WAF:443; WAF→WEB:3000; WAF/WEB→SIEM:1514/1515; uscita 80/443. TLS con CA privata e SAN IP. Juice Shop è intenzionalmente vulnerabile: nessun dato reale.

**Configurazione.** Il controller invia il playbook Ansible via SSM Run Command; Ansible gira localmente sulle EC2. WEB: installa Docker e crea il container Juice Shop dal digest, senza ricrearlo se esiste. WAF: bootstrap, monitor HTTPS, CA privata. SIEM: controlli su installazioni parziali e checksum dell'installer, utente Blue Team, regola padre 100100. Un nuovo stack usa il profilo Ansible; sullo state esistente impostare `configure_with_ansible=false` prima del plan.

**Difese Cyber integrate.** `apply_cyber.py` distribuisce senza reinstallare Wazuh la regola ModSecurity 10001 (sonda), le regole 10011–10015, l'audit JSON AHZ inoltrato come syslog `bt_waf_audit`, i template degli agenti e le classificazioni Wazuh 110213–110217. La matrice `sfide.csv` associa una difesa a ciascuna delle 118 sfide Juice Shop v20.4.0 (44 WEB, 19 IAM, 15 BUILD, 13 CRS, 8 con regole dedicate, 5 UI, 5 OPS, 5 PUB, 3 WEB3; 18 disabilitate in Docker). Il profilo Ansible per VM dedicate di Finocchielli non si usa sul lab: non eseguire `site.yml`.

## 3. Step eseguiti

| Data | Step | Esito |
|---|---|---|
| 13 nov | Deploy v3.1 sull'account personale: Terraform, cloud-init, ruoli IAM dedicati, budget, switch EC2, adattatore Cyber | Verificato (tre nodi SSM Online, Wazuh con quattro servizi attivi) |
| 13 nov | Verifiche: API WEB, browser Chromium/Firefox/WebKit desktop e mobile (sei pass), WAF 200 → 403 → ritorno a `DetectionOnly`, 13 allarmi OK, backup WEB COMPLETED, 34 simulazioni IAM Blue | Passate |
| 13 nov | Correlazione Cyber: marker `bt-fa7b0130b448488ba8ec286656026451`, stesso transaction ID su WAF e manager; due agenti Active, login Wazuh readonly e Threat Hunting | Verificata |
| 17 nov | Matrice di 118 difese per sfida (`sfide.csv`, `DIFESE-SFIDE.md`); catalogo confrontato con il digest di progetto; dieci test su dieci | Fatto |
| 19 nov | Integrazione delle difese Cyber sul lab; classificazione audit WAF in Wazuh; correlazione ModSecurity 10011 → Wazuh 110213 | Verificata; restano le altre classificazioni |
| 19 nov | Ansible integrato in v3.1: verifica via SSM sulle tre EC2 esistenti, play WEB `changed=0 failed=0`; Terraform `fmt`/`validate` passati | Fatto |
| 19 nov | Checkov 3.4.6: Terraform 176 pass / 18 finding, Ansible 4 pass / 5 finding, Ansible Cyber 7 / 3 | Eseguito, finding da rivedere |
| 19 nov | Accesso Blue Team: login AWS CLI con MFA confermato in CloudTrail; corretto il controllo IAM SSM e il tunnel Wazuh | Fatto; pagina da confermare dal browser dell'operatore |
| 19 nov | Tre EC2 verificate operative, poi fermate; budget a 35 USD con stop automatico riarmato | Fatto |
| 19 nov | Documentazione centralizzata (`attuale/`, `old/`) | Fatto |

Dopo il 19 novembre non risultano nuovi commit. Finestre di archiviazione grezza richiuse (`logall_json=no`), tunnel di collaudo chiusi, nessuna chiave API permanente per Blue.

## 4. Punti aperti

| Punto | Titolare |
|---|---|
| Collaudo dal vivo di 10012–10015 e delle classificazioni 110214–110217 | Blue |
| Blocco WAF non attivato | Blue |
| Pagina Wazuh `https://127.0.0.1:8443/` da confermare dal browser dell'operatore | Blue |
| Bootstrap Ansible su tre EC2 nuove (incluso l'installer Wazuh) non collaudato | Cloud |
| 18 finding Terraform e 5 Ansible di Checkov da rivedere (IAM, SSM, cifratura/retention CloudWatch, SNS, Backup, bucket log S3) | Cloud |
| SIEM a 2 vCPU sotto il riferimento (4 vCPU/8 GiB/50 GB); nessuno stress test | Cloud |
| Restore completo del backup non eseguito | Cloud |
| Test browser con bypass TLS; verifica CA/SAN separata | Cloud |
| GitHub Actions con approvazione non implementato | Cloud |
| Piano FREE con scadenza rilevata il 28/11/2026; budget AWS ritardato | Cloud |
| Retention archivi e indici; enrollment agenti protetto solo dai security group | Cloud + Blue |
| Esiti applicativi delle sfide (WEB, IAM, UI, BUILD, OPS, WEB3) | Titolari indicati in `sfide.csv` |

## 5. Rischi e vincoli

- Lo state Terraform è locale e privato: non applicare uno state vuoto sul deploy esistente; un'installazione per account (`blue-team` e `BlueTeamLogs` hanno nomi fissi).
- Una modifica a `user_data` può sostituire le VM; le modifiche live non tornano da sole nell'IaC. Revisionare sempre il plan.
- L'installer Wazuh della serie 4.14 è mutabile: verificare la patch 4.14.10 e fornire il SHA-256 dell'installer prima di un nuovo deploy.
- Il marker 10001 è una sonda di integrazione, non prova la copertura di tutte le famiglie CRS. Un alert indica una corrispondenza, non un attacco bloccato.
- Una sfida è "previene" solo dopo rifiuto verificato, stato integro e controllo positivo autorizzato.
- Lo stop delle EC2 lascia costi di NAT, IPv4, EBS, log e backup; lo start è rifiutato se il budget è raggiunto. `destroy` non va usato per fermare le lezioni.
- Non eseguire `verify_aws.py` o `waf_tests.py` durante una prova Red non concordata: hanno effetti.
- Segreti e log integrali restano in `private/` e `evidence/`, esclusi da Git; si conservano solo evidenze minimizzate.

## 6. Prossimi passi per team

### Team Cloud

1. Decidere sul piano crediti: la scadenza rilevata del piano FREE è il 28/11, a tre giorni.
2. Provare il restore completo del backup su tutti e tre i nodi.
3. Misurare il SIEM (ritardo marker, RAM, disco, iowait) e decidere il dimensionamento a 4 vCPU/8 GiB.
4. Collaudare il bootstrap Ansible su EC2 nuove e rivedere i finding Checkov.
5. Implementare GitHub Actions con approvazione; spostare lo state Terraform su backend remoto.
6. Verificare TLS con la CA del lab (SAN, scadenza) e togliere il bypass dai test browser.
7. Definire retention di archivi e indici; valutare gli interventi della sezione 7.
8. Controllare permessi, egress e gestione segreti (righe OPS e WEB3 della matrice).

### Team Cyber — Blue (difesa)

1. Collaudare sul lab le regole 10012–10015 e le classificazioni 110214–110217, con timestamp UTC, marker e transaction ID; `wazuh-analysisd -t`.
2. Confermare la pagina Wazuh `https://127.0.0.1:8443/` dal browser del membro Blue.
3. Promuovere al blocco in staging solo le regole senza regressioni; rollback a `DetectionOnly` se si rompe traffico normale.
4. Autenticare l'enrollment degli agenti Wazuh.
5. Assegnare e tracciare le righe WEB/IAM/UI/BUILD ai titolari e registrare per ciascuna segnale osservato ed esito applicativo.

### Team Cyber — Red (attacco)

1. Concordare con Blue e Cloud sorgente, finestra e marker delle prove.
2. Eseguire la prova asincrona (attacco → analisi Blue → modifica → replay) e la prova sincrona, con Blue che modifica WAF/SIEM durante la finestra.
3. Dopo il blocco, ripetere gli attacchi per confermare che la sfida "previene" davvero.
4. Riportare ogni test con ora UTC, marker, regola ed esito, senza segreti.
5. Non attaccare fuori finestra.

## 7. Da aggiungere per un'architettura ridondata e sicura

Stato attuale: una sola AZ, una sola istanza per ruolo, un solo NAT, backup con retention di un giorno, WAF in `DetectionOnly`. Il guasto di un nodo o della AZ ferma servizio o SIEM. Ogni modifica passa da plan revisionato.

### Ridondanza

| Priorità | Team | Intervento | Note |
|---|---|---|---|
| Alta | Cloud | Seconda AZ con subnet pubblica e privata duplicate | Elimina il guasto di AZ come punto unico. |
| Alta | Cloud | Application Load Balancer davanti a due WAF (uno per AZ) con health check; WAF non più raggiungibile direttamente | Sostituisce l'EIP singolo; certificato ACM. |
| Alta | Cloud | Due WEB, uno per AZ, dietro i WAF | Juice Shop è senza stato. |
| Alta | Cloud | Un NAT gateway per AZ con route table separate | Oggi se il NAT cade, WEB e SIEM perdono l'uscita. |
| Media | Cloud | Auto Scaling group con minimo 1 per ruolo e AMI preconfezionate | Richiede bootstrap idempotente (già in Ansible). |
| Media | Cloud + Blue | SIEM: secondo nodo (cluster Wazuh) o almeno snapshot dell'indexer su S3 con ripristino provato | Punto unico più critico per i log. |
| Media | Cloud | Backup: retention di 7–30 giorni, copia in altra regione o account, restore provato su tutti i nodi | Oggi un giorno. |
| Media | Cloud + Blue | Log Flow/CloudWatch/S3 con versioning, replica e lifecycle | Retention anche per archivi e indici Wazuh. |
| Bassa | Cloud + Blue | Piano di continuità: RTO/RPO, runbook di failover, prova periodica | Definire cosa si accetta di perdere. |

### Sicurezza

| Priorità | Team | Intervento | Note |
|---|---|---|---|
| Alta | Blue | Passare il WAF da `DetectionOnly` a blocco, regola per regola, dopo staging e controllo dei falsi positivi | Rollback documentato; confermare con prova Red. |
| Alta | Cloud | MFA su tutti gli utenti IAM, nessuna chiave permanente, restringere `AdministratorAccess` del titolare | MFA Blue già confermata. |
| Alta | Blue | Enrollment agenti Wazuh con autenticazione e validazione del certificato del manager | Oggi solo security group. |
| Alta | Cloud | Certificato TLS pubblico (ACM/Let's Encrypt) o CA privata distribuita ai client; chiudere i test con bypass TLS | SAN corretti, scadenze monitorate. |
| Alta | Cloud | State Terraform su backend remoto (S3 cifrato, versioning, lock) | Evita perdita o state vuoto. |
| Media | Cloud | AWS WAF o Shield davanti all'ALB per DDoS e rate limiting | Oltre a ModSecurity. |
| Media | Cloud + Blue | GuardDuty, CloudTrail multi-regione su bucket protetto, Config e Security Hub; allarmi su root, IAM e security group | Il SIEM oggi raccoglie solo log di host. |
| Media | Cloud | Segreti in Secrets Manager/SSM Parameter Store con rotazione; KMS gestito dal cliente per EBS, S3 e log | Oggi chiave di default. |
| Media | Cloud | Pipeline CI con `terraform validate`, Checkov e test; chiudere i finding rimasti | Pianificata, non implementata. |
| Media | Cloud | Patching con SSM Patch Manager; pin Wazuh e immagini a digest | Installer 4.14 mutabile. |
| Bassa | Cloud | VPC endpoint per SSM, S3 e CloudWatch; NACL e SG minimi | Meno superficie e meno costo NAT. |
| Bassa | Cloud | Allarmi di costo e salute per ogni componente nuovo; SIEM a 4 vCPU/8 GiB | Raddoppiare i nodi raddoppia i costi: rivedere il budget da 35 USD. |

Il team Cloud realizza gli interventi infrastrutturali; il team Blue valida regole, agenti e SIEM; Red prova l'esito. Seconda AZ, secondo NAT, ALB e nodi doppi aumentano la spesa in modo sensibile: per il laboratorio basta il livello "Alta", il resto resta progetto di riferimento.
