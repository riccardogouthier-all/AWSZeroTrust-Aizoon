# Compatibilità Cloud / Cyber

Aggiornamento documentale 13 novembre 2026. Stato runtime attestato solo dalle evidenze del relativo deploy.

| Variante | IAM / state / configurazione |
|---|---|
| Agosta 2.0, commit 90a1dca | Ruoli Lab preesistenti; backend S3; Ansible locale via SSM |
| Gouthier tentativo 2, base 3b5066c | LabRole/LabInstanceProfile; state locale; cloud-init |
| Agosta 3 / 3.1 | Ruoli personali dedicati; state locale; cloud-init + adattatore cyber; budget e BlueDefence |
| Finocchielli/site.yml | Tre VM dedicate Ubuntu 24.04 amd64; TLS e stack propri; non sovrapporre a un deploy esistente |

## Contratti

- AWS attuale: us-east-1; 10.20/16; WAF .1.10, WEB .2.10, SIEM .2.11. HTTPS pubblico, nessun IP pubblico WEB/SIEM.
- Outputs Gouthier/Agosta 3.x: waf_ip, instances, ssm_siem_tunnel. Gli helper 3.1 aggiungono account_id/region/project.
- Inventario Ansible di esempio: eu-west-1, Project=lab-integrato, Environment=lab. Non seleziona automaticamente il conto personale.
- Finocchielli: /opt/blue-team, container blue-team-waf. Stack Cloud: /opt/aizoon, container aizoon-waf. L'adattatore crea il link dei log e monta la regola 10001.
- La prima configurazione Cloud includeva regola 100100; la 10001 è la sonda cyber, non una detection generale.
- Una modifica user_data può sostituire una VM. Revisione del plan prima di apply; non reinstallare Wazuh sopra enrollment esistenti.

## Handoff

Cloud fornisce account, regione, ID/state, CIDR e accessi. Blue verifica bootstrap, clock, SAN/CA, versioni, spazio, agenti e transazione correlata. Red concorda sorgente, finestra e marker. Conservare solo evidenze minimizzate; segreti e log integrali restano privati.

Le verifiche statiche del contributo Ansible non attestano un suo deploy completo. I risultati del laboratorio personale ottenuti tramite adattatore sono separati in [validazione 3.1](../../../AWS%20ACA/Agosta/v3.1/docs/evidenze/validazione.json).
