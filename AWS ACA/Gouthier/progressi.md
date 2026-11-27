# Progressi progetto — Laboratorio AWS v3.1

**Perimetro:** versione 3.1 (`AWS ACA/Agosta/v3.1`) e contributi Cyber integrati (`Cyber CYS/Defence/Finocchielli`) · **Stato al:** 27 novembre 2026 · **Redatto da:** coordinamento progetto

## 1. Sintesi

Il laboratorio v3.1 è distribuito sull'account personale, con WAF in `DetectionOnly`. Sono stati verificati backup e restore, bootstrap Ansible su tre EC2 nuove, TLS con CA del lab, accesso Wazuh in sola lettura e migrazione dello state su S3. Il nuovo account ripartirà da Terraform e Ansible con dati vuoti. Restano l'attivazione dell'approvazione GitHub, le verifiche nel nuovo account e le prove Cyber già pianificate.

## 2. Architettura

| Risorsa | Configurazione |
|---|---|
| Rete | us-east-1, una AZ, VPC 10.20/16; subnet pubblica 10.20.1/24 e privata 10.20.2/24; IGW, NAT, endpoint S3 |
| WAF | t3.small, 20 GiB, 10.20.1.10 + EIP; nginx/ModSecurity/CRS, HTTPS pubblico, `DetectionOnly`; container `aizoon-waf` |
| WEB | t3.small, 20 GiB, 10.20.2.10; Juice Shop:3000 da digest Terraform; nessun IP pubblico |
| SIEM | m7i-flex.large (2 vCPU/8 GiB/50 GiB), 10.20.2.11; Wazuh 4.14.10; nessun IP pubblico |
| Gestione | SSM, SSH chiuso, IMDSv2, EBS cifrati, ruoli EC2/Backup dedicati |
| Telemetria | 13 allarmi, metriche memoria/disco/HTTPS, syslog CloudWatch, Flow Logs su S3, SNS→SQS |
| Backup | Tre EC2, ogni sei ore, conservazione sette giorni |
| Costi | Budget 35 USD/mese prima dei crediti. Al riavvio del 25 novembre la soglia era superata e l'azione di stop risultava già eseguita. |

Flussi: Internet→WAF:443; WAF→WEB:3000; WAF/WEB→SIEM:1514/1515; uscita 80/443. TLS con CA privata e SAN IP. Juice Shop è intenzionalmente vulnerabile: nessun dato reale.

**Configurazione.** Il controller invia il playbook Ansible via SSM Run Command; Ansible gira localmente sulle EC2. WEB: installa Docker e crea il container Juice Shop dal digest, senza ricrearlo se esiste. WAF: bootstrap, monitor HTTPS, CA privata. SIEM: controlli su installazioni parziali e checksum dell'installer, utente Blue Team, regola padre 100100. Un nuovo stack usa il profilo Ansible; sullo state esistente impostare `configure_with_ansible=false` prima del plan.

**Difese Cyber integrate.** `apply_cyber.py` distribuisce senza reinstallare Wazuh la regola ModSecurity 10001 (sonda), le regole 10011–10015, l'audit JSON AHZ inoltrato come syslog `bt_waf_audit`, i template degli agenti e le classificazioni Wazuh 110213–110217. La matrice `sfide.csv` associa una difesa a ciascuna delle 118 sfide Juice Shop v20.4.0 (44 WEB, 19 IAM, 15 BUILD, 13 CRS, 8 con regole dedicate, 5 UI, 5 OPS, 5 PUB, 3 WEB3; 18 disabilitate in Docker). Il profilo Ansible per VM dedicate di Finocchielli non si usa sul lab: non eseguire `site.yml`.

## 3. Step eseguiti

Il 27 novembre AWS Backup è passato a quattro esecuzioni al giorno (02:00, 08:00, 14:00 e 20:00 UTC), con conservazione di sette giorni e RPO di 12 ore verificabile con `verify_recovery_points.py`. I backup manuali di transizione risultano completati per WAF, WEB e SIEM. Nel nuovo account si riparte con dati vuoti.

