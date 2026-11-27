# DR e conservazione

RPO di 12 ore sui tre nodi. AWS Backup genera snapshot ogni sei ore, con avvio entro 60 minuti, completamento entro 180 minuti e conservazione di sette giorni. `python verify_recovery_points.py` controlla l'età dell'ultimo punto completato per ruolo. Un punto scaduto o mancante fa fallire il controllo. L'allarme CloudWatch `backup-jobs` osserva i job EC2 falliti, scaduti o abortiti nel vault del lab e invia le transizioni a SNS. Per verificare l'RPO serve il controllo di età per nodo. Nel lab Free l'allarme è attivo e lo stato rilevato è `OK`.

## Restore verificato

1. Scegliere un punto completato per WAF, WEB e SIEM. Creare una VPC di prova senza collegamenti al lab attivo e mantenere gli IP privati originali al suo interno.
2. Ripristinare le tre EC2 con AWS Backup, senza IP pubblici, senza copiare i tag operativi e con security group isolati. Abilitare SSM con endpoint privati e aprire solo i flussi interni del lab.
3. Verificare la home WEB e la configurazione Nginx. Verificare il proxy HTTPS WAF usando la CA originale e risolvendo l'IP del certificato verso il WAF isolato.
4. Verificare i quattro servizi Wazuh, la sintassi delle regole, il file degli alert preesistenti e l'arrivo di una sonda innocua dal WAF ripristinato.
5. Conservare gli esiti senza dati reali e rimuovere EC2 ed endpoint temporanei. Sul nuovo account ricreare il lab da Terraform e Ansible con dati vuoti.

## Retention del nuovo lab

| Dati | Conservazione |
|---|---|
| Recovery point EC2 | 7 giorni |
| Log CloudWatch e Flow Logs S3 | 7 giorni |
| Indici giornalieri Wazuh degli alert | 30 giorni con OpenSearch ISM |
| Archivi grezzi Wazuh | Attivi durante le finestre di prova, 7 giorni per i file ruotati; se indicizzati, 7 giorni anche per gli indici giornalieri |
| Inventario, vulnerabilità correnti e configurazioni Wazuh | Retention separata, esclusi dalle policy sugli indici giornalieri |

Ansible installa le policy OpenSearch ISM per i nuovi indici giornalieri e il timer per i file ruotati. La verifica delle policy e del timer è stata eseguita sul SIEM di prova. Il test sui file conferma che il filtro conserva i file attivi, recenti ed estranei. La scadenza automatica degli indici dopo 7 o 30 giorni richiede osservazione sul nuovo lab.

## Decisioni sugli interventi della sezione 7

| Intervento | Decisione |
|---|---|
| Seconda AZ, ALB, WAF e WEB duplicati, NAT per AZ, ASG e SIEM in cluster | Rimandati con RTO non vincolante. Il restore copre il guasto di un nodo. Rivalutare con un RTO concordato e chiarire come gestire lo stato applicativo prima di duplicare WEB. |
| Copie di backup tra regioni o account, replica log | Rimandate per il lab con dati ricreabili. Rivalutare se diventa necessario conservare evidenze dopo la perdita di un account o di una regione. |
| State remoto, MFA, cifratura e accessi | State S3 verificato. Mantenere MFA e credenziali temporanee. Rendere obbligatoria l'approvazione dell'environment prima di collegare OIDC al nuovo account. |
| TLS pubblico, AWS WAF gestito, Shield e servizi di audit avanzati | Rivalutare se emergono requisiti di accesso pubblico senza CA privata, DDoS, audit centralizzato o più account. |
| Enrollment agenti, patch e rete | Priorità alla validazione degli agenti, agli installer revisionati e alla verifica del filtro egress WEB al deploy nel nuovo account. Usare endpoint privati dove migliorano l'isolamento e il rischio operativo. |
| Avvisi, restore e dimensionamento | Monitorare età backup, disco, memoria e latenza. Ripetere il restore dopo modifiche al deploy o ai volumi. Dimensionare il SIEM con prove a carico concordato. |
