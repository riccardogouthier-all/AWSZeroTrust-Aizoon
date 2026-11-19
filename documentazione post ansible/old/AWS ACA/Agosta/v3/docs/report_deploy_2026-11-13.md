# Account personale — report tecnico 13 novembre 2026

Base Gouthier 3b5066c + Cyber Finocchielli 169a747. Questa relazione riporta il deploy effettivo e i controlli successivi; la pubblicazione 3.1 non è un nuovo deploy completo. State, segreti e log SSM integrali rimangono privati.

## Implementazione / adattamenti

| Passo | Esito |
|---|---|
| Identità | codex-progetto inizialmente senza policy; AdministratorAccess assegnata dopo conferma esplicita |
| Crediti | Cinque attività AWS da 20 USD completate: Budgets, DynamoDB, EC2, RDS, Lambda; +100 USD, saldo API rilevato 200 USD; piano FREE, scadenza rilevata 28/11/2026 11:27 Europe/Rome |
| Pulizia attività | EC2 temporanea terminata, RDS/DynamoDB/Lambda/URL/ruolo/log/SG dedicati eliminati; budget mantenuto |
| Terraform | Ruoli EC2/Backup dedicati, S3 ordinario, rete/compute/telemetria; nessuna dipendenza LabRole |
| SIEM | t3.xlarge rifiutata dal piano nonostante DryRun; scelta m7i-flex.large ammessa, 2 vCPU/8 GiB |
| Bootstrap | Tre nodi SSM Online, cloud-init done; Wazuh 4.14.10, quattro servizi centrali attivi |
| Cyber | Regola 10001, audit JSON AHZ, input specifici, rotazione; nessuna reinstallazione, CA/enrollment mantenuti |
| Blue Team | Utente AWS con password iniziale fuori state, reset obbligatorio/MFA; Wazuh readonly; ruolo sudo WAF/SIEM separato |
| Costi | Budget 20 USD/mese pre-crediti importato nello state, azione AUTOMATIC sulle tre EC2 |
| Switch 3.1 | Start/stop/status, ruolo singolo o tutte, guardie account/regione/tag e budget; nessun destroy |

## Verifiche

| Controllo | Risultato |
|---|---|
| Terraform | fmt/validate, apply e plan finale senza drift nella prova privata |
| API WEB | Ricerca, registrazione 201, login 200 con token; nessun segreto salvato |
| Browser | Chromium/Firefox/WebKit × viewport desktop/mobile: sei pass |
| WAF | 200 DetectionOnly → 403 On; normale 200; ritorno DetectionOnly |
| Cyber | Marker bt-fa7b0130b448488ba8ec286656026451, transaction ID 17945831688.770935 su WAF e manager; access log correlato |
| Wazuh | Due agenti Active, indexer green; 1195 alert al controllo iniziale; login readonly/Threat Hunting verificati successivamente |
| Monitoring | 13 allarmi OK; metriche e Flow Logs presenti; transizione sintetica SNS→SQS verificata |
| Backup | WEB COMPLETED, AMI privata e snapshot cifrato; recovery point COMPLETED; restore personale non eseguito |
| IAM Blue | 34 simulazioni passate, diniego senza MFA e fuori ambito; modifica regole manager readonly rifiutata 403 |
| Switch | 13 test unitari e DryRun AWS start/stop; tre VM rimaste running |

L'accesso readonly richiedeva index pattern condivisi assenti: inizializzati dall'amministratore, senza assegnare scrittura al lettore. Il ruolo frontend generico kibana_read_only nascondeva l'app Wazuh: sostituito dal ruolo custom documentato. Preferenze UI in scrittura possono ancora produrre 403; consultazione degli eventi verificata.

Finestre di archiviazione grezza chiuse con logall_json=no dopo la correlazione. Baseline WAF DetectionOnly. Tunnel di collaudo chiusi. Nessuna chiave API permanente creata per Blue; password Wazuh generata sul SIEM e consegnata cifrata RSA al workspace privato.

## Limiti / consegna

SIEM 2 vCPU sotto il riferimento; nessuno stress test, restore completo personale, telefono fisico o login AWS del membro dopo il suo MFA. La UI browser è stata verificata con bypass della fiducia TLS; la verifica CA/SAN del WAF era separata. AWS Budgets è ritardato, lo stop non elimina NAT/EBS/IPv4/storage. Il precedente recupero Learner Lab 2.0 non prova il restore di questo account.

Pipeline GitHub Actions con approvazione non implementata. L'operatore conserva state/runtime/handoff; Git include solo sorgenti, istruzioni e [evidenze selezionate](evidenze/README.md). Il pacchetto 3.1 aggiunge metadati output, helper portabili e switch, verificati offline/DryRun; nessun nuovo ciclo di deploy o stop/start reale.

Lo switch descritto sopra viene pubblicato nella [v3.1](../../../../../attuale/AWS%20ACA/Agosta/v3.1/docs/ACCENSIONE_SPEGNIMENTO.md); non fa parte del codice v3.