Il restore da AWS Backup ha ricreato i tre nodi in una VPC isolata. Verificati HTTPS con CA, proxy verso WEB, servizi e regole del SIEM, file degli alert e ricezione di una nuova sonda WAF. I job AWS sono durati circa 77 secondi ciascuno, prima della configurazione di accesso e delle verifiche applicative.

Sul SIEM attivo (2 vCPU / 8 GiB), il campione leggero ha mostrato 4.834 MiB di RAM disponibile, 47% di disco usato e iowait 0–1%. Cinque sonde sono arrivate agli alert in 0,394–1,448 s. Il dato descrive un carico leggero e non dimostra la capacità durante una sessione Cyber. Rinviare il passaggio a 4 vCPU al confronto sotto carico rappresentativo.

TLS verificato con la CA del lab, IP SAN corrispondente e scadenza del certificato server al 13 dicembre 2026 UTC. Chromium, Firefox e WebKit hanno superato i test desktop e mobile con la CA attendibile e senza bypass.

State del lab Free migrato su S3 con cifratura, versioning e lock nativo. Le 70 risorse e tutti gli output coincidono con la copia privata pre-migrazione. Terraform ha assegnato una nuova lineage al backend. Il workflow GitHub Actions è in preparazione. Per l'approvazione serve la configurazione dell'environment da parte del proprietario del repository.

L'installer ufficiale Wazuh 4.14 ora seleziona la 4.14.11. Il bootstrap richiede versione e SHA-256 revisionati. Sulle tre EC2 private nuove sono passati bootstrap, adattatore Cyber e verifica Ansible. Il test browser Blue Team su 4.14.11 ha aperto e ricaricato WEB senza richieste di scrittura sulle viste. La correzione è idempotente insieme alla configurazione della retention. Il SIEM in servizio resta sulla 4.14.10.

Provati 80 marker innocui a due richieste al secondo sul SIEM di prova. Ricevuti 80/80, p95 1,578 s, CPU mediana 3,5%, iowait massimo 3%, 5.099 MiB disponibili e disco al 40%. Manteniamo 2 vCPU/8 GiB per il carico misurato. L'account Free ha rifiutato `c7i-flex.xlarge`. Il confronto diretto a 4 vCPU resta da ripetere se il carico effettivo lo richiede.

