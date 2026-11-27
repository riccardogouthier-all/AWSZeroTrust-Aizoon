# Revisione Checkov

Scansione dalla radice del repository, con directory nascoste incluse per i workflow. I report completi restano privati, perché possono contenere metadati del deploy. Checkov analizza i formati supportati. Shell, Python e comportamento a runtime richiedono verifiche dedicate.

Scansione completa del 27 novembre 2026, Checkov 3.4.6. Terraform 808 pass / 85 finding, Ansible 34 pass / 15 finding, workflow 60 pass / 0 finding. Zero errori di parsing e zero segreti rilevati. Il conteggio comprende le versioni storiche. La sola 4.0 registra Terraform 198 pass / 24 finding e Ansible 4 pass / 6 finding.

```bash
CKV_IGNORE_HIDDEN_DIRECTORIES=false checkov -d . --skip-download -o json
CKV_IGNORE_HIDDEN_DIRECTORIES=false checkov -d . --framework secrets --enable-secret-scan-all-files --skip-download -o json
```

| Controlli | Valutazione |
|---|---|
| AWS 112, 113, 158, 166, 145, 26 | Distinguere TLS e cifratura di servizio da chiave KMS gestita dal cliente. Per i log di sessione e il vault Backup valutare CMK e policy di servizio nel nuovo account. |
| AWS 338, 144 | La durata di un anno e la replica interregionale superano il requisito corrente. Per il lab tenere sette giorni e verificare il restore. |
| AWS 18, 21, CKV2 AWS 62 | Per lo state S3 il versioning è già attivo. Per il bucket log valutare versioning, tracciamento accessi e notifiche in base a chi riceve gli eventi e ai tempi di conservazione. |
| AWS 273, 355 | Usare identità federate se disponibili nel nuovo account. Verificare il perimetro effettivo delle azioni con IAM Simulator e rivedere separatamente i wildcard consentiti per azioni senza risorsa specificabile. |
| AWS 394, CKV2 AWS 5 | Fissare la zona quando il nuovo account fornisce la zona autorizzata. Confermare in AWS l'associazione dei security group, anche quando il grafo statico non la risolve. |
| CKV2 AWS 61 | Definire una retention per le versioni non correnti del backend S3 quando sarà concordata la finestra di rollback. |
| CKV2 Ansible 1 | HTTP solo su localhost o sul flusso privato WAF→WEB. L'ingresso WAF usa HTTPS con CA verificata. |
| CKV2 Ansible 3 | I blocchi falliscono su installazione incompleta o versione inattesa. Il nuovo blocco WEB interrompe il deploy se il filtro non si applica. La ripetizione su EC2 di prova e il riavvio di Docker sono passati. Mantenere privati i log dell'installer. |

La scansione locale copre l'intero repository e distingue risultati IaC, errori di parsing e segreti. I finding dei profili storici restano visibili e vanno interpretati nel loro contesto.
