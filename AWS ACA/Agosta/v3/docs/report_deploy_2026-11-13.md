# Deploy del laboratorio nell'account personale AWS

**Diario storico del 13 novembre 2026.** Questa è la copia pubblicabile della procedura effettivamente eseguita. I riferimenti a state, file privati e output integrali descrivono il workspace dell’operatore: tali file non sono inclusi in Git. I risultati selezionati sono in [evidenze/](evidenze/). Le note sul mancato commit descrivono il momento del deploy; la pubblicazione successiva è la v3. Per replicare usare il [README v3](../README.md); per gli accessi usare la [guida breve in Defence](../../../../Cyber%20CYS/Defence/ACCESSO_BLUE_TEAM_v3.md).

Data: 13 novembre 2026. Fuso orario delle comunicazioni: Europe/Rome.

## Scopo

Ottenere i 100 USD aggiuntivi previsti dalle attività Free Tier, quindi creare il laboratorio a partire dal Terraform di `AWS ACA/Gouthier/tentativo 2`, letto dalla repository aggiornata al commit `3b5066c`.

La copia di deploy, lo state e le evidenze sono conservati in questa cartella locale. Le credenziali AWS sono quelle del profilo configurato dall'utente e non vengono copiate nel progetto o nel report. Non è stato richiesto un aggiornamento del piano a pagamento.

## Operazioni eseguite passo per passo

### 1. Identificazione dell'account e verifica dei permessi

`aws sts get-caller-identity` ha identificato l'utente IAM `codex-progetto` nell'account personale. Le prime chiamate a EC2, IAM e Free Tier sono state negate perché l'utente non aveva policy assegnate.

La console AWS già autenticata ha confermato zero policy sull'utente. È stata preparata l'associazione di `AdministratorAccess`; l'utente ha confermato esplicitamente questa modifica prima dell'applicazione. La policy è stata quindi associata e verificata tramite API IAM. Nessuna nuova access key è stata creata.

Questo accesso del controller è completo e persistente. I ruoli delle VM e di AWS Backup sono invece dedicati al progetto e descritti più avanti.

### 2. Verifica del piano Free

Le API `GetAccountPlanState` e `ListAccountActivities` hanno confermato:

- Piano `FREE`, stato `ACTIVE`.
- Saldo iniziale: 100 USD.
- Scadenza del piano: 28 novembre 2026 alle 11:27 circa, ora italiana.
- Sei attività disponibili da 20 USD ciascuna; ne sono state eseguite cinque per ottenere i 100 USD aggiuntivi.

Il credito è espresso in dollari statunitensi, non in euro. La scadenza del piano non deve essere confusa con la scadenza dei singoli crediti. Il piano non è stato trasformato in `PAID` e non sono state attivate le advanced features.

### 3. Creazione di un budget di costo

È stato creato il budget mensile `aizoon-personal-cost-budget` da 20 USD, con crediti e rimborsi esclusi dal calcolo del consumo monitorato. Questa operazione ha completato l'attività Budgets.

Il budget è conservato come strumento di osservazione. In questa prima fase non arrestava automaticamente le risorse (successivamente è stata aggiunta l’azione del punto 16); non sono stati aggiunti destinatari email o SMS.

### 4. Attività DynamoDB

È stata creata una tabella temporanea con una chiave stringa e fatturazione a richiesta. L'attività è risultata completata e la cancellazione della tabella è stata richiesta dopo il riconoscimento del credito. Non sono stati inseriti dati personali.

### 5. Attività EC2

È stata avviata una t3.micro temporanea nella VPC predefinita, senza IP pubblico, senza ingressi autorizzati, con disco cifrato e IMDSv2. Dopo l'esito positivo dei controlli EC2 è stata richiesta la terminazione. L'attività è poi risultata completata.

Questa VM non è una delle macchine del progetto e non è stata usata per ospitare Juice Shop.

### 6. Attività RDS

È stato creato un database PostgreSQL 18.3 su db.t4g.micro, Single-AZ, con storage gp3 cifrato da 20 GiB, non pubblico e senza ingressi di rete. La password generata è stata usata solo per la richiesta API e non è stata salvata o stampata.

