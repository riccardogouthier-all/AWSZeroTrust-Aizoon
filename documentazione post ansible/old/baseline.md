# Piano tecnico del laboratorio AWS Cloud Security e DevSecOps

## Obiettivo e contesto

Realizzare un laboratorio condiviso su AWS nel quale costruire, attaccare e difendere una web application vulnerabile. Il progetto deve permettere di dimostrare l'intero ciclo: deploy, attacco, rilevamento, difesa e recupero, con configurazioni ripetibili ed evidenze documentate.

Il gruppo è composto da otto partecipanti: quattro per la parte AWS, due per il red team e due per il blue team. Tutti lavorano sullo stesso account e sullo stesso ambiente. La preparazione può avvenire da scuola e da casa; le esercitazioni di attacco vengono svolte da scuola.

L'ambiente iniziale sarà un AWS Learner Lab. In seguito potrebbe essere disponibile un account AWS ordinario. Il laboratorio deve funzionare durante le lezioni; non è richiesta continuità del servizio fuori da questi periodi e la perdita dei dati applicativi è accettabile.

La sequenza delle esercitazioni è asincrona: il red team esegue gli attacchi, il blue team analizza le evidenze e applica le difese, quindi il red team ripete gli stessi scenari.

Le tecnologie confermate sono Terraform, Ansible, Checkov, Docker, OWASP Juice Shop, ModSecurity con OWASP Core Rule Set e Wazuh. La CI/CD utilizzerà GitHub Actions e ogni deploy dovrà essere sottoposto ad approvazione.

L'approvazione sarà affidata a un membro del gruppo. L'applicazione sarà raggiunta usando direttamente l'IP pubblico del WAF, senza dominio.

Questo documento unisce il piano generale del gruppo e la proposta infrastrutturale di Gouthier, letta al commit `16db047ddae130de58e9e8cd2bc5375074fdb01e`. Integra rete, compute, accesso SSM e configurazione Ansible con CI/CD obbligatoria, monitoring, recupero, QA e ciclo red/blue team.

Definisce il lavoro da realizzare; non attesta l'esistenza di un ambiente già funzionante e non assume come approvate o collaudate le implementazioni Terraform già presenti nella repository. I dettagli infrastrutturali proposti dovranno essere verificati nel Learner Lab prima del deploy.

## 1. Verifica del Learner Lab

Prima di fissare l'implementazione occorre verificare:

- Permessi disponibili per EC2, rete, IAM, Systems Manager, monitoring e backup.
- Ruoli già forniti dal laboratorio e possibilità di utilizzarli con Terraform.
- Budget, quote e comportamento delle risorse alla chiusura delle sessioni.
- Possibilità di collegare GitHub Actions ad AWS.
- Disponibilità delle protezioni GitHub necessarie a imporre l'approvazione del deploy.
- Modalità di accesso individuale all'account condiviso, senza condivisione di credenziali personali.

Regione, dimensionamento e ruoli utilizzati saranno parametri del progetto, per agevolare un eventuale passaggio a un account ordinario.

**Risultato atteso:** elenco dei servizi utilizzabili, dei vincoli e delle scelte compatibili con l'account assegnato.

## 2. Infrastruttura e hosting

Terraform creerà una VPC, le subnet e tre EC2 Ubuntu.

| Componente | Software | Funzione |
| --- | --- | --- |
| Web application | Docker e OWASP Juice Shop | Bersaglio degli attacchi |
| Reverse proxy e WAF | ModSecurity e OWASP Core Rule Set | Accesso alla web app, registrazione e blocco delle richieste |
| SIEM | Wazuh | Raccolta log, analisi e rilevamento |

### Parametri infrastrutturali proposti

La proposta iniziale adotta `eu-west-1`, una sola Availability Zone e gli indirizzi seguenti, tutti configurabili e subordinati ai vincoli dell'account e all'assenza di sovrapposizioni con eventuali reti collegate:

| Elemento | Proposta |
| --- | --- |
| VPC | `10.20.0.0/16` |
| Subnet pubblica | `10.20.1.0/24`, WAF e NAT Gateway |
| Subnet privata | `10.20.2.0/24`, web app e SIEM |
| Instradamento pubblico | Internet Gateway |
| Uscita dalla subnet privata | Un NAT Gateway, da confermare rispetto a permessi e costi |
| WAF | EC2 `t3.small`, EBS gp3 cifrato da 20 GiB, Elastic IP |
| Web app | EC2 `t3.small`, EBS gp3 cifrato da 20 GiB |
| SIEM | Wazuh all-in-one, riferimento iniziale di 4 vCPU, 8 GiB RAM e 50 GB di storage |

