# Laboratorio AWS v3

Versione del laboratorio distribuito nell'account personale il **13 novembre 2026**, a partire da Gouthier `tentativo 2` e dalle configurazioni Blue Team Finocchielli. Comprende infrastruttura, bootstrap, integrazione cyber, protezione dei costi e accessi Blue Team.

**Guida breve per gli accessi AWS e Wazuh:** [Defence / ACCESSO_BLUE_TEAM_v3.md](../../../Cyber%20CYS/Defence/ACCESSO_BLUE_TEAM_v3.md). Le credenziali vengono consegnate privatamente dal titolare: non sono nel repository.

## Architettura

| Componente | Configurazione distribuita |
|---|---|
| Rete | us-east-1, VPC 10.20.0.0/16, subnet pubblica e privata, IGW, NAT e endpoint S3 |
| WAF | t3.small, 20 GiB, IP privato 10.20.1.10, EIP, HTTPS pubblico, nginx + ModSecurity/CRS |
| WEB | t3.small, 20 GiB, 10.20.2.10, Juice Shop:3000, senza IP pubblico |
| SIEM | m7i-flex.large, 8 GiB RAM / 2 vCPU, 50 GiB, 10.20.2.11, Wazuh 4.14.10, senza IP pubblico |
| Gestione | SSM, nessuna porta SSH aperta, ruoli IAM dedicati, dischi cifrati e IMDSv2 |
| Monitoraggio | Tredici allarmi, metriche memoria/disco/HTTPS, log di sistema CloudWatch, Flow Logs S3, SNS → SQS |
| Backup | AWS Backup giornaliero delle tre VM, conservazione un giorno |
| Costi | Budget mensile 20 USD, stop automatico delle tre EC2 al 100% del consumo rilevato |
| Blue Team | Utente blue-team con MFA, lettura log e Wazuh, ruolo separato per amministrazione WAF/SIEM |

Il WAF è lasciato in **DetectionOnly**. L'applicazione è intenzionalmente vulnerabile e non deve contenere dati o credenziali reali. Il certificato HTTPS usa una CA privata; non è automaticamente riconosciuto dai browser.

## File

- `project/`: Terraform, lock provider e script cloud-init.
- `cyber/`: snapshot minimo dei file cyber effettivamente utilizzati, con provenienza.
- `apply_cyber.py`: applica le configurazioni cyber ai nodi esistenti via SSM; non reinstalla Wazuh.
- `lab.py`: esportazione output/CA e inizializzazione privata dei login Blue Team.
- `provision_wazuh_blue.py`: bootstrap dell'utente Wazuh, eseguito sul SIEM con consegna della password cifrata RSA.
- `verify_aws.py`, `verify_blue_access.py`, `verify_cost_protection.py`: controlli AWS; il primo crea un utente QA, simula un allarme e avvia un backup se non già registrato localmente.
- `browser_tests.py`, `waf_tests.py`, `test_blue_dashboard.py`: collaudi sui servizi reali.
- `test_tools.py`, `test_cyber_adapter.py`, `cyber/tests/`: controlli offline con AWS simulato o fixture locali.
- `docs/`: diario del deploy, difesa live e risultati selezionati del 13 novembre.

`private/`, `evidence/`, credenziali, CA generate, state, piani e cache sono esclusi da Git. `docs/evidenze/` contiene soltanto risultati selezionati: non è la cartella di esecuzione degli strumenti.

## Replica su un account nuovo

Serve un account che consenta IAM, EC2, SSM, S3, CloudWatch, SNS/SQS, Budgets e Backup. Questa variante crea i propri ruoli: non è destinata ai permessi ridotti del Learner Lab. Occorrono Terraform 1.13.5 o compatibile con `versions.tf`, AWS CLI, Python **3.12+** e il plugin Session Manager. Per inizializzare i login serve OpenSSL locale oppure quello di Ubuntu su WSL; il SIEM installa già la libreria crittografica richiesta.

Non applicare questa copia con uno state vuoto nell'account già distribuito: nomi IAM, budget e bucket esistono già. Per gestire quel deploy usare lo state privato originale o pianificare un'importazione. Il clone Git non contiene lo state del titolare e non dimostra che un nuovo account sia stato collaudato.

Da PowerShell, nella cartella `AWS ACA/Agosta/v3`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install