| Data | Step | Esito |
|---|---|---|
| 13 nov | Deploy v3.1 sull'account personale: Terraform, cloud-init, ruoli IAM dedicati, budget, switch EC2, adattatore Cyber | Verificato (tre nodi SSM Online, Wazuh con quattro servizi attivi) |
| 13 nov | Verifiche: API WEB, browser Chromium/Firefox/WebKit desktop e mobile (sei pass), WAF 200 → 403 → ritorno a `DetectionOnly`, 13 allarmi OK, backup WEB COMPLETED, 34 simulazioni IAM Blue | Passate |
| 13 nov | Correlazione Cyber: marker `bt-fa7b0130b448488ba8ec286656026451`, stesso transaction ID su WAF e manager; due agenti Active, login Wazuh readonly e Threat Hunting | Verificata |
| 17 nov | Matrice di 118 difese per sfida (`sfide.csv`, `DIFESE-SFIDE.md`); catalogo confrontato con il digest di progetto; dieci test su dieci | Fatto |
| 19 nov | Integrazione delle difese Cyber sul lab; classificazione audit WAF in Wazuh; correlazione ModSecurity 10011 → Wazuh 110213 | Verificata; restano le altre classificazioni |
| 19 nov | Ansible integrato in v3.1: verifica via SSM sulle tre EC2 esistenti, play WEB `changed=0 failed=0`; Terraform `fmt`/`validate` passati | Fatto |
| 19 nov | Checkov 3.4.6: Terraform 176 pass / 18 finding, Ansible 4 pass / 5 finding, Ansible Cyber 7 / 3 | Eseguito, finding da rivedere |
| 19 nov | Accesso Blue Team: login AWS CLI con MFA confermato in CloudTrail; corretto il controllo IAM SSM e il tunnel Wazuh | Fatto; pagina Wazuh poi verificata il 25 nov con `blue-team` e `blue-verifica` |
| 19 nov | Tre EC2 verificate operative, poi fermate; budget a 35 USD con stop automatico riarmato | Fatto |
| 19 nov | Documentazione centralizzata (`attuale/`, `old/`) | Fatto |
| 25 nov | Riavvio WAF, WEB e SIEM | Tre EC2 `running` e online in SSM, homepage HTTPS 200 |
| 25 nov | Un account operativo `blue-team` con MFA e profilo di verifica separato `blue-verifica` con gli stessi permessi | 58 verifiche di policy superate |
| 25 nov | Bash predefinito nel documento SSM `BlueDefence` v2 | Avvio e log CloudWatch verificati su WAF e SIEM con l'account amministrativo, Backspace e Canc verificati sul WAF |
| 25 nov | Wazuh 4.14.10, inizializzate 18 viste, impostato `checks.fields: false` e applicato `patch_wazuh_readonly.sh` | Apertura e refresh di WEB verificati con `blue-team` e `blue-verifica` in sola lettura |
| 25 nov | Commit `fd83348` "completa gli accessi Blue Team": modifiche a `lab.py`, `blue-team.tf`, `provision_wazuh_blue.py`, `verify_blue_access.py`, nuovo `patch_wazuh_readonly.sh`; aggiornati README v3.1, `DIFESA_LIVE.md` e `ACCESSO_BLUE_TEAM_v3.1.md` | Fatto; la modifica Terraform di `blue-team.tf` va applicata solo dopo plan revisionato |
| 25 nov | Riassunto dell'archivio storico `old` (piano iniziale, Learner Lab 2.0, tentativo 2, v3) in `riassunto-documentazione-old.md` | Fatto; l'archivio `old` è stato poi rimosso dal repository (commit `7caee78`), il riassunto ne conserva la sintesi |
| 25 nov | Guide di accesso Blue Team filtrate: `blue-verifica.md` e `guida-accesso-cyber.md` con segnaposto al posto di password, utenti, account, IP, ID istanze e impronta; i valori stanno in file `.txt` locali esclusi da Git (commit `7caee78`) | Fatto; le procedure sono pubblicabili, le variabili restano private |
| 25 nov | `ACCESSO_BLUE_TEAM_v3.1.md` filtrato come le altre guide: account, ID di WAF e SIEM, utenti, prefisso risorse e nome del referente sostituiti da segnaposto; valori in `variabili.txt` accanto al file, escluso da un nuovo `.gitignore` | Fatto; modifica non ancora committata |

Finestre di archiviazione grezza richiuse (`logall_json=no`), tunnel di collaudo chiusi, nessuna chiave API permanente per Blue.

## 4. Punti aperti

