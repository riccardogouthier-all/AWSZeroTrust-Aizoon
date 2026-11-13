# Manuale operativo · osservazione del traffico WAF

Tutti i comandi Bash partono da `Cyber CYS/Defence/Finocchielli/` in un checkout del progetto. Il percorso breve richiede solo Kali e Docker. Il percorso completo usa Kali come controller e tre VM Ubuntu 24.04 amd64, locali o EC2. Il collaudo distingue la risposta dell’applicazione dall’arrivo effettivo della telemetria.

## 1 · WAF locale su Kali, porta 8088

Installare Docker, Compose v2, Python 3 e jq. Il backend comunica sulla rete interna di Compose. L’unica porta pubblicata è `127.0.0.1:8088`; il WAF ascolta sulla 8080 **nel container**. Il comando della sonda ignora i proxy HTTP del sistema. [Docker su Kali](https://www.kali.org/docs/containers/installing-docker-on-kali/) · [Compose su Kali](https://pkg.kali.org/pkg/docker-compose)

```bash
sudo apt update
sudo apt install docker.io docker-compose python3 python3-venv jq curl
sudo systemctl enable --now docker
sudo docker compose version
ss -ltn '( sport = :8088 )'
umask 077
mkdir -p runtime
sudo install -d -o 101 -g adm -m 2750 runtime/logs
LOCK='../../../AWS ACA/Agosta/laboratorio_aws_2.0/images.lock.json'
export BT_WAF_IMAGE="$(jq -er .waf "$LOCK")"
export BT_WEB_IMAGE="$(jq -er .juice_shop "$LOCK")"
dc() { sudo env BT_WAF_IMAGE="$BT_WAF_IMAGE" BT_WEB_IMAGE="$BT_WEB_IMAGE" docker compose -f lab/compose.yml "$@"; }
dc config -q
dc up -d
dc ps
dc exec -T waf nginx -t
curl --noproxy '*' --retry 15 --retry-connrefused --retry-delay 2 -fsS http://127.0.0.1:8088/ -o /dev/null
python3 tools/probe.py > runtime/probe.json
MARK="$(jq -er .bt_probe runtime/probe.json)"
sudo python3 tools/check_evidence.py runtime/logs/modsec_audit.log "$MARK"
```

Su un avvio lento, attendere che Juice Shop completi il bootstrap e ripetere la sonda. L’esito atteso contiene due 200, ID transazione, rule ID 10001, modalità e firma CRS. L’ID appartiene a una regola di collaudo distribuita prima delle regole CRS. La firma attesta il caricamento del ruleset. L’efficacia delle singole famiglie di regole richiede il successivo tuning. Per terminare questo solo progetto Compose usare `dc down`; i file in `runtime/logs` rimangono sul disco. Su Kali la prova breve scrive log su bind mount: controllare lo spazio, raccogliere l’estratto e rimuovere i log locali a fine sessione secondo la retention concordata.

## 2 · Scegliere i target

| Percorso | Configurazione effettiva |
|---|---|
| Gouthier · tentativo 2 | Terraform e cloud-init configurano già le tre EC2. Default us-east-1, WAF 10.20.1.10, WEB 10.20.2.10, SIEM 10.20.2.11. Controllare i CIDR HTTPS e i flussi 3000, 1514 e 1515 con Cloud. Usare la verifica AWS qui sotto. |
| Locale completo | Tre VM Ubuntu 24.04 amd64 su rete host-only, amministrate da Kali. SSH con chiave solo sulla rete di gestione locale; NAT in uscita per i pacchetti, nessun port-forward internet. Esempio WAF/WEB 2 GiB e 20 GiB ciascuna; SIEM 4 vCPU, 8 GiB, almeno 50 GiB e margine per SO e log. Adeguare memoria host o usare la sola prova breve. L’inventario di esempio contiene tre IP di laboratorio. |
| Agosta già operativo | Chiedere al Cloud Team gli ID associati al suo stato in Virginia. Leggere via SSM `docker inspect aizoon-waf --format '{{.Config.Image}}'`, `/opt/aizoon/waf.env` (solo le chiavi MODSEC), `/opt/aizoon/logs`, lo stato dei servizi e degli agenti. Usare il tunnel già fornito da Agosta. Il suo audit non ha la regola 10001 del contributo. Evitare di avviare un secondo WAF sulla 443 o reinstallare un manager con enrollment attivi. |

### Verifica AWS sul tentativo 2

La guida Gouthier aggiornata introduce `aws configure`. Se occorre inizializzare un profilo nominato, usare `aws configure --profile learner-lab`. Con credenziali temporanee il profilo locale deve includere anche `aws_session_token` della stessa sessione del laboratorio: il normale prompt interattivo richiede access key e secret, ma non acquisisce il token. Se il profilo è già valido, basta selezionarlo e verificarlo. In Bash usare `export AWS_PROFILE=learner-lab`; in PowerShell `$env:AWS_PROFILE = 'learner-lab'`. Chi usa il profilo default può omettere la selezione. Controllare account e ruolo con il comando STS qui sotto prima di leggere lo state. Tenere l'intero blocco credenziali nel profilo privato, fuori da repo e report. [Guida AWS ai profili e alle credenziali temporanee](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)

Usare il profilo temporaneo e lo state del deploy confermati dal Cloud Team. Il solo checkout non contiene lo state della sua sessione. Dal controller:

```bash
TF='../../../AWS ACA/Gouthier/tentativo 2'
export AWS_REGION=us-east-1
aws sts get-caller-identity
WAF_IP="$(terraform -chdir="$TF" output -raw waf_ip)"
SIEM_ID="$(terraform -chdir="$TF" output -json instances | jq -er .siem.id)"
terraform -chdir="$TF" output -json instances
terraform -chdir="$TF" output -raw ssm_siem_tunnel
```

1. Su ciascuna VM aprire una sessione SSM e leggere `cloud-init status --long`. In caso di errore consultare localmente `/var/log/cloud-init-output.log`. Un apply riuscito può precedere il completamento o il fallimento del bootstrap.
2. Dal WAF verificare `sudo docker exec aizoon-waf nginx -t`, `sudo grep '^MODSEC_RULE_ENGINE=' /opt/aizoon/waf.env` e recuperare la sola CA pubblica `/opt/aizoon/tls/lab-ca.crt`. Sul SIEM verificare `systemctl is-active wazuh-manager wazuh-indexer filebeat wazuh-dashboard` e `sudo /var/ossec/bin/agent_control -lc` per web e waf.
3. Dal CIDR autorizzato inviare una richiesta innocua con `MARK="bt-$(date -u +%s)-$$"` e `curl --noproxy '*' --cacert runtime/lab-ca.crt -fsS "https://$WAF_IP/?bt_probe=$MARK" -o /dev/null -w '%{http_code}\n'`. Atteso 200. Cercare lo stesso marker nel file WAF `/opt/aizoon/logs/access.log` e in `/var/ossec/logs/archives/archives.json` sul SIEM con agente waf e location access.log. Per l’audit confrontare l’ID di una transazione già registrata in modsec_audit.log con il record ricevuto sul manager. Con RelevantOnly una normale richiesta 200 può generare solo l’access log.
4. L’output `ssm_siem_tunnel` stampa il comando da eseguire per la dashboard su 8443. Verificare i due agenti in una sessione autenticata. Annotare timestamp, versione Wazuh, rule ID e identificatore minimizzato. Le evidenze Agosta appartengono a un’altra esecuzione.

I playbook nelle sezioni 3–5 installano il profilo Blue Team su **VM dedicate**. Sul tentativo 2 i componenti e i percorsi sono già gestiti da cloud-init. Il bucket dei Flow Logs è destinato ai log. L’inventario EC2 Ansible fornito è un esempio per un ambiente separato dotato di un proprio bucket di scambio.

**Capienza.** La t3.large offre 2 vCPU e 8 GiB. Wazuh indica 4 vCPU, 8 GiB e 50 GB per 1–25 agenti con 90 giorni di alert indicizzati. Sul disco root da 50 GiB insistono anche OS, pacchetti e archivi grezzi. Usare la taglia del piano per una prova misurata e breve. Misurare CPUCreditBalance, memoria libera, iowait, spazio in `/var/lib/wazuh-indexer` e `/var/ossec/logs`, ritardo fra marker e ricezione. Se si accumulano code o l’installer rifiuta la macchina, sospendere il collaudo e concordare con Cloud CPU/disco o una VM locale più capiente. Evitare di ignorare i controlli dell’installer. NAT, IPv4, EBS e backup hanno un ciclo di vita distinto dalle EC2. Il preventivo del documento va ricalcolato per regione e ore reali. [Wazuh Quickstart](https://documentation.wazuh.com/current/quickstart.html) · [Istanze T3](https://aws.amazon.com/ec2/instance-types/t3/) · [AWS Pricing Calculator](https://calculator.aws/)

## 3 · Preparare controller, versioni e parametri

Su Kali con Python 3.12–3.14 usare una venv per il controller. Per AWS servono anche AWS CLI v2, Session Manager plugin e gli output Terraform della distribuzione scelta. Conservare la lista delle versioni realmente risolte.

```bash
mkdir -p runtime
chmod 700 runtime
python3 -m venv runtime/venv
. runtime/venv/bin/activate
python -m pip install 'ansible-core>=2.21,<2.22' boto3 botocore
ansible-galaxy collection install -r requirements.yml
ansible-galaxy collection list > runtime/collections.txt
cp settings.example.yml runtime/settings.yml
curl -fSLo runtime/wazuh-install.sh https://packages.wazuh.com/4.14/wazuh-install.sh
sha256sum runtime/wazuh-install.sh
```

Esaminare la copia scaricata dal dominio ufficiale, fissarne l’impronta in `runtime/settings.yml`. Un hash calcolato sul download serve a ripetere gli stessi byte; da solo non autentica l’editore. La release verificata è Wazuh **4.14.10**, pubblicata il 5 novembre 2026. L’assistente usa un URL di serie mobile; il ruolo confronta digest e versioni risultanti. Gli agenti amd64 usano il deb `4.14.10-1` con SHA-512 ufficiale. Manager, indexer e dashboard devono usare la stessa patch. Filebeat usa la versione fornita dall’assistente. Il ruolo mantiene i pacchetti in hold fino alla finestra di upgrade. [Release Wazuh](https://documentation.wazuh.com/current/release-notes/release-4-14-10.html) · [Pacchetti e checksum](https://documentation.wazuh.com/current/installation-guide/packages-list.html) · [Matrice Ansible](https://docs.ansible.com/projects/ansible/latest/reference_appendices/release_and_maintenance.html)

**WAF.** Il digest già in `images.lock.json` identifica l’immagine integrata Nginx + connettore + libModSecurity + CRS. La pagina release consultata elenca CRS 4.30.0 e 4.25.2 LTS. OWASP indica manutenzione della linea 4.25.x fino al terzo trimestre 2027. La versione contenuta nel digest del progetto va letta nell’audit, campi `producer.modsecurity`, `connector`, `components`, e con `nginx -v`. Per aggiornare provare un digest candidato su 8088, controllare UID 101, caricamento e formato audit, poi proporre una PR sul lock. [Immagine ufficiale e parametri](https://github.com/coreruleset/modsecurity-crs-docker) · [Release CRS](https://github.com/coreruleset/coreruleset/releases) · [Supporto LTS](https://coreruleset.org/20260321/announcing-crs-v4-25-lts/)

| Parametro | Valore o provenienza |
|---|---|
| Regione, Project, Environment e Role | Filtri in `inventory/lab.aws_ec2.yml`; tenere coerenti regione CLI, plugin e Terraform. Per nomi diversi copiare il file in `runtime/<nome>.aws_ec2.yml`. |
| Bucket SSM, manager e backend | `BT_BUCKET` è un bucket di scambio fornito dal gestore delle sole EC2 dedicate ad Ansible. `bt_private_ip` deriva dai metadati dell’istanza con tag Role, verificabile nell’inventario EC2. In locale è nell’inventario. |
| Certificato | `bt_tls_ip` è l’EIP effettivo o l’IP della VM host-only. Self-signed di laboratorio, SAN IP, validità 30 giorni; il client verifica il certificato esportato dal controller. |
| Versioni | `bt_wazuh_version`, `bt_installer_sha256`, digest provenienti dal lock condiviso. Per provare un candidato su EC2 usare `bt_waf_image` con digest completo. |
| Raccolta | `bt_web_container` individua il container dell’app; il ruolo risolve il suo LogPath esatto. `bt_archive_events` apre o chiude la finestra sul manager. Porte e DetectionOnly seguono il contratto della fase. |
| Valori privati | Mettere inventario locale, impostazioni, log e certificato pubblico esportato in `runtime/`. Chiavi TLS e password generate restano sui nodi. Per la custodia usare Vault cifrato o il gestore segreti del gruppo, con password di sblocco separata. |

## 4 · Installazione completa

1. **Common / Cloud.** Aggiornare le tre VM e verificare `timedatectl`, spazio e SSM. Su AWS controllare account, regione, lista istanze e output prima di eseguire play. Il ruolo Blue richiede esattamente un nodo per ciascun ruolo e Ubuntu 24.04 amd64.
2. **SIEM / Blue.** L’assistente all-in-one installa indexer, manager, Filebeat e dashboard. Bootstrap sul nodo in `/root/blue-team-wazuh`; log privato e archivio generato contengono credenziali. Trasferire quelle necessarie al custode via canale amministrativo protetto; per un file offline locale già privato usare `ansible-vault encrypt <file>` e custodire la password fuori repo. Non incollare l’output della password nel report.
3. **WEB / Cloud.** Su un nodo WEB nuovo installare `docker.io`, abilitare il demone e avviare l’immagine Juice Shop del lock con pubblicazione solo sull’IP privato. Il ruolo Blue verifica l’identità della pagina e il driver json-file. Se il WEB è già gestito, verificare quello esistente.
4. **WAF / Blue.** Il ruolo configura TLS, upstream privato, il bind dell’IP privato EC2 per 443 (AWS traduce l’EIP), Nginx/ModSecurity/CRS, log persistenti e rotazione. **Agenti / Blue.** L’agente WEB legge il solo container scelto; il WAF legge access, error e audit. L’enrollment iniziale usa 1515, la connessione eventi persistente usa 1514. La baseline affida l’ammissione al perimetro SG per ruolo. Per ambienti condivisi attivare validazione del certificato del manager ed enrollment autenticato, distribuendo CA e segreti fuori Git. [Enrollment Wazuh](https://documentation.wazuh.com/current/user-manual/agent/agent-enrollment/security-options/index.html)

Esempio per un **WEB nuovo**. Impostare sul nodo `BT_WEB_IMAGE` al digest letto dal lock e `WEB_PRIVATE_IP` al suo IP. Eseguire come amministratore del nodo.

```bash
sudo apt-get update && sudo apt-get install -y docker.io
sudo systemctl enable --now docker
sudo docker run -d --name juice-shop --restart unless-stopped \
  --log-driver json-file --log-opt max-size=10m --log-opt max-file=3 \
  -p "${WEB_PRIVATE_IP:?}:3000:3000" "${BT_WEB_IMAGE:?}"
curl --noproxy '*' -fsS "http://$WEB_PRIVATE_IP:3000/" -o /dev/null
```

Per le VM dedicate copiare `inventory/vm.example.yml` in `inventory/private-vm.yml`, impostare gli IP e usare `INV=inventory/private-vm.yml`. Impostare `WAF_IP` all’indirizzo del WAF host-only. Usare la chiave SSH locale e sudo (opzione `-K` se serve). Prima dell’installazione aggiornare `bt_tls_ip` e il digest dell’assistente in `runtime/settings.yml`.

```bash
ansible-playbook -i "$INV" site.yml -e @runtime/settings.yml --syntax-check
ansible-playbook -i "$INV" site.yml -e @runtime/settings.yml -e '{"bt_archive_events":true}'
python3 tools/probe.py --url "https://$WAF_IP" --ca runtime/waf.crt > runtime/probe.json
MARK="$(jq -er .bt_probe runtime/probe.json)"
ansible-playbook -i "$INV" verify.yml -e @runtime/settings.yml -e "bt_probe=$MARK"
```

Conservare solo timestamp UTC, revisione, digest, risposta HTTP, transaction ID, rule ID ed esito. Verificare che `waf` e `web` risultino Active anche nell’interfaccia autenticata. Sul tentativo 2, con SIEM_ID ricavato nella sezione 2, aprire il tunnel dal controller con AWS CLI v2 e relativo plugin; su rete host-only usare il percorso amministrativo della VM SIEM.

```bash
aws ssm start-session --region "$AWS_REGION" --target "$SIEM_ID" \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["443"],"localPortNumber":["8443"]}'
```

Aprire `https://localhost:8443`. Verificare con il gestore della dashboard CA, nome e impronta del certificato via canale SSM. Per validazione browser completa usare un nome coperto dal SAN instradato verso loopback e la CA del lab. Creare account personali in sola lettura per la consultazione. Il 200 della schermata di login attesta soltanto la raggiungibilità.

## 5 · Telemetria, gestione e ripristino

| Origine | Percorso utile | Verifica o intervento |
|---|---|---|
| WAF | `/opt/blue-team/logs/{access.log,error.log,modsec_audit.log}` | L’audit seriale è JSON su una riga. Parti AHZ evitano header e body completi; URI, IP e dettagli del match possono comunque essere sensibili. Una riga per ogni transazione rilevante, più la sonda forzata. Confrontare ID del test, ora e identificatore della transazione. |
| Agent | `/var/ossec/logs/ossec.log`, `/var/ossec/etc/ossec.conf` | Controllare permessi di lettura del processo, input duplicati e clock. WEB usa il LogPath Docker effettivo; rieseguire il ruolo se il container viene ricreato. Il log Docker contiene stdout/stderr dell’app, la copertura applicativa dipende da ciò che Juice Shop emette. |
| Manager | `/var/ossec/logs/archives/archives.json` per eventi ricevuti; `/var/ossec/logs/alerts/alerts.json` per gli alert | L’agente incapsula l’audit su una riga con prefisso `bt_waf_audit`, il verificatore estrae solo i campi consentiti. Il decoder JSON standard ha limiti sugli array di oggetti come `transaction.messages[]`. La prova usa il record grezzo; una dashboard di ruleId CRS richiederà normalizzazione e regole dedicate nella fase successiva. |
| Indexer e dashboard | Servizi `wazuh-indexer`, `filebeat`, `wazuh-dashboard`; indici `wazuh-alerts-*` | Verificare spazio, stato Filebeat e indici con account autorizzato. Le transazioni grezze archiviate sul manager non compaiono automaticamente nella vista alert. Evitare l’indicizzazione indiscriminata degli archivi sui 50 GiB. |
| Rete | VPC Flow Logs e SG | Gli ACCEPT/REJECT aiutano a diagnosticare 3000 e 1514/1515. Il contenuto HTTP e gli ID delle regole si cercano sul WAF/SIEM. |

[Formato localfile](https://documentation.wazuh.com/current/user-manual/reference/ossec-conf/localfile.html) · [Decoder JSON](https://documentation.wazuh.com/current/user-manual/ruleset/decoders/json-decoder.html) · [Archivi del manager](https://documentation.wazuh.com/current/user-manual/manager/event-logging.html)

Al termine della finestra ripristinare `bt_archive_events: false` e rieseguire il playbook per il SIEM con `--limit siem`. Attendere un secondo giro con le stesse impostazioni e controllare le modifiche. Verificare rotazione con `logrotate -d /etc/logrotate.d/blue-team-waf`; `copytruncate` ha una piccola finestra di perdita. Concordare con il gruppo durata e cancellazione dei vecchi archivi sul manager, anche compressi. Per gli indici impostare una policy di retention coerente con esercitazioni e disco. Effettuare backup protetto di configurazioni, CA e dati e provare il ripristino prima di upgrade concordati (componenti centrali prima degli agenti). [Retention indici](https://documentation.wazuh.com/current/user-manual/wazuh-indexer-cluster/index-lifecycle-management.html)

| Sintomo | Dove controllare | Esito richiesto |
|---|---|---|
| Titolo Burp o errore proxy | `ss -ltnp`, `dc ps`, `curl --noproxy '*' -i http://127.0.0.1:8088/` | Contenuto Juice Shop e riga nuova nel log del WAF. Se 8088 è occupata identificare il processo prima di cambiare il mapping. |
| 502/504 | Dal nodo WAF `curl --noproxy '*' -fsS http://<WEB_PRIVATO>:3000/`; Docker, IP di bind, SG in entrambe le direzioni | Prima HTTP 200 da WEB, poi 200 tramite il WAF. |
| TLS rifiutato | SAN, scadenza, impronta, CA fornita al client, corrispondenza EIP | `openssl x509 -in runtime/waf.crt -noout -dates -ext subjectAltName`. Per rinnovo pianificato rigenerare il certificato sul WAF, rieseguire ruolo e ridistribuire la parte pubblica. Il privato resta sul nodo. |
| 200 ma audit assente | `nginx -t`, digest, regola montata, UID 101 e file di audit scrivibile, seriale JSON; confrontare un marker nuovo | Il verificatore deve trovare 10001 e CRS. Un 403 richiede verifica di modalità, risposta upstream e regole Nginx. |
| Agente assente o duplicato | `agent_control -lc` sul manager, `systemctl status wazuh-agent` sull’endpoint, `ss -ltn` sul SIEM; 1515 per enrollment e 1514 per eventi | Verificare nome, chiave associata e manager prima di riassociare un nodo ricreato. Rieseguire il ruolo solo dopo aver corretto la causa. |
| Audit locale presente, nulla in dashboard | Prima controllare archives.json, agent.name, location, latenza, max dimensione riga; poi Filebeat, alert e intervallo UTC | Verificare il marker nell’archivio centrale. Per la diagnosi della fase regole usare `/var/ossec/bin/wazuh-logtest` sul manager con un evento minimizzato. |
| Bootstrap interrotto o risorse insufficienti | Log root-only sotto `/root/blue-team-wazuh`, servizi, memoria/disco e `journalctl -u wazuh-indexer` | Il ruolo ferma un’installazione parziale o mista. Riparare dal log o ripristinare lo snapshot della VM dedicata; evitare reinstallazioni forzate sul manager del gruppo. |

Il passaggio al blocco richiede il baseline del traffico normale, analisi dei falsi positivi per ID e percorso, una finestra con Red e un ritorno provato a DetectionOnly. Conservare report Checkov e screenshot minimizzati separatamente dai log grezzi. Spegnimento o dismissione AWS spettano al titolare dello state verificato.
