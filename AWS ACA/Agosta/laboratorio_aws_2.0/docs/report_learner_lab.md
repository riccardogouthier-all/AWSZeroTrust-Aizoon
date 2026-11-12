> Report storico della prova del 12 novembre 2026. Copia sanitizzata per Git con identificativi live e percorsi personali sostituiti da segnaposto. Per replicare usare il README. Le evidenze selezionate sono in `docs/evidenze`; i riferimenti `evidence/` nel diario indicano file runtime privati originali, non tutti pubblicati.

# Report della prova privata nel Learner Lab

Data della prova: 12 novembre 2026. Gli orari riportati nelle evidenze AWS possono essere UTC; per la lettura locale si usa Europe/Rome.

## Scopo e stato del documento

Questo report descrive le operazioni realmente eseguite per creare il laboratorio AWS, gli errori incontrati, gli adattamenti e le verifiche. È conservato esclusivamente in locale. Nessun file della prova viene pubblicato su GitHub e non vengono creati commit.

La prova utilizza l'account Learner Lab `<ACCOUNT_ID>`, regione `us-east-1`, progetto `aizoon-private-test`. L'ingresso HTTPS del WAF è pubblico per esplicita richiesta del gruppo; le VM web e SIEM restano private.

**Esito:** infrastruttura creata e servizi verificati. Sono operativi web app pubblica tramite WAF, SIEM privato, due agent, monitoring e backup. La prova di recupero dell'applicazione è riuscita. Le risorse principali sono lasciate attive per l'esercitazione cyber. Restano i limiti del laboratorio e le esclusioni documentate di seguito.

## Diario delle operazioni passo per passo

### 1. Verifica delle credenziali

È stato eseguito `aws sts get-caller-identity`. Il profilo AWS preesistente sul computer non era valido. Sono state quindi utilizzate le credenziali temporanee fornite per questa prova tramite un file di credenziali separato, fuori dalla repository. Le credenziali non sono riportate in questo documento, nel Terraform o nei comandi di esempio.

L'identità risultante è una sessione del ruolo `voclabs` nell'account del laboratorio. Il profilo AWS ordinario del computer non è stato sovrascritto.

### 2. Inventario iniziale

Sono state interrogate le istanze EC2 in `us-east-1` e `us-west-2`: non erano presenti istanze. È stata rilevata la VPC predefinita, che non è stata utilizzata per il progetto. Sono state lette le zone disponibili e le offerte dei tipi EC2.

Comandi essenziali: `aws ec2 describe-instances`, `describe-vpcs`, `describe-availability-zones`, `describe-instance-type-offerings`.

### 3. Verifica dei ruoli del laboratorio

`aws iam get-instance-profile` ha confermato la disponibilità di `LabInstanceProfile`, associato a `LabRole`. Sono state lette la trust policy e le policy collegate a LabRole.

Si è scelto di riutilizzare questi oggetti, senza creare o modificare ruoli IAM. Questo profilo ha permessi più ampi di quelli ideali per un ambiente ordinario: è un adattamento al Learner Lab, non un modello di minimo privilegio da copiare in produzione.

### 4. Separazione dei file della prova

I file sono stati creati in `<CARTELLA_PROVA>`, fuori dalla repository Git del progetto. Le sottocartelle principali sono `terraform`, `configuration` ed `evidence`.

### 5. Preparazione degli strumenti locali

È stato riutilizzato Terraform 1.13.5, il cui archivio era stato verificato tramite SHA-256. Il provider installato è HashiCorp AWS 6.73.0, con lock file locale.

È stato creato un ambiente Python isolato con boto3 e Playwright. Il primo tentativo di installare anche Checkov su Python 3.14 ha incontrato risoluzione prolungata delle dipendenze ed è stato interrotto. Checkov è stato quindi installato in un ambiente Python 3.12 separato in Ubuntu WSL. Sono stati scaricati i motori Chromium, Firefox e WebKit per le verifiche browser.

Le installazioni locali non comportano pubblicazione su GitHub.

### 6. Creazione del backend Terraform

Tramite API S3 consentite è stato creato il bucket `aizoon-private-test-state-<ACCOUNT_ID>`, con blocco dell'accesso pubblico, cifratura SSE-S3 e versioning. Terraform è stato inizializzato con backend S3, chiave `private-test/terraform.tfstate` e `use_lockfile=true`.

