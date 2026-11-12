# Laboratorio AWS versione 2.0

Pacchetto completo per ricreare il laboratorio con tre EC2 Ubuntu: Juice Shop, WAF nginx con ModSecurity e OWASP CRS, Wazuh all-in-one. Include monitoring CloudWatch, notifiche SNS verso SQS, VPC Flow Logs, AWS Backup, configurazione Ansible tramite SSM e test.

La web app è pubblica tramite HTTPS sull'IP del WAF. Web e SIEM rimangono privati. Il WAF parte in `DetectionOnly` per la prima esercitazione red team; lo script di prova verifica anche il blocco e ripristina la baseline.

## Contenuto e verifiche disponibili

| Percorso | Contenuto |
| --- | --- |
| `terraform/` | Infrastruttura, provider lock e test Terraform con mock AWS |
| `configuration/` | Playbook Ansible eseguiti sulle EC2 tramite SSM |
| `bootstrap.py` | Crea e protegge i bucket state e log senza chiamare la lettura Object Lock vietata dal Lab |
| `export_outputs.py` | Esporta gli output della nuova esecuzione |
| `configure_all.py` | Attende SSM, configura i tre host e gli agent, esporta la CA pubblica |
| `browser_tests.py`, `waf_tests.py` | Test browser e prova controllata del WAF |
| `backup_test.py` | Backup web, avvio da AMI in VM isolata, verifica applicazione e pulizia temporanei |
| `Open-WazuhTunnel.ps1` | Port forwarding locale alla dashboard, per Windows |
| `images.lock.json` | Digest delle immagini Docker risolti dal registro durante il confezionamento |
| `tests/` | Test Python senza chiamate AWS reali |
| `docs/` | Proposta e report storico sanitizzato della prova, con evidenze selezionate |

La prova reale del 12 novembre 2026 è descritta nel [report storico](docs/report_learner_lab.md). Il pacchetto aggiunge bootstrap e orchestrazione portabili rispetto agli script usati in quella prova: questi adattamenti sono verificati offline, senza un ulteriore deploy completo. I digest Docker sono stati risolti durante il confezionamento, non recuperati dai container della prova storica.

AMI Ubuntu, pacchetti di sistema, CloudWatch agent e patch della serie Wazuh 4.14 vengono risolti al momento dell'installazione. Conservare gli output e le versioni di ogni nuova esecuzione per ricostruirne esattamente il contesto.

## 1. Prerequisiti

- Account Learner Lab attivo e credenziali temporanee complete, incluso il session token.
- `LabInstanceProfile` e `LabRole`, oppure ruoli già esistenti compatibili indicati nelle variabili. Il codice non crea né modifica ruoli IAM.
- Permessi per EC2/VPC, S3, SSM, CloudWatch Logs e metriche, SNS, SQS, AWS Backup e passaggio dei ruoli utilizzati.
- Quote per tre istanze e per una quarta t3.small temporanea durante il test di recupero.
- Terraform almeno 1.9; nella prova è stato usato 1.13.5. Provider AWS bloccato alla versione del lock file.
- Python almeno 3.12, AWS CLI v2. Ansible verrà installato sulle VM Ubuntu: non occorre installarlo sul controller Windows.
- Per il tunnel, [plugin ufficiale AWS Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html) nel PATH.

Le sezioni seguenti usano PowerShell e partono da questa cartella. Su Linux/macOS attivare la venv e usare `python` al posto dell'eseguibile Windows.

```powershell
py -m venv .venv
$python = "$PWD\.venv\Scripts\python.exe"
& $python -m pip install -r requirements.txt
$env:AWS_PROFILE = 'learner-lab'
aws sts get-caller-identity
```

Configurare prima il profilo `learner-lab` con le credenziali correnti del laboratorio nel file utente AWS o tramite la normale catena di autenticazione. Non salvarle nella cartella del progetto. Se si usano variabili di ambiente invece di un profilo, non impostare `AWS_PROFILE` a un profilo inesistente.

## 2. Parametri della nuova installazione

```powershell
Copy-Item terraform.tfvars.json.example terraform/terraform.tfvars.json
```

Modificare il file copiato:

- `region`: default proposto `us-east-1`, dove è stata svolta la prova. Una regione diversa richiede verifica dei servizi e delle policy del proprio Lab.
- `project`: nome univoco per la nuova installazione, usato anche per bucket e tag. Il default `lab-integrato-v2` evita di riutilizzare automaticamente il nome della prova storica.
- `instance_profile` e `backup_role_name`: profilo EC2 e ruolo Backup già disponibili.
- `tester_ipv4_cidrs`: `0.0.0.0/0` rende pubblico solo l'ingresso HTTPS del WAF, come richiesto per l'esercitazione. Per un ambiente riservato inserire gli IP autorizzati.

