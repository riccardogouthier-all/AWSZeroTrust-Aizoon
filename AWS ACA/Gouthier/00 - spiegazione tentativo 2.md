# Spiegazione tentativo 2

Ho letto il progetto Agosta. Ho scritto il progetto Terraform in `AWS ACA/Gouthier/tentativo 2`: la configurazione Ansible diventa script `user_data`. `terraform validate` e `bash -n` passano; nessun CRLF negli script. Non ho fatto plan né apply, perché servono le credenziali del Learner Lab.

## Cosa è stato fatto

Il progetto di Agosta aveva già un `main.tf`. Python e YAML servivano per due cose:

- **Setup:** `bootstrap.py` creava i bucket.
- **Configurazione VM:** i playbook Ansible venivano lanciati via SSM.

Qui entrambe finiscono in Terraform. I playbook diventano gli script bash `scripts/*.sh`, passati come `user_data` cloud-init alle tre EC2.

## File principali

- `versions.tf`, `variables.tf`, `outputs.tf`
- `network.tf`, `security.tf`, `compute.tf`, `storage.tf`, `monitoring.tf`
- `scripts/` con `common`, `web`, `waf`, `waf-health`, `siem` e `agent`
- `README.md`, `terraform.tfvars.example`, `.gitignore`, `.gitattributes`

## Scelte e limiti da conoscere

- **IP fissi:** gli host hanno IP privati fissi, così gli script conoscono già gli indirizzi senza cicli di dipendenza.
- **IP del WAF:** l'EIP del WAF è allocato prima dell'istanza, per metterlo nel certificato TLS.
- **Bucket log:** il Learner Lab nega `GetBucketObjectLockConfiguration` richiesta da `aws_s3_bucket`. Il bucket si crea quindi con `aws s3api create-bucket` dentro `terraform_data`, e serve AWS CLI nel PATH. Fuori dal Lab si imposta `logs_bucket_via_cli = false`.
- **Tempi:** dopo `apply` Wazuh ha bisogno di circa 15-25 minuti. Gli agent su web e WAF attendono il SIEM.
- **Errori negli script:** se uno script fallisce, `apply` non lo segnala. Si controlla con `cloud-init status` sulle VM.
- **Test:** tolti i test browser, WAF e backup di Agosta.
- **State:** locale, senza bootstrap del backend.
- **Modifiche agli script:** cambiare uno script ricrea l'istanza.

Gli script bash non sono stati eseguiti: controllati solo per sintassi. Il primo deploy reale potrebbe richiedere aggiustamenti, soprattutto su Wazuh e sull'installazione dell'agent.

---

# Procedura comandi

PowerShell, dalla cartella `tentativo 2`.

## 0. Collegamento AWS CLI (Learner Lab)

Nel Learner Lab: **Start Lab** → **AWS Details** → **Show**. Copiare `aws_access_key_id`, `aws_secret_access_key` e `aws_session_token` in `%USERPROFILE%\.aws\credentials`, profilo `[default]` (oppure `[learner-lab]`). Le credenziali scadono: a ogni nuova sessione del Lab vanno ricopiate.

```powershell
cd "AWS ACA\Gouthier\tentativo 2"
# solo se si usa un profilo diverso da default:
$env:AWS_PROFILE = 'learner-lab'
aws sts get-caller-identity
aws iam get-instance-profile --instance-profile-name LabInstanceProfile
aws iam get-role --role-name LabRole
```

Se `sts get-caller-identity` risponde con `Account` e `Arn`, il collegamento è ok.

## 1. Parametri

```powershell
Copy-Item terraform.tfvars.example terraform.tfvars
notepad terraform.tfvars
```

Controllare `region`, `project`, `tester_ipv4_cidrs`. `0.0.0.0/0` rende pubblico l'HTTPS del WAF; per un ambiente riservato inserire il proprio IP `/32`.

## 2. Test statici (nessuna risorsa creata, nessun costo)