Il bucket dello state ha un ciclo di vita separato dalle risorse applicative. Deve rimanere disponibile fino al completamento della dismissione.

### 7. Scrittura e validazione Terraform

È stato preparato il Terraform per VPC, subnet, routing, NAT, EC2, Security Group, endpoint S3, Flow Logs, monitoring e AWS Backup. Sono stati corretti due errori iniziali di sintassi HCL nei blocchi delle route. `terraform fmt` e `terraform validate` sono poi terminati correttamente.

Il primo comando di plan ha incontrato un problema di interpretazione degli argomenti in PowerShell; è stato corretto passando gli argomenti come array. I plan salvati sono conservati in locale e i relativi output leggibili sono nella cartella `evidence`.

### 8. Primo deploy e restrizioni effettive

Il primo deploy ha creato la rete e parte delle risorse, ma ha incontrato due restrizioni:

- `ec2:RunInstances` negato per la VM SIEM `t3.xlarge` da una policy del laboratorio.
- `s3:GetBucketObjectLockConfiguration` negato da una Service Control Policy durante una lettura automatica del provider `aws_s3_bucket`.

Un tentativo di leggere il dettaglio della policy del laboratorio tramite `iam:GetPolicy` è stato anch'esso negato. Non sono state modificate o aggirate le policy dell'account.

### 9. Adattamenti ai limiti del Learner Lab

La VM SIEM è stata ridotta a `t3.large`, consentita dal laboratorio, con 2 vCPU, 8 GiB RAM e disco da 50 GiB. Questo è inferiore alla raccomandazione CPU del quickstart Wazuh di 4 vCPU: il funzionamento viene provato sul carico ridotto dei due agent e non attesta capacità per carichi superiori.

Il bucket dei log, già creato, è stato mantenuto e rimosso dalla sola gestione della risorsa Terraform di base che richiedeva la lettura S3 vietata. Le configurazioni di sicurezza, cifratura, policy e conservazione sono gestite tramite risorse e API consentite. Non è stato richiesto né ottenuto accesso alla configurazione Object Lock vietata.

### 10. Apertura dell'ingresso pubblico

Inizialmente l'ingresso era limitato all'IP pubblico rilevato del tester. Su richiesta esplicita, il Security Group del WAF è stato aggiornato per consentire TCP 443 da `0.0.0.0/0`.

La porta 3000 di Juice Shop è consentita solo dal Security Group del WAF; le porte Wazuh 1514 e 1515 sono consentite solo dai gruppi delle VM web e WAF. Non sono state aperte porte SSH o pubblicata la dashboard SIEM.

### 11. Completamento della prima infrastruttura

Il deploy adattato è terminato correttamente. È stato anche corretto il comportamento di `associate_public_ip_address` sul WAF per evitare che l'associazione dell'Elastic IP fosse interpretata come una differenza da correggere ricreando l'istanza a ogni piano successivo.

### 12. Configurazione tramite SSM e Ansible

Le tre istanze sono risultate Online in Systems Manager. Per questa prova privata, i playbook Ansible vengono inviati tramite SSM Run Command ed eseguiti localmente sulle singole EC2. Non è stato attivato un controller Ansible esterno con plugin SSM e bucket di scambio: il trasporto viene gestito dagli script locali `ops.py` e `configure.py`.

Questa scelta permette di lavorare dal computer Windows senza aprire SSH. Le esecuzioni SSM e i loro esiti sono registrati in `evidence/commands.jsonl` e nei file JSON delle invocazioni.

### 13. Installazione della web app e del WAF

Ansible ha installato Docker e avviato Juice Shop sulla VM privata. Il WAF utilizza l'immagine ufficiale OWASP ModSecurity CRS con nginx. Le immagini vengono risolte una volta e avviate tramite digest; il digest effettivo resta registrato sulle VM in `/opt/aizoon`.

Il WAF è configurato con upstream verso l'IP privato della web app, modalità `DetectionOnly`, log accessi/errori/audit e riavvio automatico dei container. È presente uno script che accetta esclusivamente `On` o `DetectionOnly` per cambiare modalità.

### 14. Configurazione HTTPS sull'IP

Sul WAF sono stati generati una CA privata del laboratorio e un certificato server con l'IP pubblico nel SAN. Le chiavi restano sulla VM in una directory riservata a root. Solo il certificato pubblico della CA viene copiato sul computer come `lab-ca.crt`.

