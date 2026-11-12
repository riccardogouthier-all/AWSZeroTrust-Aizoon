# Laboratorio Integrato Cloud Security & DevSecOps — Soluzione su AWS

Documento valido dalla proposta fino alla **realizzazione dell'architettura**.

> **Fuori ambito (secondo momento):** penetration test / vulnerability assessment su Juice Shop, attivazione del blocco WAF, regole di detection Wazuh sugli attacchi, scenari Red Team / Blue Team.

## Indice

1. [Mappatura Azure → AWS](#1-mappatura-azure--aws)
2. [Architettura](#2-architettura)
3. [Fasi fino all'architettura](#3-fasi-fino-allarchitettura)
4. [Rimandato a un secondo momento](#4-rimandato-a-un-secondo-momento)

---

## 1. Mappatura Azure → AWS

| Azure (proposta) | AWS (soluzione) |
|---|---|
| Microsoft Azure | Amazon Web Services, regione `eu-west-1` (Irlanda) |
| Resource Group | Tag `Project`/`Environment` + `default_tags` Terraform |
| VNet | VPC `10.20.0.0/16` |
| Subnet | Subnet pubblica `10.20.1.0/24` e privata `10.20.2.0/24` |
| Internet Gateway | Internet Gateway (IGW) |
| NAT Gateway | NAT Gateway + Elastic IP, nella subnet pubblica |
| Route table / UDR | Route table pubblica (IGW) e privata (NAT) |
| NSG | Security Group, regole tra SG (non tra IP) |
| VM Ubuntu | EC2 Ubuntu Server 24.04 LTS (AMI Canonical) |
| Managed Disk | EBS gp3 cifrato |
| IP pubblico statico | Elastic IP (solo sul WAF) |
| Bastion / SSH | SSM Session Manager (nessuna porta 22 aperta) |
| Storage per Ansible | Bucket S3 privato (usato dal plugin `aws_ssm`) |
| Azure Monitor / NSG flow logs | CloudWatch Logs + VPC Flow Logs |
| Azure Cost Management | AWS Budgets (alert via email) |
| Azure DevOps (repo + pipeline) | GitHub + GitHub Actions (opzionale: CodePipeline) |
| Azure Boards | Trello o GitHub Projects |
| Defender for Cloud | Checkov (IaC) + Security Hub (opzionale) |
| Provider `azurerm` | Provider `hashicorp/aws ~> 6.0` |
| Inventario Ansible `azure_rm` | Inventario Ansible `amazon.aws.aws_ec2` |
| Connessione Ansible SSH | Connessione Ansible `community.aws.aws_ssm` |

---

## 2. Architettura

### 2.1 Schema logico

Una sola AZ (scelta di costo).

```
   Internet
      |  HTTPS 443 solo dagli IP autorizzati (variabile allowed_cidrs)
      v
 +---------------------------- VPC 10.20.0.0/16 -----------------------------+
 |                                                                          |
 |  SUBNET PUBBLICA 10.20.1.0/24            Route: 0.0.0.0/0 -> IGW         |
 |   [EC2 WAF]  nginx + ModSecurity + OWASP CRS   (Elastic IP)              |
 |   [NAT Gateway] (Elastic IP)                                             |
 |        |                                                                 |
 |        | proxy verso :3000                                               |
 |        v                                                                 |
 |  SUBNET PRIVATA 10.20.2.0/24             Route: 0.0.0.0/0 -> NAT GW      |
 |   [EC2 WEB]  Docker + OWASP Juice Shop (bkimminich/juice-shop)           |
 |   [EC2 SIEM] Wazuh all-in-one (manager + indexer + dashboard)            |
 |        ^                                                                 |
 |        | agent Wazuh 1514/tcp (eventi), 1515/tcp (enrollment)            |
 |        +-- da WEB e da WAF                                               |
 |                                                                          |
 |  VPC Endpoint S3 (gateway) -> bucket Ansible    VPC Flow Logs -> CW Logs |
 +--------------------------------------------------------------------------+
```

- **Amministrazione:** solo SSM Session Manager, nessuna porta SSH esposta.
- **Dashboard Wazuh:** port-forward SSM su `https://localhost:8443`.

### 2.2 Componenti e dimensionamento

| Ruolo | Subnet | Tipo | Disco | Software (installato da Ansible) |
|---|---|---|---|---|
| WAF | pubblica | `t3.small` | 20 GB | nginx, ModSecurity v3, OWASP CRS, TLS |
| WEB | privata | `t3.small` | 20 GB | Docker, OWASP Juice Shop |
| SIEM | privata | `t3.large` | 50 GB | Wazuh server, indexer, dashboard |

### 2.3 Flussi di rete consentiti (Security Group)

| Origine | Destinazione | Porta | Note |
|---|---|---|---|
| Internet | WAF | tcp 443 | solo CIDR in `allowed_cidrs` (/24…/32, mai `0.0.0.0/0`) |
| WAF | WEB | tcp 3000 | riferimento al SG |
| WEB, WAF | SIEM | tcp 1514, 1515 | riferimento al SG |
| Tutti | Internet | tcp 80, 443 | in uscita via NAT/IGW (pacchetti, immagini, SSM) |

Ogni altro traffico è negato. Il SG di default della VPC è svuotato.

### 2.4 Controlli di sicurezza integrati

- IMDSv2 obbligatorio, hop limit 1.
- Dischi EBS cifrati; bucket S3 con Block Public Access, SSE e policy solo-TLS.
- Ruolo IAM minimo: `AmazonSSMManagedInstanceCore` + accesso solo al bucket Ansible.
- Nessuna chiave SSH e nessuna credenziale nel codice.
- VPC Flow Logs su CloudWatch con retention configurabile.
- Juice Shop e Wazuh mai esposti direttamente a Internet.

### 2.5 Stima costi mensili

`eu-west-1`, 730 h, ordine di grandezza. Da verificare con AWS Pricing Calculator.

| Voce | Costo |
|---|---|
| 3 EC2 (2 × `t3.small` + 1 × `t3.large`) | ~100 USD |
| NAT Gateway (ora + traffico) | ~35 USD |
| EBS gp3 90 GB | ~8 USD |
| Elastic IP (2 IPv4 pubblici) | ~7 USD |
| Flow Logs, S3, CloudWatch | pochi USD |
| **Totale sempre acceso** | **~150 USD/mese** |

> **Attenzione:** NAT e IPv4 pubblici costano anche con le EC2 spente. A fine sessione eseguire `terraform destroy`. Con ~40 h/mese il costo scende a pochi USD.

---

## 3. Fasi fino all'architettura

### Fase 0 — Prerequisiti

1. Account AWS dedicato al laboratorio (o sandbox) con utente/ruolo amministratore.
2. Strumenti locali: Terraform ≥ 1.9, AWS CLI v2 con Session Manager plugin, Ansible, Checkov, Git.
3. Autenticazione CLI con IAM Identity Center (`aws sso login`) o profilo temporaneo.
4. Repo Git con cartelle `terraform/`, `ansible/`, `docs/`.
5. Budget: impostare `budget_email` in `terraform.tfvars` per ricevere gli alert.

### Fase 1 — Rete e compute con Terraform

Cartella `terraform/`.

1. Copiare `terraform.tfvars.example` in `terraform.tfvars` e inserire il proprio IP pubblico in `allowed_cidrs`.
2. Eseguire:

   ```bash
   terraform init
   terraform fmt -check && terraform validate
   terraform plan -out lab.plan
   terraform apply lab.plan
   ```

3. Nel plan verificare: VPC, 2 subnet, IGW, NAT, 3 EC2, 1 EIP per il WAF.
4. Verifica: le 3 istanze sono **Online** in Systems Manager › Fleet Manager.
5. Output utili: `waf_public_ip`, `instance_ids`, `private_ips`, `ansible_bucket`, `ssm_shell_commands`, `ssm_wazuh_dashboard_tunnel`.

| File | Contenuto |
|---|---|
| `versions.tf` | provider, `default_tags`, backend S3 opzionale (commentato) |
| `variables.tf` | parametri e validazioni (`allowed_cidrs` obbligatorio) |
| `network.tf` | VPC, subnet, IGW, NAT, route, endpoint S3, VPC Flow Logs |
| `security.tf` | Security Group, regole, ruolo IAM e instance profile |
| `storage.tf` | bucket S3 di scambio per Ansible |
| `compute.tf` | AMI Ubuntu 24.04, 3 EC2, Elastic IP del WAF |
| `budget.tf` | AWS Budgets (creato solo se `budget_email` è valorizzato) |
| `outputs.tf` | IP, ID istanze, comandi SSM |

### Fase 2 — Analisi di sicurezza del codice IaC

1. Scansione Terraform:

   ```bash
   checkov -d terraform/ --framework terraform -o cli -o sarif
   ```

2. Scansione Ansible (quando i playbook esistono):

   ```bash
   checkov -d ansible/ --framework ansible
   ```

3. Correggere i finding rilevanti. Eccezioni consapevoli: documentarle con `checkov:skip=ID:motivo` accanto alla risorsa. Esempi attesi:
   - NAT singolo e una sola AZ: scelta di costo.
   - EBS con chiave AWS-managed invece di CMK: semplicità didattica.
   - Flow Logs senza KMS: dati non sensibili.
4. Salvare il report (SARIF/HTML) in `docs/`: è un output richiesto dal corso.

### Fase 3 — Configurazione con Ansible

Cartella `ansible/`.

1. Inventario dinamico `amazon.aws.aws_ec2` con filtro sul tag `Role` (`web`, `waf`, `siem`).
2. Connessione `community.aws.aws_ssm` con `ansible_aws_ssm_bucket_name` = output `ansible_bucket` e `ansible_aws_ssm_region` = `eu-west-1`.
3. Ruoli, in quest'ordine:

   | # | Ruolo | Cosa fa |
   |---|---|---|
   | a | `common` | aggiornamenti, orologio, hardening di base |
   | b | `siem` | Wazuh all-in-one, password in Ansible Vault |
   | c | `web` | Docker + container Juice Shop su 3000, restart automatico |
   | d | `waf` | nginx + ModSecurity v3 + OWASP CRS, TLS (self-signed o ACM/Let's Encrypt con dominio), upstream = IP privato di WEB (output `private_ips`), ModSecurity in `DetectionOnly` |
   | e | `agents` | agent Wazuh su web e waf, enrollment verso il SIEM (1515), raccolta log nginx/ModSecurity audit e Docker |

4. Playbook idempotenti, eseguibili più volte senza effetti collaterali.

### Fase 4 — Verifica dell'architettura

Criteri di accettazione:

- [ ] `terraform apply` termina senza errori; un secondo `plan` non mostra differenze.
- [ ] Le 3 EC2 risultano Online in Systems Manager.
- [ ] `https://<waf_public_ip>` mostra Juice Shop passando dal WAF.
- [ ] La porta 3000 di WEB non è raggiungibile da Internet né dal proprio IP.
- [ ] Da un IP non presente in `allowed_cidrs` il WAF non risponde.
- [ ] Nessuna istanza ha la porta 22 aperta.
- [ ] La dashboard Wazuh (tunnel SSM) mostra 2 agenti attivi (web, waf).
- [ ] Nel SIEM arrivano i log di accesso nginx e quelli di ModSecurity.
- [ ] Report Checkov archiviato in `docs/`.
- [ ] Flow Logs presenti nel log group `/<project>/vpc-flow-logs`.

### Fase 5 — CI/CD (estensione opzionale)

1. GitHub Actions con autenticazione OIDC verso un ruolo IAM (nessuna chiave statica).
2. Pipeline: `fmt`/`validate` → Checkov → `terraform plan` (commento sulla PR) → `apply` manuale con approvazione.
3. Backend remoto: bucket S3 con versioning e `use_lockfile` (blocco in `versions.tf`).

### Fase 6 — Analisi costi e documentazione

1. Tabella ore/uomo, costo infrastruttura, costo manutenzione annuale.
2. Confronto con alternative: sandbox on-prem, Azure.
3. Documentazione per il cliente finale, schema architetturale, repository.
4. Chiusura sessione: `terraform destroy` (verificare che NAT ed Elastic IP siano rimossi).

---

## 4. Rimandato a un secondo momento

- Vulnerability assessment di Juice Shop e obiettivo "login admin".
- Passaggio di ModSecurity da `DetectionOnly` a `On` e tuning delle regole.
- Regole di detection Wazuh e dashboard sugli attacchi.
- Estensioni: IDS/IPS (Suricata), alerting automatico, gamification Red vs Blue.