Il SIEM usa t3.large con 2 vCPU e 8 GiB, consentita nel Lab della prova. È sotto la raccomandazione CPU del quickstart Wazuh; dimensionamento e capacità vanno verificati per il proprio carico. La VPC usa `10.20.0.0/16` e una sola AZ.

Non eseguire un secondo deploy nel laboratorio già acceso senza verificarne prima quote e risorse. Questa copia non contiene lo state della prova precedente e non si collega automaticamente a quell'ambiente. Per amministrare un ambiente esistente servono backend, chiave dello state e variabili esattamente corrispondenti, seguiti dalla revisione del piano.

## 3. Bootstrap dei bucket e inizializzazione

```powershell
& $python bootstrap.py
terraform -chdir=terraform init -backend-config=backend.hcl
terraform -chdir=terraform fmt -check -recursive
terraform -chdir=terraform validate
```

Il bootstrap crea `<project>-state-<account>` e `<project>-logs-<account>`, blocca l'accesso pubblico e configura cifratura; sullo state abilita anche il versioning. Il backend S3 utilizza locking e chiave `lab/terraform.tfstate`.

I bucket di base sono gestiti dal bootstrap per evitare la lettura Object Lock negata dal Learner Lab. Terraform gestisce invece policy, cifratura e lifecycle del bucket log. Un errore 403 non viene interpretato come autorizzazione a riutilizzare un bucket: il bootstrap si arresta. Anche proprietario e regione sono controllati prima del riutilizzo.

`terraform/backend.hcl` ed `evidence/bootstrap.json` sono generati localmente e ignorati da Git. Utilizzare gli stessi file per il ciclo di vita dell'ambiente; non cambiare progetto o account nella stessa directory runtime.

## 4. Revisione e deploy dell'infrastruttura

```powershell
terraform -chdir=terraform plan -out=lab.tfplan
terraform -chdir=terraform show lab.tfplan
```

Far controllare il piano al membro del gruppo incaricato di approvare il deploy, incluse eventuali sostituzioni di VM o Security Group. Dopo la sua approvazione applicare proprio quel piano:

```powershell
terraform -chdir=terraform apply lab.tfplan
& $python export_outputs.py
```

In PowerShell, se la propria versione interpreta male un argomento con `=`, passarlo come stringa quotata, per esempio `'-out=lab.tfplan'`.

Non è presente un workflow GitHub Actions attivo. Il deploy qui è locale e l'approvazione è un passaggio organizzativo; l'approvazione automatizzata del progetto generale richiederà un GitHub Environment e un workflow nella cartella `.github/workflows` della repository, con permessi e autenticazione AWS verificati.

## 5. Configurazione dei servizi

```powershell
& $python configure_all.py
```

Lo script esegue in ordine:

1. Attesa che le tre istanze risultino Online in SSM.
2. Avvio delle installazioni indipendenti di SIEM, web e WAF e verifica del loro esito.
3. Installazione agent Wazuh e CloudWatch su web e WAF.
4. Raccolta dell'audit JSON ModSecurity e metriche del SIEM.
5. Timer HTTPS con verifica della CA e pubblicazione della metrica di disponibilità.
6. Esportazione del solo certificato pubblico `lab-ca.crt`.

Wazuh può richiedere diversi minuti. Un errore o timeout interrompe l'orchestrazione e lascia l'ID SSM da ispezionare: un timeout del controller non annulla automaticamente il comando remoto. Le password dell'installer restano sulla VM e non vengono stampate da Ansible.

Per riprendere un singolo passaggio, dopo aver controllato lo stato del comando precedente:

```powershell
& $python configure.py waf configuration/audit-logs.yml --wait
& $python ops.py poll waf '<COMMAND_ID>'
```

La configurazione completa ripristina la baseline del WAF. Non eseguirla durante un'esercitazione senza accordarsi con il team cyber. Un'installazione Wazuh interrotta a metà richiede diagnosi prima di ripeterla: il marker di completamento evita di scambiare una semplice presenza dei binari per un'installazione completa, ma non ripara automaticamente ogni installazione parziale.

## 6. Accesso

L'IP del WAF è disponibile in `evidence/outputs.json` e con:

```powershell
terraform -chdir=terraform output -raw waf_ip
```

Aprire `https://<IP_WAF>`. La CA è privata e non viene installata nello store del sistema: i browser ordinari richiedono una configurazione di attendibilità del certificato. Per controllare HTTPS dal terminale:

```powershell
curl.exe --cacert lab-ca.crt https://<IP_WAF>/
```

Per Wazuh, su Windows:

```powershell
.\Open-WazuhTunnel.ps1
```