La prima richiesta alla web app ha restituito HTTP 200, con verifica della catena TLS e dell'IP tramite la CA del laboratorio. Nei browser ordinari la CA deve essere considerata attendibile dal dispositivo, altrimenti compare un avviso.

### 15. Installazione Wazuh e agent

Il SIEM utilizza l'installation assistant ufficiale della serie Wazuh 4.14. L'output che contiene le password generate è rediretto in un file privato sulla VM e non viene stampato nel report o nei log SSM.

Gli agent web e WAF sono installati da repository firmato, scegliendo una versione della serie 4.14. È stato corretto un errore di shell `141`: con `pipefail`, l'uscita anticipata di awk interrompeva la lettura dell'elenco versioni. La selezione ora consuma l'intero input e l'installazione è stata ripetuta.

### 16. Monitoring e percorso degli allarmi

Sono stati creati allarmi CloudWatch per CPU, stato EC2, memoria, disco e disponibilità HTTPS. Gli agent CloudWatch raccolgono le metriche di sistema; un timer sul WAF effettua una richiesta HTTPS verificando il certificato tramite la CA e pubblica `HTTPSAvailable`.

Le notifiche passano da CloudWatch a SNS e a una coda SQS privata. Questo consente di provare il percorso senza inviare email o messaggi ad altre persone. È stato simulato lo stato ALARM di un allarme CPU: la relativa notifica è arrivata nella coda; lo stato è stato poi riportato a OK. Si tratta di una simulazione del percorso di notifica, non di un guasto CPU reale.

### 17. Scansione Checkov e modifica con ricreazione delle VM

La prima scansione ha prodotto 97 controlli superati e 26 segnalazioni, senza errori di parsing. Sono state aggiunte descrizioni ai gruppi e alle regole di sicurezza ed esplicitata l'ottimizzazione EBS.

Questa modifica Terraform ha comportato la sostituzione dei Security Group e delle tre EC2 già inizializzate. Il piano di sostituzione non è stato valutato con sufficiente attenzione prima di applicarlo: è un errore operativo di questa prova. L'effetto è stata l'interruzione dei servizi e dell'installazione Wazuh in corso, con perdita della prima configurazione sulle VM.

Il problema è stato comunicato durante l'esecuzione. La rete e l'Elastic IP sono rimasti disponibili; le nuove VM sono state configurate nuovamente tramite gli stessi playbook. Le verifiche finali devono riferirsi a queste nuove istanze, non alla generazione precedente.

La scansione successiva ha prodotto 116 controlli superati e 7 segnalazioni, senza controlli saltati o errori di parsing. Non viene dichiarata una scansione interamente superata.

### 18. Test browser della prima generazione e ripetizione finale

Sulla prima generazione la web app è stata caricata con Chromium, Firefox e WebKit, sia desktop sia viewport mobile, con HTTP 200 e prodotti visibili. I primi screenshot hanno mostrato che il popup di benvenuto non veniva chiuso correttamente dal test: il selettore è stato corretto e la checklist è stata estesa alla visualizzazione del form di login.

Queste prove devono essere ripetute sull'infrastruttura finale dopo la ricreazione. I contesti browser di automazione non installano la CA nello store del sistema e quindi ignorano l'errore di attendibilità; la verifica crittografica TLS viene eseguita separatamente usando `lab-ca.crt`. Le viewport mobile non equivalgono a test su telefoni fisici.

### 19. Backup e preparazione della prova di ripristino

Sono stati creati un vault AWS Backup e un piano giornaliero con conservazione di un giorno, usando LabRole. È stato avviato anche un backup su richiesta della VM web della prima generazione, job `d4eba97d-10db-46a8-9052-d3ff8ec90eb9`.

L'esito definitivo e la prova di ripristino sono riportati nei risultati finali. L'avvio del job, da solo, non dimostra che il backup sia recuperabile.

### 20. Verifica dei costi e perimetro CI/CD

Una lettura dei prezzi tramite `pricing:GetProducts` è stata negata dal ruolo. I costi non possono quindi essere attestati tramite il catalogo interrogato dall'account.

Per questa prova non è stata attivata GitHub Actions: l'istruzione di non caricare niente su Git è rispettata. I deploy sono stati eseguiti localmente con Terraform e Ansible su autorizzazione esplicita dell'utente. La pipeline GitHub con approvazione rimane parte del progetto generale, non una funzionalità collaudata in questa prova.

## Risultati finali

### 21. Verifica della configurazione finale

