# Gouthier — tentativo 2

Provisioning Terraform/cloud-init; gestione SSM. Nessun controller Ansible. Variante Learner Lab, distinta da [Agosta v3.1](../../Agosta/v3.1/README.md).

## Contratto

VPC 10.20/16; WAF 10.20.1.10, WEB 10.20.2.10, SIEM 10.20.2.11. WAF pubblico HTTPS, WEB:3000 privato, eventi/enrollment Wazuh 1514/1515. NAT per l'uscita, endpoint S3, EIP WAF, TLS SAN IP e CA privata. CloudWatch, SNS→SQS, Flow Logs S3, Backup giornaliero con retention un giorno.

Terraform ≥1.9, AWS CLI v2/plugin SSM, profilo Lab completo di session token, LabInstanceProfile/LabRole. Lo state è locale; backend S3 opzionale in versions.tf. Default us-east-1 e HTTPS pubblico.

```powershell
Copy-Item terraform.tfvars.example terraform.tfvars
aws sts get-caller-identity
terraform init
terraform fmt -check
terraform validate
terraform plan '-out=lab.tfplan'
# Approvare il piano.
terraform apply lab.tfplan
terraform output instances
terraform output -raw waf_ip
terraform output -raw ssm_siem_tunnel
```

L'ultimo comando stampa il tunnel da eseguire; dashboard https://localhost:8443. Installazione ancora in corso dopo apply: controllare cloud-init status --long e i servizi. Wazuh può richiedere 15–25 minuti; agenti in attesa fino a circa un'ora.

## File

network/security/compute: rete, SG, EC2. storage: S3/Flow Logs. monitoring: allarmi/Backup. scripts: common, web, waf, waf-health, siem, agent.

Il bucket usa terraform_data + AWS CLI quando logs_bucket_via_cli=true per evitare la lettura Object Lock vietata dal Lab. Su account compatibile usare false.

## Vincoli

- Una modifica user_data può ricreare le VM; apply riuscito non valida il bootstrap.
- Immagini Docker a digest; AMI e pacchetti/installer risolti al deploy.
- Certificato 30 giorni; CA pubblica sul WAF in /opt/aizoon/tls/lab-ca.crt.
- Credenziali Wazuh nell'archivio privato /opt/aizoon/wazuh-install-files.tar sul SIEM.
- CIDR HTTPS ristretto può bloccare il controllo dal WAF al proprio EIP.
- Nessuna suite browser/restore inclusa in questa variante.
- Destroy: prima gestire i recovery point; il vault non vuoto è protetto. Stop EC2 lascia costi NAT/EBS/IPv4/storage.

[Comandi e diagnostica](../00%20-%20spiegazione%20tentativo%202.md).
