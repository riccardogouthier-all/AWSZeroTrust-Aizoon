# AWS Lab 3.1

Account personale: Terraform/cloud-init, integrazione Cyber via SSM, IAM Blue Team, budget e switch EC2. Evoluzione della [v3](../v3/README.md); nessun nuovo stack creato durante la pubblicazione.

## Architettura

| Risorsa | Configurazione |
|---|---|
| Rete | us-east-1, una AZ, VPC 10.20/16, subnet 10.20.1/24 pubblica e 10.20.2/24 privata; IGW, NAT, endpoint gateway S3 |
| WAF | t3.small/20 GiB; 10.20.1.10 + EIP; nginx/ModSecurity/CRS; HTTPS pubblico; DetectionOnly |
| WEB | t3.small/20 GiB; 10.20.2.10; Juice Shop:3000; nessun IP pubblico |
| SIEM | m7i-flex.large, 2 vCPU/8 GiB/50 GiB; 10.20.2.11; Wazuh 4.14.10; nessun IP pubblico |
| Gestione | SSM; SSH chiuso; IMDSv2; EBS cifrati; ruoli EC2/Backup dedicati |
| Telemetria | 13 allarmi, memoria/disco/HTTPS, syslog CloudWatch, Flow Logs S3, SNS→SQS |
| Backup | Tre EC2, giornaliero 02:00 UTC, retention un giorno |
| Costi | Budget mensile 20 USD pre-crediti; stop automatico delle tre EC2 |

Flussi SG: Internet→WAF:443; WAF→WEB:3000; WAF/WEB→SIEM:1514/1515; uscita 80/443. TLS con CA privata e SAN IP. Juice Shop è intenzionalmente vulnerabile: nessun dato reale.

## Deploy

Prerequisiti: Terraform 1.13.5 o compatibile, AWS CLI/plugin SSM, Python ≥3.12, profilo privato con permessi IAM/Cloud. OpenSSL locale o Ubuntu/WSL per i login. Variante non compatibile con i soli permessi ridotti del Learner Lab.

Da questa cartella, PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install
aws sts get-caller-identity
Copy-Item project/terraform.tfvars.json.example project/terraform.tfvars.json
terraform -chdir=project init
terraform -chdir=project validate
terraform -chdir=project plan '-out=deploy.tfplan'
# Apply del piano dopo revisione/approvazione del membro incaricato.
terraform -chdir=project apply deploy.tfplan
python lab.py outputs
python ops.py nodes
```

Parametri: region/project, nomi ruoli, tester_ipv4_cidrs; 0.0.0.0/0 pubblica solo il WAF. Un'installazione per account: blue-team e BlueTeamLogs hanno nomi fissi. Sul deploy esistente recuperare lo state privato originale; non applicare uno state vuoto.

Attendere cloud-init done e tre nodi SSM Online prima di configurare:

```powershell
python lab.py ca
python apply_cyber.py
python lab.py blue-init
```

L'adattatore aggiunge regola 10001, audit JSON AHZ, input e rotazione senza reinstallare Wazuh. blue-init crea login con password fuori dallo state, consegna Wazuh cifrata RSA e cambio password AWS obbligatorio. File in private/, ACL Windows o directory Linux 0700; niente reset automatico di login già esistenti senza handoff.

## Aggiornare un lab esistente

Con WAF in `DetectionOnly`, WAF e SIEM online in SSM e gli output corretti in `evidence/outputs.json`:

```powershell
python update_cyber_rules.py
```

Installa le classificazioni Wazuh, verifica gli ID e la configurazione, riavvia il manager e ricarica nginx dopo `nginx -t`. Ripristina il file precedente del componente se la validazione o l’attivazione fallisce. Il comando conserva le impostazioni di archiviazione. Verificare poi l’alert 110213 con una richiesta di controllo innocua, come descritto nella [matrice Cyber](../../../Cyber%20CYS/Defence/Finocchielli/DIFESE-SFIDE.md).

## Verifiche

```powershell
python -m unittest test_tools -v
python test_cyber_adapter.py
python -m unittest discover -s cyber/tests -v
python verify_blue_access.py
python verify_cost_protection.py
python verify_aws.py
python browser_tests.py
python waf_tests.py
```

Primi tre comandi offline. verify_aws crea utente QA, forza un allarme sintetico e avvia un backup se assente; waf_tests cambia temporaneamente la modalità e ripristina DetectionOnly. test_blue_dashboard richiede credenziali private e tunnel locale 8445. Non eseguire i controlli con effetti durante una prova Red non concordata.

## Operazioni

| Procedura | Riferimento |
|---|---|
| AWS/Wazuh/BlueDefence | [Accessi in Defence](../../../Cyber%20CYS/Defence/ACCESSO_BLUE_TEAM_v3.1.md) |
| Start/stop EC2 | [Switch](docs/ACCENSIONE_SPEGNIMENTO.md) |
| Enforcement, regole, archivi | [Difesa live](docs/DIFESA_LIVE.md) |
| Deploy effettivo / limiti | [Report](docs/report_deploy_2026-11-13.md) |
| Test, immagini, hash | [Evidenze](docs/evidenze/README.md), [provenienza](docs/provenienza.json) |

## Vincoli

State locale, runtime in evidence/, segreti in private/: esclusi da Git. Installer Wazuh serie 4.14 mutabile; l'adattatore richiede 4.14.10: verificare patch prima di un nuovo deploy. Docker a digest e provider nel lockfile. Modifiche user_data possono sostituire le VM; modifiche live non tornano automaticamente nell'IaC.

SIEM sotto il riferimento di 4 vCPU; niente stress test, telefoni fisici, restore completo personale o nuovo deploy integrale del pacchetto Git. Login AWS/MFA del membro ancora da completare; login Wazuh readonly verificato. GitHub Actions con approvazione ancora da implementare.

Stop EC2 lascia costi NAT/IPv4/EBS/log/backup. Budgets è ritardato; start rifiuta budget già raggiunto. Il piano FREE rilevato il 13/11 scadeva il 28/11/2026 11:27 Europe/Rome: dato storico, non garanzia per altri account o piani PAID. Dismissione: plan -destroy revisionato, gestione recovery point, destroy; il bucket log force_destroy cancella gli oggetti. Non usare destroy per lo stop delle lezioni.