La seconda installazione dei tre servizi è stata completata con esito positivo. Gli agent CloudWatch sono stati configurati su tutte le VM e hanno pubblicato dati di memoria e disco per ciascuna istanza finale. Alcuni riavvii dei servizi durante l'installazione dei pacchetti hanno provocato disconnessioni temporanee degli agent Wazuh, che si sono poi riconnessi. Il controllo finale mostra entrambi gli agent Active.

### 22. Prova del WAF e raccolta nel SIEM

È stata inviata una richiesta sintetica XSS al solo endpoint del laboratorio. In `DetectionOnly` ha restituito 200; in modalità `On` ha restituito 403; la pagina ordinaria ha continuato a restituire 200. Lo script usa un blocco di ripristino per riportare il WAF in `DetectionOnly` anche in caso di errore.

La prova è stata ripetuta dopo l'attivazione del SIEM. È stato aggiunto un input specifico per il file audit JSON di ModSecurity. Wazuh ha ricevuto le transazioni audit e generato gli eventi 31105, 31333 e la regola locale 100100. Le evidenze SSM riportano gli orari degli eventi; non è stato eseguito l'attacco di login admin previsto per il futuro lavoro del red team.

### 23. Verifiche funzionali e browser finali

Sono passate sei combinazioni: Chromium, Firefox e WebKit, ciascuno con viewport desktop e mobile. Sono stati verificati caricamento della pagina, presenza dei prodotti, chiusura del popup di benvenuto e visibilità del form di login, senza errori JavaScript rilevati nelle prove. Sono stati salvati screenshot.

Separatamente sono state provate ricerca prodotti, registrazione di un account sintetico e login ordinario via API, con verifica TLS attiva: registrazione 201 e login 200 con token ricevuto. Password e token dell'account sintetico non sono stati salvati nelle evidenze.

Il test mobile è una simulazione della viewport, non una prova su dispositivi fisici; WebKit automatizzato non equivale a una certificazione di tutte le versioni di Safari. I test browser ignorano l'attendibilità della CA privata nei propri contesti isolati, mentre le verifiche HTTPS e API controllano catena e SAN usando la CA esportata.

### 24. Completamento del backup e prova di recupero

Il job AWS Backup è terminato in stato `COMPLETED`. Ha prodotto l'immagine privata `<ami_ID>` e lo snapshot cifrato `<snap_ID>`, della VM web della prima generazione. La prima VM sorgente era stata nel frattempo eliminata dalla ricreazione Terraform.

Quando l'immagine era disponibile ma il job AWS Backup era ancora in fase di finalizzazione, la lettura dei metadati di ripristino del vault ha restituito `ResourceNotFoundException`. Per provare il recupero è stata avviata direttamente una EC2 dall'AMI generata da AWS Backup; non è stato usato `StartRestoreJob` e non si dichiara collaudato quel percorso API.

La VM temporanea `<INSTANCE_ID>` è stata avviata in subnet privata con Security Group `<sg_ID>`, senza ingressi e con sola uscita HTTPS per la gestione SSM. Dopo l'avvio e la registrazione in SSM, Docker ha riavviato Juice Shop e una richiesta a `http://127.0.0.1:3000/` ha verificato il contenuto atteso, senza reinstallare l'applicazione: `RESTORED_JUICE_SHOP_OK`.

La VM temporanea è stata terminata e il relativo Security Group è stato eliminato. L'immagine e il recovery point di backup rimangono soggetti alla conservazione configurata. Il backup provato riguarda la prima generazione web; il piano giornaliero è invece aggiornato alle tre istanze finali. Non sono stati eseguiti tre ripristini distinti né validata consistenza applicativa sotto carico.

### 25. Dashboard Wazuh e verifica della catena di rilevamento

È stato scaricato il Session Manager plugin ufficiale, versione 1.2.896.0, in una cartella privata della prova. È stato aperto un tunnel verso la porta 443 del SIEM, esposto solo localmente su `https://localhost:8443`.

La pagina di login Wazuh ha risposto 200 tramite il tunnel ed è stato salvato uno screenshot. Un controllo autenticato dell'indexer, con credenziali lette e usate esclusivamente sulla VM senza stamparle, ha verificato cluster `green`, un nodo e 883 alert indicizzati al momento del controllo. La UI autenticata della dashboard non è stata provata.

### 26. Controlli di chiusura della prova