La dashboard risponde su `https://localhost:8443`. Su altri sistemi eseguire il port forwarding con AWS CLI e plugin:

```text
aws ssm start-session --region <REGION> --target <SIEM_INSTANCE_ID> --document-name AWS-StartPortForwardingSession --parameters portNumber=443,localPortNumber=8443
```

L'utente dashboard è `admin`. Per leggere la password generata, aprire una shell SSM sul SIEM ed eseguire:

```bash
sudo tar -O -xf /opt/aizoon/wazuh-install-files.tar wazuh-install-files/wazuh-passwords.txt
```

Il comando mostra segreti: non salvarne l'output in Git, screenshot condivisi o report pubblici.

## 7. Verifiche funzionali e WAF

```powershell
& $python -m playwright install chromium firefox webkit
& $python browser_tests.py
& $python waf_tests.py
```

Il primo script verifica ricerca prodotti via API con TLS verificato e caricamento/form di login in tre motori browser con viewport desktop e mobile. I contesti browser isolati ignorano l'attendibilità della CA per non modificare lo store del computer; la catena e l'IP vengono verificati separatamente dal client Python.

Il secondo invia una richiesta sintetica al WAF del proprio ambiente, verifica 200 in DetectionOnly e 403 in On e ripristina DetectionOnly. Cambia temporaneamente il servizio: concordarne l'esecuzione con il team cyber.

Le evidenze nuove sono generate in `evidence/`, esclusa da Git. Le evidenze storiche selezionate sono invece in `docs/evidenze/`. Non sono incluse tutte le invocazioni SSM grezze o i dump dell'account.

## 8. Backup e prova di recupero

Il piano Terraform copre le tre istanze con backup giornaliero e conservazione di un giorno. Per provare subito il recupero della web app:

```powershell
& $python backup_test.py
```

Lo script attende un backup completo, verifica che l'AMI sia privata e dello stesso account, avvia una VM temporanea in subnet privata senza ingressi, attende SSM e verifica Juice Shop senza reinstallarlo. Infine termina la VM temporanea ed elimina il relativo SG, anche se fallisce la verifica applicativa. Il backup rimane secondo il lifecycle.

È un recupero dall'AMI prodotta da AWS Backup, non una chiamata `StartRestoreJob`. La prova crea risorse a pagamento e può richiedere decine di minuti. Il file locale `evidence/backup-restore-test.json` registra gli ID prima delle verifiche. Se un'interruzione impedisce la pulizia, controllare gli ID e i tag registrati e rimuovere solo le risorse temporanee della propria prova prima di ripeterla.

## 9. Verifiche offline e sicurezza del codice

```powershell
& $python -m pip install -r requirements-dev.txt
& $python -m unittest discover -s tests -v
terraform -chdir=terraform test
```

I test Terraform usano esclusivamente mock AWS; gli `apply` nei test non creano risorse. Per controllare solo il codice senza backend o credenziali inizializzare prima con `terraform -chdir=terraform init -backend=false` in una copia dedicata ai test. Prima del deploy reale ripetere `init -reconfigure -backend-config=backend.hcl`.

Checkov va installato in un ambiente separato per evitare conflitti con le dipendenze del controller; nella prova è stato usato Checkov 3.4.5 su Python 3.12:

```text
checkov -d terraform --framework terraform --skip-download -o json
```

Il report storico conserva 116 controlli superati e 7 segnalazioni residue, senza skip. Non sono dichiarati conformità produttiva, disponibilità elevata o capacità per carichi non provati. Le segnalazioni su KMS personalizzato, retention, SNS e scelta della AZ sono descritte nel report.

## 10. Chiusura e dismissione

Fermare le VM non elimina i costi di NAT, IPv4, dischi e backup. Per terminare la prova:

1. Esportare le evidenze necessarie e chiudere i tunnel SSM.
2. Controllare i recovery point del vault dedicato: un vault non vuoto blocca la sua distruzione. Attendere la scadenza o eliminare esplicitamente i soli backup di questa prova dopo aver deciso di rinunciarvi.
3. Eseguire `terraform -chdir=terraform plan -destroy`, revisionare il piano e poi `terraform -chdir=terraform destroy`.
4. Verificare NAT, Elastic IP, dischi e risorse temporanee di recupero residue.
5. Svuotare ed eliminare il bucket log indicato nel proprio `evidence/bootstrap.json`, creato fuori dallo state Terraform.
6. Solo dopo la dismissione, se non serve più, eliminare tutte le versioni degli oggetti e il bucket del backend. Non cancellare prima lo state.

Non inserire dati personali o credenziali reali in Juice Shop. L'app vulnerabile è esposta intenzionalmente per questa esercitazione: coordinarne durata, scenari e chiusura con il gruppo.
