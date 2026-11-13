# STEP — stato avanzamento laboratorio AWS Zero Trust

Ultimo aggiornamento: 2026-11-13. Codice Terraform: `AWS ACA/Gouthier/tentativo 2`.

## Fatto

- [x] **Infrastruttura attiva**: deploy solo Terraform (VPC, subnet pubblica/privata, NAT, 3 EC2: WAF, web, SIEM).
- [x] **Confronto con blue team e red team** (difesa e offesa) sull'ambiente in piedi.
- [x] **Accesso al WAF da CLI** (shell SSM sull'istanza WAF).
- [x] **Web visualizzata**: Juice Shop raggiungibile da `https://<waf_ip>` attraverso il WAF.
- [x] **Bozza dell'architettura** con WAF e SIEM e installazione automatizzata (`user_data` cloud-init, script in `scripts/`).

## Da fare

- [ ] **Entrare nel SIEM da CLI** (Wazuh, host privato, solo via SSM).
- [ ] **Verificare tutte le route table e i security group** (VPC `10.20.0.0/16`).

## Info utili

### Accesso al SIEM
```powershell
terraform output instances
aws ssm start-session --target <SIEM_INSTANCE_ID>
cloud-init status --wait          # nella shell del SIEM
```
Dashboard: `terraform output -raw ssm_siem_tunnel`, poi `https://localhost:8443`, utente `admin`.
Il SIEM ha IP privato `10.20.2.11`; Wazuh richiede 15-25 minuti dopo l'`apply`.

### Verifica route table e security group
```powershell
aws ec2 describe-route-tables --filters Name=vpc-id,Values=<VPC_ID> --output table
aws ec2 describe-security-groups --filters Name=vpc-id,Values=<VPC_ID> --output table
```
Attesi: subnet pubblica `10.20.1.0/24` con `0.0.0.0/0` verso IGW; subnet privata `10.20.2.0/24` con `0.0.0.0/0` verso NAT; endpoint S3 su entrambe.
Flussi SG attesi: Internet → WAF `443`; WAF → web `3000`; web e WAF → SIEM `1514-1515`; uscita `80/443` verso Internet.

### Note
- `tester_ipv4_cidrs` ha ora default `["0.0.0.0/0"]` (HTTPS del WAF pubblico).
- Guida completa ai comandi: `AWS ACA/Gouthier/00 - spiegazione tentativo 2.md`.