# Seleziona il tuo profilo AWS privato, già configurato.
aws sts get-caller-identity
Copy-Item project/terraform.tfvars.json.example project/terraform.tfvars.json
```

Controllare la configurazione copiata: regione, prefisso progetto, nomi dei ruoli e CIDR del WAF. `0.0.0.0/0` espone intenzionalmente il solo ingresso HTTPS. I nomi `blue-team` e `BlueTeamLogs` sono globali nell'account: è prevista una sola installazione di questo laboratorio per account.

```powershell
terraform -chdir=project init
terraform -chdir=project fmt -check
terraform -chdir=project validate
terraform -chdir=project plan -out=deploy.tfplan
# Esaminare il piano e far approvare il deploy al referente del gruppo.
terraform -chdir=project apply deploy.tfplan
python lab.py outputs
```

L'approvazione qui è un passaggio operativo: questo pacchetto non configura un workflow GitHub Actions o un'approvazione automatica. Il file di piano va conservato localmente e non pubblicato.

Attendere tre nodi SSM Online e `cloud-init status --long` con stato `done`. Un apply riuscito non prova il completamento dei servizi. Su Wazuh il bootstrap ha impiegato diversi minuti; i log privati dell'installer sono in `/opt/aizoon/wazuh-install-private.log` e possono contenere segreti: non copiarli nel report.

```powershell
python ops.py nodes
python lab.py ca
python apply_cyber.py
```

L'adattatore mantiene CA, container esistente e identità degli agenti. Aggiunge regola 10001, audit seriale JSON AHZ, sorgenti WAF/WEB, rotazione e blocco degli upgrade isolati. Non usa l'inventario Ansible di esempio del contributo cyber. Le subnet e gli IP privati sono fissi nel Terraform; modificarli richiede allineare anche l'adattatore.

L'installer Wazuh usa l'URL della serie 4.14, che può cambiare nel tempo. Il contributo cyber controlla la patch **4.14.10**: prima di una futura installazione verificare la versione scaricata e concordare l'aggiornamento delle verifiche, senza ignorare un errore di compatibilità. Le immagini Docker sono invece fissate a digest e il provider AWS è nel lockfile.

## Login Blue Team e collaudo

Da operatore amministrativo, dopo il completamento del bootstrap:

```powershell
python lab.py blue-init
python verify_blue_access.py
python verify_cost_protection.py
python verify_aws.py
python browser_tests.py
python waf_tests.py
```

`blue-init` crea il login console con cambio password richiesto e l'utente Wazuh readonly. Genera una chiave RSA locale e restituisce la password Wazuh soltanto cifrata; i segreti sono in `private/blue-team-credentials.json`, non nello state o nell'output del comando. Su Windows restringe gli ACL a proprietario, SYSTEM e amministratori; su Linux usa una directory privata. Non sostituisce password esistenti: se il login esiste ma mancano i file privati originali si ferma. Il membro Blue Team deve registrare il proprio MFA e rientrare prima di leggere o assumere il ruolo operativo.

La verifica IAM simula i permessi: non sostituisce il primo accesso reale del membro con MFA. `test_blue_dashboard.py` verifica la UI Wazuh, legge la password dal file privato e richiede un tunnel già aperto sulla porta locale **8445**. Per la normale consultazione il collega usa la porta 8443 della guida breve.

La sonda cyber e il verificatore confrontano lo stesso ID di transazione tra WAF e manager. L'adattatore abilita gli archivi grezzi per la finestra di verifica; al termine disabilitarli come descritto in [Difesa live](docs/DIFESA_LIVE.md). Gli archivi già raccolti restano disponibili per l'analisi asincrona.

`waf_tests.py` prova il passaggio a On e ripristina DetectionOnly. `verify_aws.py` ha effetti controllati sul laboratorio: account QA sintetico, transizione dell'allarme CPU e backup del WEB. Non eseguirlo come semplice controllo offline. Prima di ripeterlo leggere i suoi effetti e controllare account e output. Gli strumenti SSM verificano che il profilo coincida con l'account esportato dallo state.

## Prove offline

```powershell
python -m unittest test_tools -v
python test_cyber_adapter.py
python -m unittest discover -s cyber/tests -v
```

Non eseguono deploy AWS. Il test cyber HTTP usa un server loopback temporaneo. La sintassi shell va controllata con `bash -n`, per esempio in Ubuntu/WSL.

## Costi e limiti

Lo stop a 20 USD/mese misura il consumo **prima dei crediti** e si applica alle tre EC2 nello state. Budgets è ritardato: non è un tetto istantaneo, non impedisce a un amministratore di riaccendere una VM e non elimina NAT, IPv4, dischi, log o backup.

Nel deploy verificato il piano era **FREE**, con 200 USD riportati dalle API dopo le attività promozionali. Il piano scadeva il **28 novembre 2026 alle 11:27 circa, Europe/Rome**: questi sono dati storici dell'account, non benefici assegnati a chi clona il repository. Il piano FREE chiude l'account a esaurimento credito o a scadenza; la protezione non vale passando a PAID, anche tramite adesione a Organizations. Non viene creato alcun account Organizations.

La m7i-flex.large era ammessa dal piano, mentre t3.xlarge era stata rifiutata nonostante il DryRun. Verificare i tipi consentiti con `free-tier-eligible=true`: ammesso non significa gratuito. Il SIEM ha 2 vCPU, meno delle 4 consigliate da Wazuh; è stato collaudato con due agenti, senza prova sotto attacco intenso.

Per dismettere, esaminare `terraform -chdir=project plan -destroy` sullo state corretto. Il vault Backup non è forzatamente cancellabile con recovery point presenti. Il bucket log ha `force_destroy=true`: applicare la distruzione cancella gli oggetti. Non usare la dismissione come semplice spegnimento delle lezioni.

## Provenienza e stato delle verifiche

Terraform di base: Gouthier `3b5066c`. Contributo cyber: Finocchielli, letto al commit `169a747`. La v3 aggiunge ruoli per l'account personale, SIEM compatibile con il piano, budget con azione automatica e profili Blue Team. In fase di pubblicazione sono stati aggiunti output account/regione/progetto e helper per la replica, corretti i valori di default e resi dinamici i riferimenti dei controlli.

[Report passo passo](docs/report_deploy_2026-11-13.md) · [Evidenze selezionate](docs/evidenze/validazione.json) · [Difesa live](docs/DIFESA_LIVE.md)

Il deploy storico ha superato test browser su tre motori e due viewport, prova WAF 200/403/ripristino, correlazione Wazuh, backup reale e verifiche IAM. **Non è stato eseguito un nuovo deploy completo della cartella Git v3**. Non sono collaudati il ripristino completo, il carico intenso, telefoni fisici e il login AWS del compagno dopo l'attivazione del suo MFA.
