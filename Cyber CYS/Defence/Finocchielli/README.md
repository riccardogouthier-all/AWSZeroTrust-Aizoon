# Blue Team · WAF e SIEM

Controlli AWS sul secondo tentativo Gouthier e laboratorio ripetibile su Kali. Nel laboratorio Finocchielli il primo traguardo è ottenere la stessa transazione su Juice Shop, nell’audit di ModSecurity e nell’archivio del manager Wazuh. La regola locale 10001 riconosce soltanto una sonda sintetica. La risposta attesa è HTTP 200.

| Per iniziare | Dove |
|---|---|
| Presentare al team il lavoro svolto e la prossima demo | [Spiegazione del lavoro Blue Team](SPIEGAZIONE-TEAM.md) |
| Stato della repo, differenze fra i due progetti AWS, commit e dipendenze | [Audit del 13 novembre](AUDIT.md) |
| Eseguire il WAF su Kali, preparare le VM, installare, collaudare e ripristinare | [Manuale operativo](RUNBOOK.md) |
| Applicare i ruoli siem, waf, agents | [Playbook principale](site.yml) |
| Correlare access log, audit locale, archivio centrale e stato degli agenti | [Collaudo Ansible](verify.yml) |
| Controllare i parametri prima del deploy | [Esempio impostazioni](settings.example.yml) |
| Verifiche eseguite e prove da completare | [Registro di validazione](VALIDAZIONE.md) |

Il contributo vive in `Cyber CYS/Defence/Finocchielli/` ed è condiviso fra i componenti del gruppo. Il controller legge i digest già registrati da Agosta. Gouthier configura le tre VM tramite Terraform e cloud-init. Seguire la sezione 2 del manuale per verificare quel deploy; usare i ruoli Ansible su VM dedicate. Il Cloud Team gestisce sistema base, rete e backend WEB. Su un Learner Lab già configurato con Agosta usare la procedura di sola lettura nel manuale prima di decidere un’eventuale migrazione.