L'attività è stata accreditata. Dopo che RDS ha raggiunto `available`, è stata richiesta la cancellazione senza snapshot finale e senza mantenere backup automatici, trattandosi esclusivamente di una risorsa temporanea vuota per questa attività.

### 7. Attività Lambda

Sono stati creati una funzione Python e un ruolo di esecuzione con il solo accesso di base ai log Lambda. La funzione esponeva una Function URL con autenticazione IAM; una richiesta firmata ha ricevuto HTTP 200.

L'attività è risultata completata. Function URL, funzione, ruolo e log dedicati sono stati successivamente eliminati.

### 8. Verifica dell'accredito

Prima di avviare l'infrastruttura del progetto, le API hanno confermato le cinque attività `COMPLETED` e un saldo di **200 USD**: 100 USD iniziali più 100 USD aggiuntivi. L'attività Bedrock non è stata necessaria e non è stata eseguita.

Le evidenze iniziali e aggiornate sono in `evidence/credits-before.json`, `activities-before.json`, `activities-current.json` e `plan-current.json`. Il saldo successivo può diminuire per l'uso dei servizi.

### 9. Lettura e adattamento del progetto di Gouthier

È stata copiata fuori dalla repository la versione `tentativo 2`, che usa Terraform e cloud-init per installare i componenti senza Ansible. I file originali nella repository non sono stati modificati per questo deploy.

Gli adattamenti locali sono:

- Regione `us-east-1`, progetto `aizoon-personal` e ingresso HTTPS pubblico sul WAF.
- Creazione di un ruolo EC2 e instance profile dedicati, con `AmazonSSMManagedInstanceCore` e `CloudWatchAgentServerPolicy`.
- Creazione di un ruolo AWS Backup dedicato con policy AWS per backup e restore.
- Rimozione della dipendenza dal ruolo preesistente `LabRole` del Learner Lab.
- Gestione ordinaria del bucket log tramite `aws_s3_bucket`, con `logs_bucket_via_cli=false`.
- SIEM proposto su t3.xlarge, con 4 vCPU e 16 GiB, al posto della t3.large ridotta della prova Learner Lab.

La quota EC2 consultata è di 32 vCPU On-Demand per la categoria standard. Un controllo `DryRun` per t3.xlarge ha restituito `DryRunOperation`, indicando che la richiesta preliminare sarebbe stata autorizzata.

### 10. Validazione e approvazione del deploy

Sono stati eseguiti `terraform fmt`, `terraform init` e `terraform validate`, con esito positivo. Anche gli script shell sono stati verificati con `bash -n`.

Il piano salvato prevedeva **67 creazioni, zero modifiche e zero distruzioni**. Il deploy è stato avviato su richiesta esplicita dell'utente, applicando quel piano salvato. Lo state è locale nella cartella `project`, come nella versione di Gouthier; non è pubblicato in Git.

## Stato finale e verifiche

### 11. Problema reale del piano Free e adattamento del SIEM

Il primo apply ha creato rete, storage e le VM WAF e WEB, ma AWS ha rifiutato t3.xlarge con `InvalidParameterCombination: The specified instance type is not eligible for Free Tier`. Il precedente DryRun non aveva rilevato questo limite commerciale del piano.

È stata interrogata la lista effettiva con il filtro `free-tier-eligible=true`. Tra i tipi x86 compatibili con Ubuntu e Wazuh, m7i-flex.large offre 2 vCPU e 8 GiB. Il Terraform locale è stato aggiornato a questo tipo; il piano di ripresa prevedeva 14 creazioni, zero modifiche e zero distruzioni. L'apply di ripresa è terminato correttamente. Il piano è rimasto FREE.

Le tre istanze attive sono:

| Ruolo | Istanza | Tipo | IP privato | Ingresso pubblico |
|---|---|---|---|---|
| WAF | i-0fe2d9e03e1dbd54f | t3.small, 2 GiB | 10.20.1.10 | HTTPS 32.201.245.48:443 |
| WEB | i-004d56b002f3b23a1 | t3.small, 2 GiB | 10.20.2.10 | Nessuno |
| SIEM | i-05e152bb6ec353ac1 | m7i-flex.large, 8 GiB | 10.20.2.11 | Nessuno |