Il tipo EC2 del SIEM sarà scelto tra quelli consentiti dal laboratorio. La `t3.large` indicata nella proposta di Gouthier ha 2 vCPU e 8 GiB di RAM: non soddisfa il riferimento raccomandato di 4 vCPU del quickstart Wazuh. Un eventuale utilizzo ridotto dovrà essere motivato e verificato sotto il carico delle esercitazioni, senza presentarlo come conforme al dimensionamento raccomandato.

L'AMI sarà ufficiale Canonical Ubuntu 24.04 LTS, con identificativo e versioni effettivamente usati registrati per ogni esercitazione. Saranno richiesti IMDSv2 e tag `Project`, `Environment` e `Role`.

### Flussi di rete e accesso

Il percorso ordinario delle richieste sarà: utenti e tester autorizzati, reverse proxy/WAF, Juice Shop. Web app e SIEM saranno collocati in subnet privata, senza accesso pubblico diretto.

I Security Group consentiranno soltanto i flussi necessari. L'amministrazione utilizzerà Systems Manager Session Manager se disponibile, verificando agent, ruoli e connettività richiesti. L'accesso amministrativo alla dashboard Wazuh sarà riservato agli utenti autorizzati.

La modalità di collegamento del team cyber sarà concordata con il gruppo quando l'infrastruttura sarà disponibile. Non si assume già l'utilizzo di una VPN o di una macchina di attacco interna ad AWS. Eventuali accessi aggiuntivi saranno espliciti, limitati allo scenario e rimossi al termine delle prove.

Saranno inoltre previsti:

- Volumi EBS cifrati e permessi IAM minimi compatibili con il laboratorio.
- Accesso HTTPS al reverse proxy tramite `https://<IP-pubblico-WAF>`, senza dominio. Si propone un certificato di laboratorio con l'IP effettivo nel Subject Alternative Name (SAN), da rendere attendibile sui browser e dispositivi di test con una procedura documentata. La verifica TLS non sarà disabilitata negli smoke test. Se l'IP cambia dopo una ricreazione, certificato e configurazioni dei client dovranno essere aggiornati.
- Connettività in uscita per aggiornamenti, immagini Docker e servizi AWS, scelta in base a costi e vincoli.
- Una sola Availability Zone come proposta iniziale per il laboratorio didattico.
- Tag comuni per identificare risorse, ambiente e componenti.

| Origine | Destinazione | Flusso previsto |
| --- | --- | --- |
| Indirizzi autorizzati di utenti e tester | WAF | TCP 443 |
| WAF | Web app | TCP 3000 |
| Web app e WAF | Wazuh | TCP 1514 per eventi e TCP 1515 per enrollment |
| Istanze | Repository software e servizi necessari | Uscita HTTP/HTTPS secondo le necessità verificate |
| Amministratori autorizzati | Istanze e dashboard Wazuh | Sessioni e port forwarding SSM |

Le comunicazioni tra componenti saranno autorizzate tramite riferimenti ai Security Group. Il gruppo di sicurezza predefinito della VPC sarà svuotato e non utilizzato. Non saranno aperte porte SSH e l'accesso HTTPS non sarà consentito indiscriminatamente a Internet. La lista CIDR dovrà includere gli indirizzi pubblici effettivamente usati a scuola e da casa, aggiornandoli quando necessario.

Un endpoint gateway S3 permetterà alle istanze di raggiungere il bucket di scambio Ansible senza attraversare il NAT. Questo endpoint non sostituisce la connettività necessaria per Systems Manager, aggiornamenti e immagini Docker.

**Risultato atteso:** infrastruttura raggiungibile dai soggetti autorizzati, con flussi di rete documentati e componenti interni isolati.

## 3. Configurazione automatica

Terraform gestirà le risorse AWS; Ansible installerà e configurerà software e servizi.

Le attività comprenderanno:

- Fissare le versioni di immagini e componenti per rendere ripetibili le prove.
- Configurare Docker e Juice Shop.
- Configurare reverse proxy, TLS, ModSecurity e CRS.
- Installare Wazuh e gli agent necessari alla raccolta dei log.
- Usare un inventario dinamico Ansible EC2 filtrato sia per progetto e ambiente sia per tag `Role`, evitando di includere macchine estranee al laboratorio.
- Predisporre uno state Terraform condiviso in S3, cifrato, privato e con versioning e locking, prima dell'uso collaborativo. La creazione iniziale del backend avrà una procedura dedicata e il suo ciclo di vita sarà separato dall'ambiente da distruggere.
- Gestire credenziali e segreti fuori dal repository.
- Documentare ricreazione e azzeramento del laboratorio.

