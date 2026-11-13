# Laboratorio AWS 2.0 — solo Terraform

Stesso laboratorio di `Agosta/laboratorio_aws_2.0` (WAF nginx+ModSecurity, Juice Shop, Wazuh all-in-one, CloudWatch, SNS→SQS, Flow Logs, AWS Backup), ma senza Python, Ansible o SSM. Un solo `terraform apply`.

La configurazione delle VM, prima playbook Ansible lanciati via SSM, ora è negli script `scripts/*.sh`. Terraform li concatena e li passa come `user_data` (cloud-init) a ogni istanza.

## File

| File | Contenuto |
| --- | --- |
| `versions.tf` | Provider, data source (AMI Ubuntu 24.04, ruolo Lab) |
| `variables.tf` | Parametri |
| `network.tf` | VPC, subnet, NAT, route, EIP del WAF, IP fissi degli host |
| `security.tf` | Security Group |
| `compute.tf` | 3 EC2 + composizione `user_data` |
| `storage.tf` | Bucket log, policy, lifecycle, VPC Flow Logs |
| `monitoring.tf` | Log group, SNS/SQS, allarmi, AWS Backup |
| `outputs.tf` | IP WAF, ID istanze, comando tunnel Wazuh |
| `scripts/common.sh` | Tutti gli host: pacchetti base, CloudWatch agent |
| `scripts/web.sh` | Docker + Juice Shop (:3000, privato) |
| `scripts/waf.sh` | Docker, CA privata e certificato per IP, WAF `DetectionOnly` |
| `scripts/waf-health.sh` | Timer systemd: metrica `HTTPSAvailable` |
| `scripts/siem.sh` | Wazuh 4.14 all-in-one, regola ModSecurity |
| `scripts/agent.sh` | Agent Wazuh su web e WAF (attende il SIEM) |

## Prerequisiti

- Terraform ≥ 1.9, AWS CLI v2 nel PATH.
- Credenziali Learner Lab complete (con session token) attive nella shell/profilo.
- `LabInstanceProfile` e `LabRole` esistenti. Nessun ruolo IAM viene creato.

## Deploy

```powershell
Copy-Item terraform.tfvars.example terraform.tfvars   # poi modificare
terraform init
terraform plan -out lab.tfplan
terraform apply lab.tfplan
```

Il bucket log viene creato con `aws s3api create-bucket` (risorsa `terraform_data`), perché il Learner Lab nega `GetBucketObjectLockConfiguration` richiesta da `aws_s3_bucket`. Fuori dal Learner Lab: `logs_bucket_via_cli = false`.

`apply` termina in pochi minuti, ma il provisioning continua sulle VM: Wazuh richiede 15-25 min. Gli agent su web e WAF attendono il SIEM (max ~60 min). Stato e log: shell SSM e `/var/log/cloud-init-output.log`.

## Accesso

```powershell
terraform output -raw waf_ip          # https://<IP>
terraform output -raw ssm_siem_tunnel # esegue il tunnel, poi https://localhost:8443
```

CA privata: copiarla dal WAF (shell SSM) con `sudo cat /opt/aizoon/tls/lab-ca.crt`.
Password Wazuh (`admin`), dal SIEM via SSM:

```bash
sudo tar -O -xf /opt/aizoon/wazuh-install-files.tar wazuh-install-files/wazuh-passwords.txt
```

Modalità WAF, dal WAF: `sudo /opt/aizoon/set-waf-mode.sh On|DetectionOnly`.

## Differenze e limiti rispetto ad Agosta

- Cambiare uno script cambia `user_data`: l'istanza viene ricreata (`user_data_replace_on_change`).
- Nessun orchestratore di verifica: niente `browser_tests`, `waf_tests`, `backup_test`. Controllare a mano.
- Nessun state remoto né bootstrap: state locale. Backend S3 opzionale commentato in `versions.tf`.
- Le installazioni `apt`, Wazuh e CloudWatch agent risolvono l'ultima versione disponibile al deploy.
- Un errore in uno script non fa fallire `terraform apply`: controllare `cloud-init status` sulle VM.
- Con `tester_ipv4_cidrs` ristretto, il controllo HTTPS dal WAF verso il proprio IP pubblico può fallire e far scattare l'allarme `https`.
- Il certificato dura 30 giorni.

## Dismissione

```powershell
terraform destroy
```

Un vault Backup non vuoto blocca la distruzione: attendere la scadenza dei recovery point (1 giorno) o eliminarli.