Lo state è in `project/terraform.tfstate`. Tutti i nodi risultano Online in Systems Manager. `cloud-init status --long` ha raggiunto `done`, senza errori, su tutti e tre. Wazuh 4.14.10 ha completato il bootstrap; manager, indexer, dashboard e Filebeat risultano attivi.

### 12. Configurazioni pubblicate dal team cyber

Su richiesta dell'utente è stato eseguito un nuovo fetch e fast-forward della repository al commit `169a747`. È stato letto il contributo completo `Cyber CYS/Defence/Finocchielli`: manuale, ruoli WAF/SIEM/agenti, template, sonda, verificatore e test.

Il manuale distingue il tentativo 2 già configurato dalle VM dedicate ai playbook Ansible. Per adottare le loro configurazioni senza avviare un secondo WAF sulla 443 o reinstallare Wazuh è stato creato l'adattatore locale `apply_cyber.py`, che le applica via SSM alle VM esistenti. La copia originale del contributo è in `cyber/`.

Sono stati applicati:

- La regola originale `REQUEST-900-BLUE-TEAM.conf`, ID 10001, montata nel ruleset CRS del container esistente.
- DetectionOnly, audit JSON seriale, RelevantOnly e parti AHZ.
- Le sorgenti originali del template cyber: access/error/audit sul WAF; solo il LogPath del container Juice Shop sul WEB. L'audit viene inoltrato con il prefisso `bt_waf_audit`, evitando i limiti degli array di oggetti nel decoder JSON standard.
- Rotazione dei file WAF, massimo 20 MiB, quattro rotazioni; limiti dei log Docker 5 MiB per due file.
- Blocco degli upgrade isolati dei pacchetti Wazuh/Filebeat.
- Archiviazione degli eventi grezzi sul manager per la finestra di collaudo.

Sono rimasti la CA privata esistente, il certificato per l'EIP, il container `aizoon-waf` e le identità degli agenti già registrati. `/opt/blue-team/logs` è un collegamento ai log esistenti in `/opt/aizoon/logs`, per utilizzare il verificatore cyber originale senza cambiarlo. Il WAF ascolta sul solo IP privato 10.20.1.10:443, tradotto nell'EIP da AWS. Sono state salvate copie delle configurazioni precedenti sui nodi per il ripristino.

Non sono stati eseguiti alla cieca l'inventario di esempio in eu-west-1 né il bootstrap destinato a VM nuove. Non è stato cambiato il codice cyber nella repository.

### 13. Collaudo della catena cyber

I sei test offline del contributo cyber sono passati. L'adattatore ha superato il controllo di generazione dei sette payload SSM, la compilazione dei blocchi Python e `bash -n`; il controllo conferma anche l'assenza di reinstallazione del manager.

La sonda originale `cyber/tools/probe.py` ha ricevuto 200 sia dalla pagina sia dalla richiesta marcata, con verifica della CA e del SAN dell'IP. Il verificatore originale eseguito su WAF e manager ha trovato:

- Marker: `bt-fa7b0130b448488ba8ec286656026451`.
- ID transazione comune: `17945831688.770935`.
- Regola di collaudo 10001, modalità DetectionOnly, risposta 200 e firma OWASP CRS 4.30.0.
- Sul manager, origine agente `waf` e audit dalla location prevista dal contributo.

Il comando `agent_control -lc` mostra `waf` e `web` Active; il riscontro è stato ripetuto anche dopo la chiusura della finestra di archiviazione. È stata verificata anche la riga access.log dello stesso marker sul manager. La salute dell'indexer è stata interrogata con autenticazione, leggendo la password esclusivamente in memoria sul SIEM: stato green, un nodo, 23 shard primari attivi. Sono stati inoltre contati 1195 documenti negli indici wazuh-alerts-* con una richiesta autenticata. Il numero riguarda l’intero bootstrap e collaudo, non 1195 attacchi. Password e chiavi non sono state esportate nei report o negli output SSM.

