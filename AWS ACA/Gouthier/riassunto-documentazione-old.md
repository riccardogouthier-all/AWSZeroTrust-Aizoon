# Riassunto della documentazione storica (`documentazione post ansible/old`)

Sintesi dei documenti superati, archiviati il 19 novembre 2026 dopo l'integrazione di Ansible nella v3.1. La versione corrente è la [v3.1](../Agosta/v3.1/README.md); lo stato aggiornato è in [progressi.md](progressi.md). Questi documenti restano utili come storico delle scelte e dei vincoli.

## Contenuto dell'archivio

| Documento | Cosa descrive |
|---|---|
| `baseline.md` | Piano tecnico iniziale del laboratorio (obiettivi, infrastruttura, CI/CD, monitoring, esercitazioni, costi, criteri di consegna) |
| `AWS ACA/step.txt`, `STEP.md` | Appunti iniziali (3 EC2, nginx WAF, Juice Shop, Wazuh) e stato tecnico del 13 novembre |
| `Agosta/soluzione_aws_2.0.md` | Specifica tecnica 2.0 (requisiti, architettura, criteri di consegna) |
| `Agosta/laboratorio_aws_2.0/` | Runbook e report del deploy sul Learner Lab del 12 novembre |
| `Agosta/v3/` | Release v3 su account personale: README, report del deploy del 13 novembre, difesa live, evidenze |
| `Gouthier/tentativo 2/`, `00 - spiegazione tentativo 2.md` | Variante Terraform/cloud-init di Gouthier per il Learner Lab e relative procedure CLI |
| `Gouthier/progressi.md` | Versione precedente di questo report (prima dell'aggiornamento Ansible) |
| `Cyber CYS/Defence/ACCESSO_BLUE_TEAM_v3.md` | Vecchia guida di accesso Blue Team, rimandata alla guida 3.1 |

## Piano iniziale (`baseline.md`)

Obiettivo: un laboratorio AWS condiviso in cui costruire, attaccare e difendere Juice Shop, con ciclo completo deploy → attacco → rilevamento → difesa → recupero. Gruppo di otto persone (quattro AWS, due Red, due Blue) sullo stesso account; esercitazioni asincrone (Red attacca, Blue analizza e difende, Red ripete). Strumenti confermati: Terraform, Ansible, Checkov, Docker, Juice Shop, ModSecurity con CRS, Wazuh, GitHub Actions con deploy approvato da un membro del gruppo.

Il piano indicava: verifica dei vincoli del Learner Lab (permessi, ruoli, budget, GitHub Actions); una VPC 10.20.0.0/16 in una sola AZ con subnet pubblica (WAF + NAT) e privata (WEB e SIEM); tre EC2 Ubuntu 24.04 (WAF e WEB t3.small, SIEM con riferimento Wazuh di 4 vCPU/8 GiB/50 GB); accesso solo HTTPS al WAF tramite IP pubblico con certificato SAN IP; amministrazione via SSM senza SSH; state Terraform su S3 cifrato con versioning e lock; pipeline fmt/validate → Checkov → plan → approvazione → apply/Ansible → smoke test; monitoring con Flow Logs, allarmi CloudWatch e agent per memoria e disco; backup con prova di ripristino isolato; checklist di test funzionale e browser; chiusura delle lezioni con `terraform destroy` o controllo dei costi residui (NAT, EIP, EBS, snapshot, bucket). Era un piano, non attestava alcun ambiente già funzionante.

## Learner Lab 2.0 (12 novembre)

Prima implementazione su Learner Lab: ruoli `LabRole`/`LabInstanceProfile` preesistenti, backend S3 con lock, Ansible eseguito localmente sulle EC2 via SSM, regione us-east-1, SIEM ridotto a t3.large (2 vCPU/8 GiB). Esiti: Terraform senza drift; HTTPS e API OK; browser Chromium/Firefox/WebKit desktop e mobile (sei pass); porte interne non raggiungibili dall'esterno; WAF 200 in `DetectionOnly` → 403 con motore On → baseline ripristinata; Wazuh con due agenti Active e regola 100100; 13 allarmi e notifica SNS→SQS; backup completato e VM ripristinata da AMI; Checkov 116 pass e 7 finding (cifratura CMK di CloudWatch, SNS e vault, retention 7 giorni, scelta AZ, SG non associati). Adattamenti: bucket log gestito fuori dal Terraform per il divieto Object Lock del Lab; una modifica a SG/compute ha ricreato le tre VM durante il bootstrap. Limiti: nessun secondo deploy completo, stress test o telefoni fisici; pipeline non attivata; il restore riguardava il WEB della prima generazione.

## Tentativo 2 di Gouthier

Variante senza controller Ansible: Terraform e cloud-init, state locale (S3 opzionale), gestione SSM, stessa rete (WAF 10.20.1.10, WEB 10.20.2.10, SIEM 10.20.2.11), CloudWatch, Flow Logs, Backup giornaliero. Wazuh richiede 15–25 minuti per installarsi e gli agenti fino a un'ora. Vincoli: una modifica a `user_data` può ricreare le VM, un `apply` riuscito non valida il bootstrap, certificato di 30 giorni, nessuna suite browser né restore. Le procedure CLI coprono profilo con session token, bootstrap, tunnel Wazuh, cambio modalità WAF (`set-waf-mode.sh`), diagnostica (token scaduto, 403 Object Lock, 502, agenti assenti) e dismissione.

## v3 (13 novembre, account personale)

Release originale `b729167`: Terraform e cloud-init con ruoli IAM dedicati (nessuna dipendenza da LabRole), adattatore Cyber, IAM Blue Team, budget con stop automatico, backup. Esiti principali: SIEM m7i-flex.large (la t3.xlarge era rifiutata dal piano), tre nodi online, Wazuh 4.14.10, regola 10001 con transaction ID coincidente su WAF e manager, 34 simulazioni IAM Blue passate, backup WEB completato. Crediti: cinque attività da 20 USD completate, saldo 200 USD, piano FREE con scadenza rilevata il 28/11/2026. Accesso Blue: ruolo `aizoon-personal-BlueDefence` con MFA, sessione SSM con `sudo` limitata a WAF/SIEM, massimo un'ora. Limiti rimasti: nessun restore sull'account personale, stress test, GitHub Actions e login AWS completo dopo MFA. La v3 non conteneva lo switch `start`/`stop`/`status`, aggiunto poi nella v3.1.

## Cosa è stato superato dalla v3.1

- Ruoli del Learner Lab sostituiti da ruoli IAM dedicati; state locale e privato invece di backend S3 condiviso.
- Aggiunti switch EC2, budget da 35 USD con stop automatico, profili Blue Team (`blue-team`, `blue-verifica`), configurazione con Ansible via SSM e difese Cyber per sfida.
- Restano non ancora realizzati rispetto al piano iniziale: GitHub Actions con approvazione, dimensionamento SIEM a 4 vCPU, prova di restore sull'account personale, retention e KMS completi (finding Checkov).
