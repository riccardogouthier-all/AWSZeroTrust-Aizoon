# Progressi progetto — Agosta (Cloud) e Finocchielli (Blue Team)

**Perimetro:** `AWS ACA/Agosta` e `Cyber CYS/Defence/Finocchielli` · **Stato al:** 19 novembre 2026 · **Redatto da:** coordinamento progetto

## Aggiornamento dopo l’integrazione Ansible

- **AWS:** il 19 novembre WAF, WEB e SIEM sono stati verificati operativi, poi fermati su richiesta. Stato finale delle tre EC2 verificato in AWS: `stopped`. Budget a 35 USD mensili prima dei crediti, con stop automatico riarmato.
- **Cyber:** regole integrate sul lab. Correlazione verificata tra ModSecurity 10011 e Wazuh 110213 sul log di audit JSON. WAF in `DetectionOnly`. Restano da provare le altre classificazioni e il blocco.
- **Ansible e Checkov:** verifica via SSM passata sulle tre EC2 esistenti. Play WEB con zero modifiche. Restano il bootstrap su EC2 nuove e la revisione dei finding.
- **Accesso Blue Team:** login AWS CLI con MFA confermato in CloudTrail. Corretto il controllo IAM SSM. La sessione del tunnel risulta connessa in AWS e Wazuh risponde sulla porta 443 del SIEM. La guida indica `https://127.0.0.1:8443/` sul PC che apre il tunnel. Resta da confermare la pagina dal suo browser.
- **Documentazione:** guide operative in `attuale/`, versioni storiche in `old/`. Questo file resta aggiornato in Gouthier. [Indice](../../documentazione%20post%20ansible/README.md) · [Report Ansible](../../documentazione%20post%20ansible/attuale/AWS%20ACA/Agosta/v3.1/docs/ANSIBLE.md)

## 1. Sintesi

Il laboratorio AWS (Agosta, versione corrente 3.1) è distribuito e verificato sull'account personale: tre EC2 (WAF, WEB, SIEM), telemetria, backup, protezione costi e switch di accensione/spegnimento. Il contributo Blue Team (Finocchielli) è consegnato e documentato e si innesta sul laboratorio tramite un adattatore, senza reinstallare Wazuh. Il WAF parte in `DetectionOnly`: osserva e segnala, non blocca. Codice, test e documentazione sono a buon punto; restano aperte le prove sui motori reali, il passaggio al blocco e alcune verifiche di sicurezza e dimensionamento.

Storico: 12 novembre pacchetto Agosta 2.0 (Learner Lab) e consegna iniziale Blue; 13 novembre v3 e v3.1 su account personale, guida al Learner Lab; 17 novembre difese per singola sfida (commit `868d1c1`).

## 2. Agosta — evoluzione delle versioni

| Versione | Contenuto |
|---|---|
| `laboratorio_aws_2.0` | Variante storica per Learner Lab: Terraform + Ansible via SSM, ruoli LabRole preesistenti, backend S3, immagini a digest (`images.lock.json`), test browser/WAF/backup, report e proposta soluzione. |
| `v3` | Account personale: ruoli IAM dedicati, state locale, cloud-init, adattatore Cyber, accessi Blue Team, protezione costi. |
| `v3.1` | Evoluzione corrente: aggiunge lo switch EC2 `lab.py`/`lab.ps1`, il profilo Ansible via SSM e la guida operativa. Nessun nuovo stack creato alla pubblicazione. |

**Architettura 3.1.** us-east-1, una AZ, VPC 10.20/16 con subnet pubblica (10.20.1/24) e privata (10.20.2/24), IGW, NAT, endpoint S3. WAF t3.small su 10.20.1.10 con EIP (nginx/ModSecurity/CRS, HTTPS pubblico); WEB t3.small su 10.20.2.10 (Juice Shop:3000); SIEM m7i-flex.large (2 vCPU/8 GiB/50 GiB) su 10.20.2.11 con Wazuh 4.14.10. WEB e SIEM senza IP pubblico; gestione via SSM, SSH chiuso, IMDSv2, EBS cifrati. Telemetria: 13 allarmi, metriche memoria/disco/HTTPS, syslog CloudWatch, Flow Logs su S3, SNS→SQS. Backup giornaliero alle 02:00 UTC, retention un giorno. Budget operativo da 35 USD al mese prima dei crediti, con stop automatico delle tre EC2.

## 3. Agosta — esiti del deploy e delle verifiche (13 novembre)

| Area | Esito |
|---|---|
| Terraform | fmt/validate, apply e plan finale senza drift (prova privata); nessuna dipendenza da LabRole. |
| Bootstrap | Tre nodi SSM Online, cloud-init done; quattro servizi Wazuh attivi. La t3.xlarge è stata rifiutata dal piano: scelta m7i-flex.large. |
| Applicazione | API WEB: ricerca, registrazione 201, login 200. Browser Chromium/Firefox/WebKit × desktop/mobile: sei pass. |
| WAF | 200 in DetectionOnly → 403 con motore On → ritorno a DetectionOnly; traffico normale sempre 200. |
| Cyber | Marker `bt-fa7b0130b448488ba8ec286656026451`: stesso transaction ID su WAF e manager, access log correlato. |
| Wazuh | Due agenti Active, indexer green; login readonly e Threat Hunting verificati. |
| Monitoring / backup | 13 allarmi OK, Flow Logs presenti, transizione SNS→SQS verificata; backup WEB COMPLETED con AMI e snapshot cifrato. |
| IAM Blue | 34 simulazioni passate, diniego senza MFA e fuori ambito; modifica regole readonly rifiutata con 403. |
| Switch EC2 | 13 test unitari e DryRun AWS start/stop; nessun ciclo reale forzato. |
| Crediti | Cinque attività da 20 USD completate (+100 USD, saldo 200 USD); piano FREE con scadenza rilevata il 28/11/2026. |