### 14. Verifiche applicative, TLS e difesa

Sono stati verificati ricerca prodotti, creazione di un utente sintetico e login: HTTP 201 alla registrazione e HTTP 200 con token al login. La password e il token di questo account di prova non sono conservati.

I test Playwright su Chromium, Firefox e WebKit, ciascuno in viewport desktop e mobile, hanno verificato pagina, prodotti e modulo login senza errori JavaScript. Gli screenshot sono in `evidence/`. Sono prove di viewport su browser desktop, non prove su telefoni fisici o su ogni versione dei browser.

La catena TLS e il SAN dell'EIP sono verificati con la CA esportata in `lab-ca.crt`. I contesti Playwright ignorano la fiducia nella CA privata; non è stata modificata la trust store di Windows. Il browser di un compagno mostrerà un avviso finché non avrà verificato e installato la CA del laboratorio.

La prova controllata del WAF ha restituito 200 in DetectionOnly, 403 alla sonda XSS in modalità On e 200 alla pagina normale. Infine è stata ripristinata DetectionOnly e verificato nuovamente HTTP 200. Questa è la baseline finale per le esercitazioni asincrone; non equivale a un pentest completo né a tuning dei falsi positivi.

La dashboard Wazuh è raggiungibile soltanto tramite SSM. Sul tunnel locale di questa esecuzione, `https://localhost:8444`, la pagina di login ha restituito 200 e mostra il modulo password. Il login autenticato nella UI non è stato eseguito; la verifica autenticata riguarda l'indexer e gli agenti sono stati verificati sul manager.

### 15. Monitoring, backup e pulizia

Al controllo conclusivo tutti i tredici allarmi risultano OK. Sono presenti tredici allarmi CloudWatch, metriche di memoria/disco per le tre VM, metrica HTTPSAvailable, log di sistema e VPC Flow Logs nel bucket privato. Una transizione sintetica dell'allarme CPU del WEB ha attraversato SNS e raggiunto SQS; è stata riconosciuta e l'allarme è stato riportato a OK. Questa prova verifica la consegna, non simula un incidente CPU reale. Non sono configurate notifiche personali email/SMS.

AWS Backup contiene un piano giornaliero alle 02:00 UTC per le tre istanze, con conservazione di un giorno. È stato avviato anche un job reale sul WEB; lo stato definitivo è riportato nel riepilogo conclusivo. Lo snapshot EBS del job è cifrato. Un ripristino completo dell'applicazione non è stato collaudato.

Le risorse temporanee usate per i crediti sono state rimosse: EC2 terminata, RDS e DynamoDB eliminati, funzione/Function URL/ruolo Lambda e log eliminati, security group temporaneo eliminato dopo il distacco RDS. È rimasto il solo budget da 20 USD/mese, utile per il progetto.

Un nuovo `terraform plan -detailed-exitcode` ha restituito zero modifiche. Questo confronto copre le risorse AWS gestite da Terraform; le configurazioni cyber applicate via SSM sono riprodotte dall'adattatore separato, non vengono controllate dal plan.

Al termine del collaudo `logall_json` è stato riportato a `no`, come richiesto dal manuale cyber, e il manager è stato verificato attivo. Gli archivi già raccolti rimangono consultabili e gli alert continuano a essere indicizzati. Prima delle prossime prove Red attivare la raccolta grezza per tutta la finestra concordata; il Blue può analizzare successivamente i file già raccolti. Le istruzioni sono nel README.

### Limiti operativi

Il SIEM dispone di 2 vCPU: è inferiore alle 4 vCPU consigliate da Wazuh per la configurazione iniziale. Il bootstrap e il collaudo con due agenti funzionano; non è stata provata la capacità durante attacchi intensivi. Dopo il bootstrap sono stati rilevati circa 5 GiB di RAM disponibili e 30 GiB liberi sul root. Monitorare disco, latenza e code durante le prove.

Nessun nuovo commit o push è stato eseguito per il deploy personale. La baseline della repository non è stata modificata. GitHub Actions e le regole di approvazione dei deploy non sono stati cambiati in questa esecuzione.