La connessione Ansible utilizzerà il plugin SSM della collection scelta e fissata nel progetto, con un bucket S3 privato dedicato allo scambio dei file. Il bucket avrà Block Public Access, cifratura, accesso solo TLS e pulizia dei file temporanei. Non sarà utilizzato come archivio dello state o delle evidenze.

Saranno definiti separatamente i permessi delle EC2 e quelli del controller Ansible, locale o in GitHub Actions. Quest'ultimo deve poter avviare le sessioni necessarie e caricare, scaricare ed eliminare i file di scambio S3. Non si presume che assegnare permessi alle sole EC2 sia sufficiente.

L'ordine di configurazione sarà:

1. Configurazione comune, aggiornamenti e sincronizzazione degli orologi.
2. Wazuh server, indexer e dashboard sulla VM SIEM.
3. Docker e Juice Shop sulla VM web, con riavvio automatico del servizio.
4. nginx, ModSecurity v3, CRS e TLS sulla VM WAF, con upstream verso la web app e modalità iniziale `DetectionOnly`.
5. Agent Wazuh su web e WAF e raccolta dei log previsti.

I playbook dovranno essere idempotenti. I segreti, comprese le credenziali Wazuh, saranno conservati con un meccanismo protetto, per esempio Ansible Vault, gestendo separatamente anche la chiave di sblocco.

I dati applicativi saranno sacrificabili. Codice, configurazioni, procedure ed evidenze dovranno invece essere conservati nel repository o nello spazio concordato per i report, escludendo segreti e dati sensibili.

**Risultato atteso:** ambiente configurabile in modo ripetibile senza passaggi manuali non documentati.

## 4. Pipeline CI/CD

GitHub Actions eseguirà questa sequenza:

1. Controllo della formattazione e validazione Terraform.
2. Scansione Checkov e controlli applicabili alla configurazione Ansible.
3. Generazione del piano Terraform.
4. Revisione e approvazione del deploy.
5. Applicazione del piano approvato e configurazione Ansible.
6. Smoke test dell'applicazione.

Prima del deploy dovranno risultare superati i controlli previsti. Le eccezioni alle segnalazioni di sicurezza dovranno essere motivate e documentate, distinguendo le vulnerabilità intenzionali del laboratorio dalle configurazioni infrastrutturali non desiderate.

La scansione IaC sarà eseguita prima del primo deploy e nella CI. I report saranno conservati come evidenze; una singola AZ, la scelta della cifratura e l'assenza di KMS personalizzato non saranno motivi automatici per ignorare qualsiasi finding. Ogni eccezione avrà identificativo, motivazione e perimetro espliciti.

L'autenticazione ad AWS dipenderà dai permessi disponibili: OIDC se consentito; altrimenti una procedura compatibile con le credenziali temporanee del Learner Lab. Il meccanismo di approvazione sarà verificato rispetto alle funzionalità disponibili nel repository GitHub.

Con OIDC la trust sarà limitata al repository e al contesto di deploy autorizzati. Le credenziali permanenti non saranno inserite nel codice. Se i vincoli del laboratorio o di GitHub impediscono il percorso previsto, sarà concordata una procedura alternativa che mantenga l'approvazione: la CI/CD è parte del progetto, non un'estensione opzionale. Un membro del gruppo approverà i deploy; il suo account GitHub dovrà essere indicato per configurare il controllo.

L'esecuzione concorrente di deploy sullo stesso ambiente sarà impedita. Configurazioni e versioni saranno congelate prima delle esercitazioni, così da rendere confrontabili i risultati.

**Risultato atteso:** deploy tracciabile, ripetibile e subordinato ad approvazione.

## 5. Monitoring e backup

### Monitoring infrastrutturale

Il monitoring controllerà stato delle VM, utilizzo delle risorse e raggiungibilità dell'applicazione. Saranno definiti allarmi e un destinatario delle notifiche.

Memoria e spazio disco richiederanno un agent: non sono coperti dalle sole metriche EC2 standard. Saranno valutati i log delle connessioni di rete e gli eventi di gestione AWS in funzione dei permessi, dei costi e degli scenari.

La proposta prevede VPC Flow Logs su CloudWatch Logs con conservazione configurabile, metriche e allarmi CloudWatch per lo stato delle VM e CPU, e una verifica HTTPS del servizio. Soglie, controllo di memoria/disco, canale delle notifiche e relativi permessi saranno definiti durante la configurazione. I Flow Logs non sostituiscono i log HTTP e di sicurezza e non contengono il contenuto delle richieste applicative.

### Rilevamento di sicurezza