Il controllo di drift Terraform ha restituito exit code 0 e `No changes`. L'inventario ha confermato che web e SIEM non hanno IP pubblico e che tutte le istanze usano IMDSv2 ed EBS optimized.

Dal computer del tester è stata verificata la raggiungibilità di TCP 443 sull'IP pubblico e la mancata raggiungibilità delle porte 22, 3000, 1514, 1515, 9200 e 55000. Non si tratta di una scansione esaustiva di tutte le porte.

Sono stati verificati 13 allarmi CloudWatch, dati di memoria e disco delle tre VM, file Flow Logs nel bucket S3 e stream di log di sistema in CloudWatch. La prima scansione Checkov e quella finale sono conservate entrambe, senza nascondere le segnalazioni residue.

Lo stato Git della repository del progetto è rimasto sul commit precedente, con il solo `baseline.md` locale già presente come file non tracciato. Non sono stati effettuati commit, push o modifiche alla baseline durante questa prova.

### Quadro dei risultati

| Controllo | Risultato | Evidenza principale |
| --- | --- | --- |
| Terraform e drift | Valido; nessuna modifica richiesta dal piano finale | `evidence/terraform-drift-check.txt` |
| Web app pubblica via WAF | HTTP 200 con TLS verificato usando la CA privata | `evidence/functional-api-tests.json` |
| Isolamento web e SIEM | Nessun IP pubblico; flussi tramite Security Group | `evidence/final-instance-inventory.json`, `security-groups.json` |
| Porte pubbliche controllate | Solo 443 raggiungibile tra quelle provate | `evidence/public-port-check.json` |
| Browser e viewport | Sei combinazioni superate | `evidence/browser-results.json`, screenshot PNG |
| Registrazione e login ordinario | 201 e 200; account sintetico | `evidence/functional-api-tests.json` |
| WAF in rilevamento e blocco | 200 in DetectionOnly, 403 in On; richieste normali 200 | `evidence/waf-test-results.json` |
| Stato finale WAF | DetectionOnly per la prima fase cyber | `evidence/waf-test-with-siem-run.txt` |
| Wazuh | Manager, indexer, dashboard e Filebeat attivi; due agent Active | Invocazioni SSM in `evidence/commands.jsonl` |
| Detection e audit | Eventi WAF e regola 100100 ricevuti; transazioni audit archiviate | `evidence/f2af9a38-bbd0-4b42-833d-b36ce49a718d.json` |
| Indicizzazione | Cluster green e 883 alert al momento della verifica | `evidence/24876900-6e16-4f4b-bd3a-4b3c8cb8fce4.json` |
| Metriche | Memoria e disco con datapoint per tutte le VM finali | `evidence/final-metric-check.json` |
| Allarmi e notifica | 13 allarmi; messaggio di test ricevuto in SQS | `evidence/final-alarms.json`, `notification-test.json` |
| Backup | Job completato, snapshot cifrato | `evidence/backup-job-status.json` |
| Recupero applicazione | VM da AMI AWS Backup, Juice Shop operativo senza reinstallazione | `evidence/restore-check-result.json` |
| Pulizia del ripristino | VM temporanea terminata e SG eliminato | `evidence/restore-resources.json` |
| Checkov | 116 passati, 7 segnalazioni, 0 saltati, 0 errori parsing | `evidence/checkov-final.json` |
| GitHub Actions | Non attivata per mantenere la prova privata | Nessun caricamento Git |

## Inventario delle risorse principali finali

| Ruolo | EC2 | Tipo | IP privato | IP pubblico |
| --- | --- | --- | --- | --- |
| WAF | `<INSTANCE_ID>` | t3.small | `10.20.1.151` | `<IP_WAF>` |
| Web | `<INSTANCE_ID>` | t3.small | `10.20.2.19` | Nessuno |
| SIEM | `<INSTANCE_ID>` | t3.large | `10.20.2.212` | Nessuno |

Altre risorse principali:

- VPC: `<vpc_ID>`, CIDR `10.20.0.0/16`.
- Subnet privata: `<subnet_ID>`.
- NAT Gateway: `<nat_ID>`.
- Elastic IP del WAF: `<eipalloc_ID>`.
- Flow Log: `<fl_ID>`.
- Bucket state: `aizoon-private-test-state-<ACCOUNT_ID>`.
- Bucket log: `aizoon-private-test-logs-<ACCOUNT_ID>`.
- Backup vault: `aizoon-private-test-backup`.
- Log group: `/aizoon-private-test/system`.
- Namespace delle metriche custom: `AizoonLab`.
- Topic SNS e coda SQS: `aizoon-private-test-alerts`.