### Riepilogo conclusivo

Controlli conclusi il 13 novembre 2026 alle 16:30 (Europe/Rome).

| Controllo | Esito |
|---|---|
| Crediti aggiuntivi | Cinque attività completate, +100 USD; saldo API attuale 200.0 USD, soggetto ad aggiornamento ritardato dei consumi |
| Piano | FREE / ACTIVE, nessun upgrade a pagamento |
| Infrastruttura | 67 risorse Terraform create; ultimo plan senza modifiche |
| EC2 e bootstrap | Tre nodi SSM Online; cloud-init done senza errori |
| Applicazione | https://32.201.245.48, ricerca/registrazione/login verificati |
| Browser | Sei combinazioni Chromium/Firefox/WebKit e viewport desktop/mobile passate dopo l'integrazione cyber |
| Cyber | Regola 10001, stesso ID transazione nel WAF e nel manager; access log correlato ricevuto |
| Wazuh | Quattro servizi centrali attivi, due agenti Active, indexer green e alert effettivamente indicizzati |
| WAF finale | DetectionOnly; blocco 403 e ritorno a 200 collaudati |
| Archivi grezzi | Disabilitati al termine del collaudo; evidenze già raccolte conservate |
| Monitoring | Tredici allarmi OK; metriche, log e Flow Logs presenti; consegna SNS→SQS provata |
| Backup reale WEB | COMPLETED, recovery point COMPLETED, AMI privata ami-0f5fb0f4d69d8cf31 e snapshot EBS cifrato |
| Dashboard | Pagina login 200 tramite SSM, tunnel di verifica poi chiuso |
| Risorse per i crediti | Eliminate; conservato soltanto il budget |
| Git | Solo aggiornamento dai commit del gruppo; nessun nuovo commit/push e baseline invariata |

Il laboratorio è lasciato **acceso** per l'uso richiesto. Il progetto completo locale è questa cartella; seguire `README.md` per accessi, replica e apertura/chiusura della raccolta prima delle prossime prove Red/Blue. Il piano FREE scade il 28 novembre 2026 alle 11:27 circa. Il budget è stato successivamente dotato dello stop automatico descritto al punto 16.

Evidenze principali: `evidence/terraform-apply-retry.txt`, `terraform-final-plan.txt`, `outputs.json`, `cyber-apply.txt`, `cyber-transaction.json`, `browser-results.json`, `waf-test-results.json`, `final-verification.json`, `backup-status.json` e `recovery-point.json`. Gli output SSM di questa esecuzione sono conservati localmente. Lo state e i piani non devono essere pubblicati.

Alla chiusura del deploy iniziale restavano non collaudati il ripristino completo, il carico sotto attacco intenso, i telefoni fisici e il login autenticato nella UI Wazuh. Il successivo punto 17 documenta l’utente Blue Team e il collaudo della UI in lettura.

### 16. Protezione contro il consumo del credito

Su richiesta dell'utente è stato verificato nuovamente lo stato del piano tramite API: FREE / ACTIVE, saldo riportato 200 USD e scadenza 28 novembre 2026 alle 11:27 circa, Europe/Rome. La documentazione AWS conferma che il piano FREE chiude automaticamente l'account a esaurimento credito o a scadenza, senza proseguire come piano a pagamento. Non è stato eseguito alcun upgrade. Le limitazioni cambiano se il titolare passa al piano PAID o compie un'operazione che comporta tale passaggio, come aderire ad AWS Organizations.

È stata aggiunta una protezione anticipata sul budget da 20 USD mensili già esistente. Il budget è stato importato nello state del progetto. Il file `project/cost-protection.tf` aggiunge un ruolo dedicato, una policy di stop limitata alle tre EC2 via SSM, il permesso SNS per Budgets e una Budget Action con approvazione AUTOMATIC, tipo ACTUAL, soglia 100% e operazione STOP_EC2_INSTANCES.