```powershell
terraform version
terraform init
terraform fmt -check -recursive
terraform validate
```

- `fmt -check`: nessun output = formattazione ok.
- `validate`: deve rispondere `The configuration is valid.`

## 3. Test con AWS (sola lettura, nessuna risorsa creata)

```powershell
terraform plan -out lab.tfplan
terraform show lab.tfplan
```

Il plan interroga AWS (AMI Ubuntu via SSM, ruolo `LabRole`, account), quindi verifica anche credenziali e permessi. Nel riepilogo controllare `Plan: N to add, 0 to change, 0 to destroy` e che non ci siano errori su `data.aws_iam_role.lab` o `data.aws_ssm_parameter.ubuntu`.

## 4. Creazione dell'architettura

```powershell
terraform apply lab.tfplan
```

Applica esattamente il piano revisionato. Se il piano è vecchio, rifare `terraform plan -out lab.tfplan`. Durata: ~5-10 minuti (NAT Gateway).

> **Attenzione:** NAT Gateway, Elastic IP, 3 EC2 e dischi costano finché esistono.

## 5. Verifica dopo il deploy

```powershell
terraform output
terraform output -raw waf_ip
terraform state list
```

Il provisioning continua dentro le VM dopo l'`apply` (Wazuh 15-25 minuti). Stato dello script di avvio, su ogni VM via SSM (ID da `terraform output instances`):

```powershell
aws ssm start-session --target <INSTANCE_ID>
```

Poi, nella shell della VM:

```bash
cloud-init status --wait
sudo tail -n 50 /var/log/cloud-init-output.log
```

Istanze Online in SSM dopo qualche minuto:

```powershell
aws ssm describe-instance-information --query "InstanceInformationList[].[InstanceId,PingStatus]" --output table
```

### Test HTTPS del WAF

Dopo `cloud-init` completato su waf e web. Dalla shell SSM del WAF copiare la CA in un file locale `lab-ca.crt`:

```bash
sudo cat /opt/aizoon/tls/lab-ca.crt
```

```powershell
curl.exe --cacert lab-ca.crt https://<IP_WAF>/
```

### Dashboard Wazuh

Richiede il plugin Session Manager di AWS nel PATH. Eseguire il comando stampato da:

```powershell
terraform output -raw ssm_siem_tunnel
```

Poi aprire `https://localhost:8443`, utente `admin`. Password, dalla shell SSM del SIEM:

```bash
sudo tar -O -xf /opt/aizoon/wazuh-install-files.tar wazuh-install-files/wazuh-passwords.txt
```

## 6. Modifiche successive

```powershell
terraform plan -out lab.tfplan
terraform apply lab.tfplan
```

Cambiare un file in `scripts/` ricrea l'istanza interessata: leggere il plan.

## 7. Smontaggio

```powershell
terraform plan -destroy
terraform destroy
```

Un vault AWS Backup non vuoto blocca la distruzione: attendere la scadenza dei recovery point (1 giorno) oppure eliminarli:

```powershell
aws backup list-recovery-points-by-backup-vault --backup-vault-name <project>-backup
aws backup delete-recovery-point --backup-vault-name <project>-backup --recovery-point-arn <ARN>
```

Dopo `destroy` verificare che non restino NAT Gateway, Elastic IP o EC2:

```powershell
aws ec2 describe-nat-gateways --filter Name=state,Values=available
aws ec2 describe-addresses
aws ec2 describe-instances --filters Name=instance-state-name,Values=running,pending
```

## Problemi tipici

- `ExpiredToken` / `InvalidClientTokenId`: credenziali Lab scadute, ricopiarle.
- 403 su `GetBucketObjectLockConfiguration`: lasciare `logs_bucket_via_cli = true`.
- `aws` non riconosciuto nel `local-exec`: AWS CLI v2 non è nel PATH.
- Regione: il Lab di solito consente solo `us-east-1` e `us-west-2`.