Wazuh raccoglierà i log necessari alle esercitazioni, compresi quelli di sistema, del reverse proxy e del WAF. Prima degli attacchi sarà verificato che gli eventi arrivino al SIEM con orari coerenti e informazioni sufficienti per correlare richieste e risultati.

### Backup e recupero

Non è richiesta conservazione dei dati applicativi. Il backup avrà soprattutto uno scopo dimostrativo:

1. Creare un punto di ripristino delle risorse selezionate.
2. Ripristinare una macchina o un volume in un contesto isolato.
3. Verificare avvio dei servizi e funzionamento dell'applicazione.
4. Documentare la procedura e rimuovere le copie non necessarie.

Il servizio utilizzato, la frequenza e la conservazione saranno scelti dopo la verifica del Learner Lab. La ricreazione tramite Terraform e Ansible sarà il metodo principale di recupero della configurazione.

Se consentito, sarà utilizzato AWS Backup; in alternativa sarà valutata una prova tramite snapshot EBS. Le evidenze descriveranno il perimetro effettivamente recuperato e la consistenza applicativa verificata. Lo state Terraform, le chiavi necessarie alla configurazione e i report non dovranno essere eliminati insieme alle VM.

**Risultato atteso:** guasti e attività rilevanti osservabili, con almeno una prova documentata di ripristino.

## 6. Esercitazioni red e blue team

Prima delle esercitazioni saranno concordati bersagli, accessi, strumenti, finestre operative e scenari autorizzati, nel rispetto della policy AWS applicabile.

| Passaggio | Attività | Evidenze |
| --- | --- | --- |
| Baseline | Ambiente funzionante, log attivi e WAF in modalità rilevamento | Controlli iniziali e configurazione utilizzata |
| Primo attacco | Il red team esegue gli scenari concordati, incluso l'obiettivo di login admin su Juice Shop | Richieste, risultati e orari |
| Analisi | Il blue team esamina log ed eventi | Ricostruzione degli attacchi e limiti di visibilità |
| Difesa | Il blue team configura blocchi CRS e regole Wazuh | Configurazioni, blocchi e allarmi |
| Ripetizione | Il red team ripete gli stessi scenari | Confronto dei risultati prima e dopo le difese |

Il traffico ordinario dovrà continuare a funzionare dopo l'attivazione delle difese. Eventuali falsi positivi saranno registrati e corretti. Se uno scenario richiede un reset, sarà ripristinata una condizione iniziale documentata.

**Risultato atteso:** evidenze confrontabili di attacco, rilevamento e mitigazione, con indicazione degli scenari riusciti e di quelli non coperti.

## 7. Verifica funzionale e compatibilità browser

Non sono richieste ulteriori suite obbligatorie. Sarà preparata una checklist essenziale per verificare:

- Apertura dell'applicazione e navigazione.
- Ricerca dei prodotti.
- Registrazione e login ordinario.
- Funzionamento delle operazioni previste dopo l'attivazione del WAF.
- Funzionamento dopo deploy, riavvio e ripristino.

Il perimetro proposto comprende Chrome, Edge, Firefox e Safari nelle versioni recenti, con una verifica del layout e delle interazioni su mobile. Browser, versioni e dispositivi effettivamente provati saranno riportati nelle evidenze; l'obiettivo generico di compatibilità con tutti i browser non equivale a una verifica universale.

Gli automatismi saranno limitati agli smoke test utili. Le vulnerabilità intenzionali di Juice Shop saranno trattate come scenari del laboratorio; i malfunzionamenti introdotti dall'infrastruttura o dalle difese saranno registrati come difetti.

**Risultato atteso:** checklist compilata e problemi riproducibili documentati.

## 8. Gestione delle lezioni e dei costi

Sarà definita una procedura di apertura della sessione, controllo dell'ambiente e chiusura delle risorse. Prima di eventuali azzeramenti saranno esportate le evidenze delle esercitazioni.

La dismissione con `terraform destroy` è la proposta per evitare costi residui, subordinata alla ricostruzione automatica e al tempo necessario per reinstallare i componenti a ogni lezione. Prima della distruzione occorrerà verificare l'esportazione delle evidenze e lo state aggiornato, senza eliminare il backend. Al termine saranno controllati NAT Gateway, Elastic IP, volumi, snapshot, bucket e log residui. I tempi di ricostruzione saranno misurati nella prima prova completa.

L'analisi economica comprenderà EC2, EBS, indirizzi IPv4 pubblici, connettività in uscita, eventuale NAT o endpoint, monitoring, log e backup. Le stime saranno calcolate dopo avere conosciuto regione, dimensionamento, budget e ore di utilizzo.

