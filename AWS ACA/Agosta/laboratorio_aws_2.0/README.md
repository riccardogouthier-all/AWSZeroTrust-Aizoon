# Laboratorio 2.0 — Learner Lab

Variante storica: Terraform + Ansible eseguito sulle EC2 via SSM. [Versione corrente 3.1](../v3.1/README.md).

## Configurazione

Tre Ubuntu 24.04 amd64: WAF/WEB t3.small 20 GiB; SIEM t3.large 8 GiB RAM/50 GiB. VPC 10.20/16, subnet pubblica/privata, NAT, EIP WAF, endpoint S3. WEB/SIEM senza IP pubblico; SSH chiuso. WAF DetectionOnly, TLS con CA privata.

Prerequisiti: Terraform ≥1.9, AWS CLI v2 + Session Manager plugin, Python ≥3.12. Profilo Learner Lab con access key, secret e session token nel file privato AWS. LabRole/LabInstanceProfile già presenti; nessuna creazione IAM.

## Deploy — PowerShell dalla cartella del pacchetto

```powershell
py -m venv .venv
$python = "$PWD/.venv/Scripts/python.exe"
& $python -m pip install -r requirements.txt
$env:AWS_PROFILE = 'learner-lab'
aws sts get-caller-identity
Copy-Item terraform.tfvars.json.example terraform/terraform.tfvars.json
& $python bootstrap.py
terraform -chdir=terraform init -backend-config=backend.hcl
terraform -chdir=terraform validate
terraform -chdir=terraform plan '-out=lab.tfplan'
# Revisione e approvazione del membro incaricato.
terraform -chdir=terraform apply lab.tfplan
& $python export_outputs.py
& $python configure_all.py
```

Parametri: region, project univoco, ruoli esistenti, tester_ipv4_cidrs. Il bootstrap gestisce bucket state/log fuori dal Terraform per il divieto Object Lock del Lab; state con versioning e locking. Non cambiare account/progetto nella stessa directory runtime. Un timeout SSM non annulla il comando remoto: ispezionare l'ID prima di ripetere.

## Accesso e test

```powershell
terraform -chdir=terraform output -raw waf_ip
.\Open-WazuhTunnel.ps1
& $python -m playwright install chromium firefox webkit
& $python browser_tests.py
& $python waf_tests.py
& $python backup_test.py
```

WEB: https://IP_WAF; verifica TLS con lab-ca.crt. Wazuh: https://localhost:8443 tramite tunnel; credenziali private dell'installer sul SIEM. Non registrare password in output condivisi.

WAF test: 200 DetectionOnly → 403 On → ripristino DetectionOnly. Backup test: backup WEB, VM privata da AMI, verifica Juice Shop senza reinstallazione, terminazione VM/SG temporanei. Crea risorse a pagamento; non usa StartRestoreJob. Controller e backup lasciano evidenze in evidence/, ignorata da Git.

```powershell
& $python -m pip install -r requirements-dev.txt
& $python -m unittest discover -s tests -v
terraform -chdir=terraform test
```

I test Terraform usano mock AWS. Checkov separato dalle dipendenze del controller: 116 pass, 7 finding nel run storico. GitHub Actions non implementata.

## Dismissione e limiti

1. Esportare evidenze e chiudere tunnel.
2. Gestire i recovery point: vault non vuoto blocca destroy.
3. Revisionare plan -destroy, poi destroy sul backend corretto.
4. Verificare NAT/EIP/EBS e temporanei. Eliminare bucket log esterno allo state se non serve.
5. Conservare il backend fino alla verifica finale; cancellarne versioni/oggetti solo dopo la dismissione.

SIEM 2 vCPU sotto il riferimento Wazuh; installer/pacchetti risolti al deploy. Stop VM non azzera i costi. [Esiti e finding storici](docs/report_learner_lab.md).
