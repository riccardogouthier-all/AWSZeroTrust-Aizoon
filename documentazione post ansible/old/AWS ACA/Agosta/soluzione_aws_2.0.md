# Specifica tecnica 2.0 — riferimento storico

Implementazione corrente: [v3.1](../../../attuale/AWS%20ACA/Agosta/v3.1/README.md). Specifica originale aizoOn conservata nella radice del repository.

## Requisiti

- Otto membri: quattro AWS, due Red, due Blue; account condiviso.
- Preparazione da casa/scuola; attacchi durante le lezioni da scuola.
- WEB pubblico tramite IP del WAF e HTTPS; WEB/SIEM privati, gestione SSM.
- Scenari asincroni: attacco → analisi → difesa → replay. Variante sincrona: Red attacca, Blue applica difese live.
- Dati applicativi sacrificabili; configurazioni ed evidenze versionate senza segreti.
- Deploy approvato da un membro del gruppo; GitHub Actions richiesto, non ancora attivo.

## Architettura

| Nodo | Stack / rete |
|---|---|
| WAF | nginx + ModSecurity/CRS; subnet pubblica 10.20.1.0/24; EIP e TLS SAN IP |
| WEB | Docker/Juice Shop:3000; subnet privata 10.20.2.0/24 |
| SIEM | Wazuh manager/indexer/dashboard/Filebeat; subnet privata |

VPC 10.20.0.0/16, una AZ, IGW, NAT, endpoint gateway S3. Flussi: Internet→WAF:443; WAF→WEB:3000; WAF/WEB→SIEM:1514/1515; uscita 80/443. SSH chiuso; IMDSv2, EBS cifrati, tag Project/Environment/Role.

Il riferimento Wazuh è 4 vCPU/8 GiB/50 GB; le varianti con 2 vCPU sono ridotte e non validate sotto carico. Regione effettiva delle prove: us-east-1. Il piano iniziale proponeva eu-west-1, subordinata ai vincoli del Learner Lab.

## Automazione e controlli

- 2.0: Terraform, backend S3 cifrato/versionato/locking; Ansible locale sulle EC2 tramite SSM.
- Gouthier: Terraform/cloud-init, state locale.
- 3.1: ruoli IAM dedicati, integrazione cyber via SSM, budget con stop EC2, profili Blue Team e switch manuale.
- Pipeline prevista: fmt/validate → Checkov/config → plan → approvazione → apply/config → smoke test. Autenticazione OIDC se consentita; nessuna credenziale nel repository.
- Monitoring: stato/CPU/memoria/disco/HTTPS, log di sistema, Flow Logs e notifiche. Flow Logs non contengono HTTP payload.
- Recupero: backup → ripristino isolato → verifica applicativa → pulizia temporanei. Una creazione di backup non prova il recupero.

## Criteri di consegna

Drift assente, bootstrap completato, HTTPS verificato con CA privata, due agenti Active, transazione WAF correlata sul manager, blocco senza regressioni sul traffico normale, QA documentata e ripristino provato. Conservare versioni, timestamp UTC, regole, esiti e limiti; non log grezzi con segreti.

Lo stop EC2 non elimina i costi di NAT, IPv4, EBS, log e backup. La dismissione è distinta dallo spegnimento delle lezioni.