Finestre di archiviazione grezza richiuse (`logall_json=no`), tunnel di collaudo chiusi, nessuna chiave API permanente per Blue. Lo stop delle EC2 lascia costi di NAT, IPv4, EBS, log e backup; `destroy` non va usato per fermare le lezioni.

## 4. Finocchielli — contenuto e risultati

| Elemento | Contenuto |
|---|---|
| `site.yml`, `verify.yml`, `roles/` | Ansible per tre VM Ubuntu 24.04 dedicate (SIEM → controllo WEB → WAF → agenti); `verify.yml` confronta il transaction ID tra WAF e manager. |
| `lab/compose.yml` | Ambiente locale Kali/Docker, WAF + Juice Shop su `127.0.0.1:8088`. |
| Regole | ModSecurity 10001 (sonda) e 10011–10015; sette regole Wazuh di classificazione (110213–110217 per le regole WAF). |
| `tools/`, `tests/` | `probe.py`, `check_evidence.py`, `check_challenges.py`, `check_public_assets.py`; dieci test automatici. |
| `sfide.csv` | 118 sfide Juice Shop v20.4.0: 44 WEB, 19 IAM, 15 BUILD, 13 con regole CRS, 8 con regole dedicate, 5 UI, 5 OPS, 5 PUB, 3 WEB3; 18 disabilitate in Docker. |

**Telemetria.** Client → WAF:443 → Juice Shop:3000; agenti WAF e WEB verso il manager sulla 1514 (enrollment 1515). L'audit ModSecurity è JSON seriale inoltrato come syslog con prefisso `bt_waf_audit`. La sonda 10001 forza l'audit del marker; il verificatore controlla transaction ID, agente, location, CRS, modalità e HTTP 200.

**Verifiche.** 13 novembre: 12 YAML parsati, template XML validi, cinque test offline. 17 novembre: chiavi, nomi e flag delle 118 voci confrontati con il catalogo del digest di progetto; dieci test su dieci passati. Definiti i casi Payback Time (WAF 10015, alert 110217) e View Basket (verifica applicativa lato WEB).

**Integrazione.** Sul laboratorio attivo non si esegue `site.yml`: `apply_cyber.py` monta la regola 10001 e gli input. Le differenze tra Agosta 2.0, Gouthier tentativo 2 e Agosta 3.x sono in `AUDIT.md`. Nel tentativo 2 di Gouthier (LabRole, state locale, cloud-init) le stesse regole vanno integrate nel cloud-init; una modifica a `user_data` può sostituire la VM, quindi serve revisione del plan prima di ogni `apply`.

## 5. Punti aperti

| Punto | Titolare / azione |
|---|---|
| Verifica dal vivo di 10012–10015 e delle relative classificazioni ancora aperta | Blue: prova su WAF e manager, `wazuh-analysisd -t`. |
| Blocco non attivato | Blue: staging, rollback a `DetectionOnly` se si rompe traffico normale. |
| Esiti applicativi (WEB, IAM, UI, BUILD, OPS, WEB3) | Team applicativo, frontend, chi prepara l'immagine, Cloud. |
| Idempotenza Ansible, carico, installazione su VM dedicate | Blue: secondo run di `site.yml`. |
| SIEM a 2 vCPU sotto il riferimento (4 vCPU/8 GiB/50 GB); nessuno stress test | Cloud: misure di ritardo marker, RAM, disco. |
| Restore completo del backup non eseguito | Cloud: prova di ripristino. |
| Login AWS con MFA del membro Blue non completato | Cloud + membro Blue. |
| Test browser con bypass TLS; verifica CA/SAN separata | Cloud: verifica con CA del lab. |
| GitHub Actions con approvazione non implementato; budget AWS ritardato; piano FREE in scadenza il 28/11 | Cloud: decisione su CI e piano. |
| Retention archivi/indici; enrollment agenti protetto solo da SG | Blue/Cloud. |

## 6. Rischi e vincoli

- Il marker 10001 è una sonda di integrazione, non prova la copertura di tutte le famiglie CRS.
- Sintassi YAML/XML valida non equivale a esecuzione: il contributo Ansible non ha un deploy completo attestato.
- Un alert indica una corrispondenza, non un attacco bloccato. Una sfida è "previene" solo dopo rifiuto verificato, stato integro e controllo positivo autorizzato.
- Lo state Terraform è locale e privato: non applicare uno state vuoto sul deploy esistente; un'installazione per account.
- L'installer Wazuh della serie 4.14 è mutabile: verificare la patch 4.14.10 prima di un nuovo deploy.
- Non eseguire `verify_aws.py` o `waf_tests.py` durante una prova Red non concordata (hanno effetti).
- Segreti e log integrali restano privati; si conservano solo evidenze minimizzate.

## 7. Prossimi passi

1. Completare il collaudo delle regole rimanenti sul laboratorio AWS, con timestamp UTC, marker e transaction ID.
2. Concordare con Red sorgente, finestra e marker; eseguire prova asincrona (attacco → analisi → modifica → replay).
3. Promuovere al blocco in staging solo le regole senza regressioni.
4. Completare MFA del membro Blue, restore di backup e misure sul SIEM.
5. Assegnare e tracciare le righe WEB/IAM/UI/BUILD/OPS ai rispettivi titolari.
6. Integrare le modifiche nel cloud-init del tentativo 2 e decidere sul piano crediti prima del 28/11.
