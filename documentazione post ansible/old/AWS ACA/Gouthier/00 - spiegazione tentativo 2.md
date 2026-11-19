# Gouthier — procedure CLI

Eseguire da `tentativo 2`. [Architettura e limiti](tentativo%202/README.md).

## Profilo e deploy

Credenziali temporanee complete nel profilo AWS privato: access key, secret, session token. Il prompt aws configure non acquisisce da solo il session token.

```powershell
$env:AWS_PROFILE = 'learner-lab'
aws sts get-caller-identity
aws iam get-instance-profile --instance-profile-name LabInstanceProfile
aws iam get-role --role-name LabRole
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform validate
terraform plan '-out=lab.tfplan'
terraform apply lab.tfplan
terraform output instances
```

Revisionare il piano prima di apply, soprattutto sostituzioni. Parametri: region, project, tester_ipv4_cidrs; 0.0.0.0/0 espone il WAF. Gli script user_data sostituiscono la configurazione Ansible, non la gestione SSM.

## Bootstrap e accessi

```powershell
aws ssm describe-instance-information --output table
aws ssm start-session --region us-east-1 --target <INSTANCE_ID>
```

Sui nodi:

```bash
cloud-init status --long
sudo systemctl is-active amazon-cloudwatch-agent
# SIEM
sudo systemctl is-active wazuh-manager wazuh-indexer wazuh-dashboard filebeat
sudo /var/ossec/bin/agent_control -lc
# WAF
sudo docker exec aizoon-waf nginx -t
sudo /opt/aizoon/set-waf-mode.sh On
# Ritorno alla baseline
sudo /opt/aizoon/set-waf-mode.sh DetectionOnly
```

Esportare solo la CA pubblica /opt/aizoon/tls/lab-ca.crt; verificare HTTPS con curl --cacert. Non condividere log dell'installer o password.

```powershell
terraform output -raw waf_ip
terraform output -raw ssm_siem_tunnel
```

Eseguire il tunnel restituito e aprire https://localhost:8443. Le credenziali admin Wazuh restano nell'archivio privato sul SIEM.

## Diagnostica / dismissione

| Errore | Controllo |
|---|---|
| ExpiredToken / InvalidClientTokenId | Aggiornare l'intero profilo Lab, incluso token |
| 403 Object Lock | logs_bucket_via_cli=true e AWS CLI nel PATH |
| 502 | WEB pronto, container, flusso WAF→WEB:3000 |
| Agenti assenti | Bootstrap SIEM, porte 1514/1515, enrollment |

Per distruggere: plan -destroy sullo state corretto, gestione recovery point, destroy, verifica NAT/EIP/EC2 residue. Non eliminare prima il backend. Per lo stop operativo senza ricreazione usare la variante [3.1](../../../attuale/AWS%20ACA/Agosta/v3.1/docs/ACCENSIONE_SPEGNIMENTO.md).