Il piano di modifica è stato controllato anche con assert sul JSON: quattro aggiunte, aggiornamento dei soli tag del budget importato, zero distruzioni e nessuna modifica delle VM o dei loro dati. L'apply è riuscito; un nuovo plan non rileva differenze. Gli ID nell'azione corrispondono esattamente alle tre VM del progetto. La simulazione IAM consente StopInstances sui tre target tramite SSM e lo nega su un target esterno; il runbook AWS-StopEC2Instance è autorizzato. La policy SNS mantiene anche i permessi preesistenti degli allarmi.

L'azione `8b875840-e1ac-4226-9c3b-ed8fec260c7f` è STANDBY e AUTOMATIC. Le tre VM sono ancora running: lo spegnimento non è stato forzato durante la verifica. Le notifiche vanno al topic SNS/coda SQS del lab; nessun messaggio personale è stato inviato. La configurazione e il test di sola lettura sono inclusi nella cartella replicabile, senza nuovo commit/push.

Limiti: il budget misura consumo mensile, non saldo residuo; 20 USD è una soglia di intervento e non un limite istantaneo. Budgets si aggiorna con ritardo, tipicamente ogni 8–12 ore. Lo stop non elimina NAT, dischi, snapshot, log e backup, né governa eventuali VM esterne allo state; un amministratore può riaccendere i nodi. La protezione contro addebiti oltre il credito dipende quindi dal mantenimento del piano FREE. La chiusura automatica dell'account comporta perdita dell'accesso alle risorse e, trascorso il periodo di conservazione previsto da AWS, cancellazione dei dati.

Evidenze: `cost-protection-import.txt`, `cost-protection-plan.txt`, `cost-protection-plan.json`, `cost-protection-apply.txt`, `cost-protection-final-plan.txt` e `cost-protection-verification.json` in `evidence/`. Il README contiene le istruzioni aggiornate.

### 17. Utente Blue Team e ruolo per la difesa sincrona

L'utente ha richiesto l'accesso per un membro Blue Team con nome “blue team”, poi ha esteso lo scenario alle prove sincrone e ha scelto esplicitamente l'amministrazione delle sole VM WAF e SIEM. Il nome tecnico creato è `blue-team`, perché IAM non ammette spazi.

È stata aggiunta la configurazione replicabile `project/blue-team.tf`: utente, gruppo BlueTeamLogs, policy di lettura con bootstrap password/MFA, documento di solo port forwarding sulla 443 del SIEM, ruolo BlueDefence, documento shell per WAF/SIEM e log group di registrazione delle sessioni. Il primo piano aveva dieci aggiunte e nessuna modifica o distruzione delle risorse esistenti; successivamente sono stati allineati due dettagli delle policy per consentire sia il nome di sessione console blue-team sia quello CLI blue-team-live. Il plan finale non rileva drift.

Il login profile AWS è stato creato via API con una password generata, cambio obbligatorio al primo accesso e nessuna access key permanente. Le password non vengono gestite da Terraform per non salvarle nello state. La cartella locale private/ ha ACL limitati all'utente Windows, SYSTEM e amministratori locali. Il file di consegna è private/accessi-blue-team.txt; non è stato pubblicato, inviato a terzi o stampato in chat.

La policy nega l'accesso a log e ruolo operativo senza MFA, anche quando la chiave di contesto MFA è assente. Consente il cambio iniziale della password e l'attivazione del proprio MFA senza già richiedere MFA, evitando di bloccare il primo accesso. Il membro deve registrare personalmente il dispositivo Authenticator, uscire e rientrare prima di usare il laboratorio.

Il profilo normale legge contenuti dei log dei due gruppi del progetto e oggetti Flow Logs nel prefisso concordato. Alcune API di elenco, metriche e stato sono globali per permettere l'uso della console. Non autorizza modifiche alle risorse AWS. L'accesso SSM di base è un tunnel verso il solo SIEM con porta remota fissa 443; la porta e l'host remoto non possono essere cambiati. L'accesso shell predefinito e Run Command sono negati.