| Punto | Titolare |
|---|---|
| Collaudo dal vivo di 10012–10015 e delle classificazioni 110214–110217 | Blue |
| Blocco WAF non attivato | Blue |
| Sessione SSM `BlueDefence` da collaudare con l'MFA dell'operatore dal proprio PC | Blue |
| Bootstrap Ansible su tre EC2 nuove (incluso l'installer Wazuh) non collaudato | Cloud |
| Checkov su tutto il repository. Finding analizzati in [Revisione Checkov](../../documentazione/attuale/AWS%20ACA/Agosta/v3.1/docs/CHECKOV.md). | Cloud |
| Ripetere la misura SIEM durante una lezione se cresce il carico rispetto alla prova da due richieste al secondo. | Cloud |
| GitHub Actions con approvazione non implementato | Cloud |
| Budget 35 USD superato al riavvio del 25/11 con stop già eseguito: verificare consumo e decidere soglia o azione di stop | Cloud |
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
- Le guide Cyber in Git usano segnaposto: password e identificativi stanno nei file `*variabili*.txt` locali, ignorati da Git. Account e ID delle istanze sono ora filtrati anche in `ACCESSO_BLUE_TEAM_v3.1.md`, ma restano nella cronologia Git dei commit precedenti; le password mostrate durante la preparazione delle guide vanno ruotate se i log della sessione non sono privati.

## 6. Prossimi passi per team

### Team Cloud

1. Decidere sul piano crediti (scadenza rilevata del piano FREE il 28/11, a tre giorni) e sul budget da 35 USD, già superato al riavvio del 25/11.
2. Verificare nel nuovo account permessi, tipi EC2 disponibili e bootstrap da Terraform.
3. Configurare su GitHub l'environment con approvazione indipendente e verificare l'esecuzione OIDC.
4. Controllare nel nuovo lab l'età dei recovery point e la scadenza degli indici Wazuh.
5. Provare il perimetro del ruolo EC2 dopo il deploy e il filtro egress del container WEB.
6. Preparare la stima prudenziale dopo le ultime verifiche.

### Team Cyber — Blue (difesa)

1. Collaudare sul lab le regole 10012–10015 e le classificazioni 110214–110217, con timestamp UTC, marker e transaction ID; `wazuh-analysisd -t`.
2. Collaudare la sessione SSM `BlueDefence` dal PC del membro Blue con il suo MFA.
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

Stato attuale: una sola AZ, una sola istanza per ruolo, un solo NAT, backup con conservazione di sette giorni, WAF in `DetectionOnly`. Il guasto di un nodo o della AZ ferma servizio o SIEM. Ogni modifica passa da plan revisionato.

### Ridondanza

| Priorità | Team | Intervento | Note |
|---|---|---|---|
| Alta | Cloud | Seconda AZ con subnet pubblica e privata duplicate | Elimina il guasto di AZ come punto unico. |
| Alta | Cloud | Application Load Balancer davanti a due WAF (uno per AZ) con health check; WAF non più raggiungibile direttamente | Sostituisce l'EIP singolo; certificato ACM. |
| Alta | Cloud | Due WEB, uno per AZ, dietro i WAF | Juice Shop è senza stato. |
| Alta | Cloud | Un NAT gateway per AZ con route table separate | Oggi se il NAT cade, WEB e SIEM perdono l'uscita. |
| Media | Cloud | Auto Scaling group con minimo 1 per ruolo e AMI preconfezionate | Richiede bootstrap idempotente (già in Ansible). |
| Media | Cloud + Blue | SIEM: secondo nodo (cluster Wazuh) o almeno snapshot dell'indexer su S3 con ripristino provato | Punto unico più critico per i log. |
| Media | Cloud | Backup: retention di sette giorni e restore provato su tutti i nodi | Copia tra regioni o account da rivalutare se sarà necessario conservare evidenze. |
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
| Media | Cloud | Pipeline CI con Terraform, Checkov e deploy approvato | Workflow pronto nel ramo di lavoro. Approvazione e OIDC da verificare con i permessi del proprietario del repo. |
| Media | Cloud | Patching con SSM Patch Manager; pin Wazuh e immagini a digest | Installer 4.14 mutabile. |
| Bassa | Cloud | VPC endpoint per SSM, S3 e CloudWatch; NACL e SG minimi | Meno superficie e meno costo NAT. |
| Bassa | Cloud | Allarmi di costo e salute per ogni componente nuovo; SIEM a 4 vCPU/8 GiB | Raddoppiare i nodi raddoppia i costi: rivedere il budget da 35 USD. |

Il team Cloud realizza gli interventi infrastrutturali; il team Blue valida regole, agenti e SIEM; Red prova l'esito. Seconda AZ, secondo NAT, ALB e nodi doppi aumentano la spesa in modo sensibile: per il laboratorio basta il livello "Alta", il resto resta progetto di riferimento.