L'inventario completo con gli output Terraform è in `evidence/outputs.json`.

## Segnalazioni Checkov residue e limiti

| Segnalazione | Situazione rilevata e trattamento nella prova |
| --- | --- |
| CKV_AWS_158 | Il log group non usa una chiave KMS personalizzata. Non viene dichiarata la conformità a quel requisito. |
| CKV_AWS_338 | La conservazione CloudWatch è di 7 giorni, coerente con la prova temporanea; il check richiede almeno un anno. |
| CKV_AWS_26 | Il topic SNS non ha cifratura KMS configurata. Le notifiche di prova non contengono credenziali; è una segnalazione aperta da riesaminare prima di un uso ordinario. |
| CKV_AWS_166 | Il vault non utilizza una CMK personalizzata. Lo snapshot verificato è comunque cifrato; il requisito specifico della CMK non è soddisfatto. |
| CKV_AWS_394 | La scelta della prima AZ disponibile non è fissata a una zone identity. Per questa esecuzione è stata usata us-east-1a; una nuova creazione richiede revisione del piano. |
| CKV2_AWS_5, due risorse | L'analisi statica segnala SG WAF e web come non collegati. L'inventario EC2 reale conferma entrambi i collegamenti; il riscontro è conservato senza cancellare i finding. |

Altri limiti: LabRole ha privilegi ampi; il SIEM ha due vCPU; non è stata svolta una prova di carico né una certificazione su dispositivi fisici. Non è stata eseguita una campagna red team o verificato il login admin vulnerabile. Gli utenti e le regole operative dei team devono ancora essere organizzati per l'esercitazione.

Le notifiche sono recapitate a una coda privata, non a una persona: nessun destinatario email o SMS è stato configurato. Il controllo HTTPS parte dal WAF stesso e verifica il percorso pubblico verso l'app, ma non equivale a un servizio di monitoring esterno indipendente.

## Accesso e gestione

La web app utilizza l'Elastic IP `<IP_WAF>` sulla porta HTTPS. Dashboard Wazuh e shell amministrative richiedono un'identità AWS autorizzata e Systems Manager.

### Web app

Aprire `https://<IP_WAF>`. Il certificato è di laboratorio. Per una verifica da terminale senza ignorare TLS:

```powershell
curl.exe --cacert .\lab-ca.crt https://<IP_WAF>/
```

Il file `lab-ca.crt` è il certificato pubblico, non contiene la chiave privata. L'eventuale importazione della CA nello store di un dispositivo va gestita esplicitamente; il deploy non l'ha installata nello store Windows dell'utente.

### Dashboard e shell Wazuh

È stato aperto un tunnel locale per questa sessione. Se necessario, con credenziali AWS temporanee valide:

```powershell
.\Open-WazuhTunnel.ps1
```

La dashboard è disponibile su `https://localhost:8443`. Lo script non pubblica la dashboard su Internet. Per chiudere il tunnel usare Ctrl+C se avviato interattivamente oppure interrompere il processo di tunnel registrato in `evidence/wazuh-tunnel.pid`, verificando prima che il PID corrisponda ancora al tunnel.

La shell amministrativa si apre con:

```powershell
$env:PATH = "$PWD\tools\session-manager\package\bin;$env:PATH"
aws ssm start-session --region us-east-1 --target <INSTANCE_ID>
```

L'utente dashboard è `admin`. La password generata resta solo sulla VM. Dalla shell SSM autorizzata può essere letta nel file dell'installer:

```bash
sudo tar -O -xf /opt/aizoon/wazuh-install-files.tar wazuh-install-files/wazuh-passwords.txt
```

Questo comando mostra segreti: eseguirlo solo nella propria sessione amministrativa e non copiarne l'output nel repository o nel report.

### Modifica controllata della modalità WAF

Dalla shell SSM della VM WAF:

```bash
sudo /opt/aizoon/set-waf-mode.sh On
# Per tornare alla baseline:
sudo /opt/aizoon/set-waf-mode.sh DetectionOnly
```

La modalità finale lasciata al gruppo è `DetectionOnly`: l'applicazione vulnerabile resta raggiungibile per la prima fase degli attacchi.

### Ripetizione dei controlli locali