Le cifre mensili nella proposta di Gouthier sono indicative e non vengono adottate come preventivo. La stima distinguerà utilizzo continuativo e sole lezioni, includendo installazioni ripetute e trasferimenti. AWS Budgets con notifiche sarà aggiunto se consentito, senza presumere che gli avvisi arrestino automaticamente le risorse o impediscano il superamento della soglia.

Fermare le EC2 non elimina tutti i costi: dischi, backup ed eventuali risorse di rete possono continuare a generarli. La procedura di chiusura dovrà quindi distinguere arresto delle VM e dismissione dell'ambiente.

**Risultato atteso:** uso limitato alle necessità del laboratorio e risorse residue identificate.

## 9. Consegne e criteri di completamento

La consegna comprenderà:

- Repository con Terraform, Ansible, pipeline e configurazioni.
- Schema architetturale e matrice dei flussi di rete.
- Istruzioni per deploy, accesso, reset, ripristino e dismissione.
- Report Checkov ed eventuali eccezioni motivate.
- Checklist funzionale e browser con risultati.
- Report red team con evidenze degli scenari eseguiti.
- Report blue team con configurazioni, log, blocchi e rilevamenti.
- Prova di ripristino documentata.
- Analisi dei costi e demo finale.

Il laboratorio sarà completato quando sarà possibile ricrearlo, usarlo, eseguire gli scenari concordati, osservare gli eventi, applicare le difese e dimostrare il recupero, conservando evidenze ripetibili.

### Verifica prima della consegna al team cyber

- Terraform termina senza errori e un secondo piano, a configurazione invariata, non propone modifiche inattese.
- Le tre EC2 sono gestibili tramite Systems Manager.
- Juice Shop risponde tramite HTTPS passando dal WAF; la porta applicativa non è esposta pubblicamente.
- Un'origine non autorizzata non raggiunge l'ingresso HTTPS e nessuna VM espone SSH.
- La dashboard Wazuh è accessibile tramite il percorso amministrativo concordato e mostra i due agent attivi.
- I log nginx e ModSecurity arrivano al SIEM; il WAF è in `DetectionOnly` per la prima esercitazione.
- I Flow Logs sono presenti e il percorso di notifica infrastrutturale è stato provato.
- L'esito Checkov e le eventuali eccezioni sono archiviati.
- Deploy approvato, smoke test e procedura di ricostruzione sono stati verificati.

Questa verifica conclude la fase infrastrutturale. Le fasi red/blue team, QA dopo le difese e prova di recupero rimangono necessarie per completare il progetto complessivo.

## Decisioni ancora aperte

- Permessi, quote e servizi effettivamente disponibili nel Learner Lab.
- Conferma di regione, indirizzamento, dimensionamento SIEM, budget e connettività proposti.
- Modalità concreta di accesso del team cyber alla rete.
- Procedura di emissione e distribuzione del certificato di laboratorio per l'IP del WAF e verifica sui dispositivi disponibili.
- Autenticazione AWS, disponibilità delle protezioni GitHub e account GitHub del membro del gruppo incaricato di approvare i deploy.
- Destinatario delle notifiche e conservazione di log e backup.
- Browser e dispositivi disponibili per le verifiche.

Questi punti richiedono una verifica dell'ambiente o un accordo tra i gruppi; non costituiscono configurazioni già approvate o collaudate.

## Riferimenti

- [Proposta originale del laboratorio](https://github.com/riccardogouthier-all/AWSZeroTrust-Aizoon/blob/main/Proposta%20Laboratorio%20Integrato_Ottobre%202026_aizoOn.docx)
- [Proposta infrastrutturale di Gouthier esaminata](https://github.com/riccardogouthier-all/AWSZeroTrust-Aizoon/blob/16db047ddae130de58e9e8cd2bc5375074fdb01e/AWS%20ACA/Gouthier/soluzione_aws.md)
- [Requisiti del quickstart Wazuh](https://documentation.wazuh.com/current/quickstart.html)
- [Specifiche delle istanze EC2 T3](https://aws.amazon.com/ec2/instance-types/t3/)
- [Connessione Ansible tramite Systems Manager](https://docs.ansible.com/projects/ansible/latest/collections/amazon/aws/aws_ssm_connection.html)
- [Prerequisiti AWS Systems Manager Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-prerequisites.html)
- [Backend S3 di Terraform](https://developer.hashicorp.com/terraform/language/backend/s3)
- [OIDC tra GitHub Actions e AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)
- [Test di ripristino AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/restore-testing.html)
- [Policy AWS sui penetration test](https://aws.amazon.com/security/penetration-testing/)