Il ruolo `aizoon-personal-BlueDefence` è assumibile dal solo utente blue-team con MFA per massimo un'ora. Consente sessioni Standard_Stream con documento dedicato solo su WAF e SIEM, non sulla VM WEB. Il documento configura timeout di inattività 15 minuti e registrazione CloudWatch. All'interno delle VM l'utente SSM ha sudo: può modificare ModSecurity/CRS, regole Wazuh e servizi. Questa è amministrazione locale e include capacità di modificare file o fermare servizi; non è un profilo in lettura. Il ruolo AWS non concede creazione EC2, gestione IAM/fatturazione, API StopInstances o SendCommand.

L'utente Wazuh blue-team è stato creato nello stack esistente con ruolo indexer custom di lettura e mappatura manager readonly. La password viene generata sul SIEM e restituita soltanto cifrata RSA-OAEP; è decifrata nel processo locale e salvata nel file privato. Le credenziali amministrative dello stack restano sul SIEM e non sono state esportate. Il bootstrap adotta il manager esistente, usa run_as già attivo e non reinstalla i componenti.

Il collaudo ha rilevato la mancanza degli index pattern condivisi, che il lettore non poteva creare. Sono stati inizializzati dall'amministratore via API locale, senza concedere scrittura al profilo di consultazione. È stato usato il ruolo custom di sola lettura previsto dalla documentazione: il ruolo frontend generico kibana_read_only nascondeva l'app Wazuh ed è stato rimosso. Le scritture alle regole del manager effettuate con il contesto readonly sono rifiutate con HTTP 403, mentre la lettura degli agenti è consentita.

Verifiche finali:

- 34 controlli IAM positivi e negativi passati, inclusi MFA falso/assente, letture su risorse consentite, diniego fuori ambito, tunnel fisso, sole due destinazioni amministrative e nessuna access key.
- Cambio password iniziale richiesto e MFA da attivare dal membro; non è stato simulato un dispositivo appartenente al compagno.
- Login Wazuh reale con blue-team: overview caricata, due agenti Active e dashboard Threat Hunting con alert indicizzati. Il totale visualizzato include bootstrap e attività del laboratorio, non un conteggio di attacchi confermati.
- Le preferenze UI in scrittura possono generare notifiche 403 nel profilo readonly: non sono stati concessi permessi aggiuntivi per nasconderle.
- Test browser eseguito tramite un tunnel aperto dall'operatore del deploy, con verifica della password Wazuh blue-team; la fiducia TLS nel browser di test era bypassata e la trust store Windows non è stata modificata.
- Login AWS con MFA e assunzione del ruolo da parte del membro ancora da verificare dopo la sua registrazione MFA. I controlli IAM non sostituiscono questo passaggio.

Istruzioni operative e comandi per il blocco WAF/ritorno alla baseline sono in BLUE_TEAM.md. Le modifiche live sui nodi non vengono automaticamente riportate nel Terraform; prima di una ricreazione occorre conservarle e integrare quelle approvate nei file replicabili. Rimangono attivi budget e protezione del piano FREE. Nessun nuovo commit o push.

Evidenze: blue-team-plan.txt, blue-team-apply.txt, blue-team-console-plan.txt, blue-team-console-apply.txt, blue-team-final-plan.txt, blue-team-iam-verification.json, blue-team-wazuh-verification.json, blue-team-browser-verification.json e screenshot della dashboard in evidence/.

## Note operative

Il laboratorio contiene intenzionalmente un'applicazione vulnerabile. La web app deve essere pubblica attraverso il WAF, mentre web e SIEM devono restare privati. Non inserire dati personali o credenziali reali in Juice Shop.

VM, NAT, IPv4, dischi, log e backup consumano il credito. Spegnere le sole EC2 non elimina gli altri costi. La scadenza Free rilevata è il 28 novembre 2026: questo report non autorizza né esegue un passaggio automatico al piano a pagamento.

## Riferimenti

- [Attività AWS per i crediti aggiuntivi](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans-activities.html)
- [API dello stato del piano](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_freetier_GetAccountPlanState.html)
- [Sorgente Gouthier utilizzato](https://github.com/riccardogouthier-all/AWSZeroTrust-Aizoon/tree/3b5066c/AWS%20ACA/Gouthier/tentativo%202)