Gli script richiedono credenziali temporanee valide per lo stesso account. Gli esempi sono da eseguire dalla cartella della prova:

```powershell
.\.venv\Scripts\python.exe browser_tests.py
.\.venv\Scripts\python.exe waf_tests.py
```

`waf_tests.py` cambia temporaneamente la modalità del WAF e la ripristina: non eseguirlo mentre il team cyber sta svolgendo una prova senza concordarlo.

Gli helper cercano il file di credenziali temporaneo privato solo se ancora presente; altrimenti utilizzano la normale catena delle credenziali AWS. Per un nuovo accesso occorre aggiornare le credenziali dal Learner Lab. Le credenziali della prova vengono rimosse dal file temporaneo al termine del lavoro; non sono comprese nella cartella consegnata.

Lo spegnimento delle EC2 non elimina i costi di NAT, indirizzi IPv4, dischi, log e backup. La dismissione completa richiede Terraform e la pulizia controllata delle risorse create fuori dal suo state. Non eliminare il bucket dello state prima di aver concluso la distruzione.

### Dismissione a fine esercitazione

La dismissione non è stata eseguita sulle risorse principali, che restano attive. Quando il gruppo termina la prova:

1. Salvare le evidenze necessarie e chiudere i tunnel SSM.
2. Verificare lo stato del job e i recovery point nel vault dedicato. Il vault non vuoto è protetto dalla distruzione forzata: attendere la scadenza o eliminare esplicitamente i soli recovery point di questa prova se non servono più.
3. Dalla cartella `terraform`, con le credenziali aggiornate, eseguire `terraform plan -destroy` e controllare l'elenco; poi `terraform destroy` per rimuovere le risorse gestite, inclusi NAT ed Elastic IP.
4. Controllare che non rimangano istanze o Security Group di ripristino. La VM temporanea di questa esecuzione è già stata eliminata.
5. Svuotare ed eliminare, se non più necessario, il solo bucket log `aizoon-private-test-logs-<ACCOUNT_ID>`, la cui risorsa di base è stata gestita fuori dal Terraform per il limite Object Lock.
6. Conservare lo state fino alla verifica finale. Solo dopo la dismissione, se si vuole eliminare anche il backend, rimuovere esplicitamente tutte le versioni degli oggetti e il bucket dedicato dello state.
7. Ricontrollare risorse con tag `Project=aizoon-private-test`, recovery point, snapshot e indirizzi pubblici. Non intervenire su risorse estranee o sulla VPC predefinita.

## Costi e conservazione

Non è stato prodotto un consuntivo di fatturazione: il ruolo non consente la lettura del catalogo prezzi tramite l'API tentata. Le pagine ufficiali sono riportate nei riferimenti per il preventivo del gruppo.

Il costo operativo comprende due t3.small, una t3.large, 90 GiB di dischi gp3, un NAT Gateway, due IPv4 pubblici, metriche e allarmi, log, S3 e backup. Anche le VM eliminate durante le ricreazioni e la VM temporanea di recupero hanno consumato risorse per la durata di utilizzo. Le istanze T3 possono avere addebiti aggiuntivi per CPU in modalità Unlimited in funzione del carico.

Come riferimento separato dal costo totale, il listino pubblico AWS indica 0,005 USD/ora per IPv4 pubblico: i due indirizzi del progetto equivalgono a 0,01 USD/ora di soli IPv4, escluso il resto. Il bucket state ha versioning senza scadenza automatica delle versioni; i log di sistema e i Flow Logs hanno conservazione breve e il backup giornaliero una conservazione di un giorno. [Prezzi IPv4 AWS](https://aws.amazon.com/vpc/pricing/).

La prova non è un ambiente produttivo: l'ingresso pubblico di Juice Shop è intenzionale e autorizzato per l'esercitazione. Non inserire dati reali o credenziali personali nell'applicazione vulnerabile.

## Riferimenti tecnici

- [Wazuh quickstart](https://documentation.wazuh.com/current/quickstart.html)
- [Immagine ufficiale OWASP ModSecurity CRS](https://github.com/coreruleset/modsecurity-crs-docker)
- [AWS Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html)
- [Prezzi EC2 T3](https://aws.amazon.com/ec2/instance-types/t3/)
- [Prezzi VPC](https://aws.amazon.com/vpc/pricing/)
- [Prezzi EBS](https://aws.amazon.com/ebs/pricing/)
