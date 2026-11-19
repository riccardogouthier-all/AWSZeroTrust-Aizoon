# Learner Lab — esiti del 12 novembre 2026

Report storico; non prova lo stato attuale dell'account. [Runbook 2.0](../README.md).

## Deploy e adattamenti

- Regione us-east-1; identità voclabs, LabRole/LabInstanceProfile preesistenti.
- State S3 con locking/versioning; bucket log gestito esternamente per il divieto GetBucketObjectLockConfiguration.
- WAF/WEB t3.small; SIEM ridotto a t3.large, 2 vCPU/8 GiB/50 GiB.
- HTTPS pubblico solo sul WAF; WEB/SIEM privati, SSM, EBS cifrati, IMDSv2.
- Configurazione Ansible tramite Run Command locale sulle EC2.
- Una modifica SG/compute ha ricreato le tre VM durante il bootstrap. Servizi riconfigurati; il piano di sostituzione richiede revisione esplicita.

## Risultati

| Verifica | Esito |
|---|---|
| Terraform | validate e plan finale senza drift |
| HTTPS / API | 200; ricerca, registrazione 201, login 200; CA/IP verificati |
| Browser | Chromium, Firefox, WebKit × desktop/mobile viewport: sei pass |
| Porte provate | 443 raggiungibile; 22/3000/1514/1515/9200/55000 non raggiungibili |
| WAF | Sonda XSS: 200 DetectionOnly, 403 On, traffico normale 200; baseline ripristinata |
| Wazuh | Quattro servizi centrali attivi, due agenti Active, audit ricevuto e regola 100100 |
| Indexer | green, un nodo, 883 alert al controllo |
| Monitoring | 13 allarmi, metriche memoria/disco, log e Flow Logs; notifica SNS→SQS |
| Backup/recupero | COMPLETED; VM da AMI privata AWS Backup, Juice Shop operativo senza reinstallazione; temporanei rimossi |
| Checkov | 116 pass, 7 finding, zero skip/errori di parsing |
| Dashboard | Login page 200 via tunnel; login UI autenticato non provato |

Il recupero riguarda il WEB della prima generazione, non le tre VM finali; non è un test StartRestoreJob né una prova di consistenza sotto carico. Il piano giornaliero è stato aggiornato alle istanze finali. La prova non include una campagna Red completa.

## Finding residui

| ID | Limite |
|---|---|
| CKV_AWS_158 / CKV_AWS_338 | CloudWatch senza CMK custom; retention 7 giorni invece di un anno |
| CKV_AWS_26 | SNS senza KMS configurata |
| CKV_AWS_166 | Vault senza CMK custom; snapshot verificato cifrato |
| CKV_AWS_394 | AZ selezionata per ordine, non per zone identity |
| CKV2_AWS_5 ×2 | SG segnalati non associati; inventario EC2 conferma le associazioni |

[Evidenze selezionate](evidenze/checkov-final.json). I log SSM integrali restano privati. Nessun secondo deploy completo del pacchetto riproducibile, stress test o prova su telefoni fisici. Pipeline non attivata. Le risorse principali furono lasciate attive; stato/costi correnti da verificare.
