# Runbook Cyber

Comandi Bash da `Cyber CYS/Defence/Finocchielli`. [Accessi account personale](../ACCESSO_BLUE_TEAM_v3.1.md).

## Stack AWS già distribuito

Non eseguire site.yml sulle VM configurate da Cloud. In 3.1 l'adattatore integra regola 10001 e input senza reinstallazione.

```bash
# Ogni nodo, via SSM
cloud-init status --long
# WAF
sudo docker exec aizoon-waf nginx -t
sudo grep '^MODSEC_RULE_ENGINE=' /opt/aizoon/waf.env
# SIEM
sudo systemctl is-active wazuh-manager wazuh-indexer filebeat wazuh-dashboard
sudo /var/ossec/bin/agent_control -lc
```

Per apertura/chiusura archivi, enforcement e rollback usare [Difesa live](../../../AWS%20ACA/Agosta/v3.1/docs/DIFESA_LIVE.md). WAF/WEB→SIEM:1514/1515; WAF→WEB:3000. Confermare regione, account e ID prima dei comandi.

## WAF locale — Kali/Docker, 127.0.0.1:8088

Prerequisiti: Docker, Compose v2, Python 3, jq. Porta 8088 libera; backend non pubblicato.

```bash
mkdir -p runtime
chmod 700 runtime
sudo install -d -o 101 -g adm -m 2750 runtime/logs
LOCK='../../../AWS ACA/Agosta/laboratorio_aws_2.0/images.lock.json'
export BT_WAF_IMAGE="$(jq -er .waf "$LOCK")"
export BT_WEB_IMAGE="$(jq -er .juice_shop "$LOCK")"
dc() { sudo env BT_WAF_IMAGE="$BT_WAF_IMAGE" BT_WEB_IMAGE="$BT_WEB_IMAGE" docker compose -f lab/compose.yml "$@"; }
dc config -q
dc up -d
dc exec -T waf nginx -t
curl --noproxy '*' --retry 15 --retry-connrefused --retry-delay 2 -fsS http://127.0.0.1:8088/ -o /dev/null
python3 tools/probe.py > runtime/probe.json
MARK="$(jq -er .bt_probe runtime/probe.json)"
sudo python3 tools/check_evidence.py runtime/logs/modsec_audit.log "$MARK"
```

Atteso: HTTP 200, rule 10001, DetectionOnly, firma CRS e transaction ID. Per chiudere: dc down; i bind mount rimangono. Il marker sintetico non prova la copertura di tutte le famiglie CRS.

## Installazione Ansible — solo tre VM dedicate

Ubuntu 24.04 amd64, un host distinto per ruolo; WEB:3000 già predisposto da Cloud, container Juice Shop con log json-file. Su rete locale usare SSH con chiave; su EC2 servono identità SSM, bucket di scambio proprio e inventario con regione/tag corretti. Non usare il bucket Flow Logs come scambio.

```bash
python3 -m venv runtime/venv
. runtime/venv/bin/activate
python -m pip install 'ansible-core>=2.21,<2.22' boto3 botocore
ansible-galaxy collection install -r requirements.yml
cp settings.example.yml runtime/settings.yml
curl -fSLo runtime/wazuh-install.sh https://packages.wazuh.com/4.14/wazuh-install.sh
sha256sum runtime/wazuh-install.sh
cp inventory/vm.example.yml runtime/inventory.yml
```

Impostare IP/inventario, bt_tls_ip, bt_wazuh_version=4.14.10 e bt_installer_sha256 dopo verifica del download ufficiale. L'hash locale fissa i byte, non autentica da solo l'editore. Ruoli: SIEM → controllo WEB → WAF → agenti. Installer/pacchetti parziali o incompatibili bloccano l'adozione; non forzare reinstallazioni. Agenti 4.14.10-1, stack centrale stessa patch; pacchetti in hold.

```bash
INV=runtime/inventory.yml
ansible-playbook -i "$INV" site.yml -e @runtime/settings.yml --syntax-check
ansible-playbook -i "$INV" site.yml -e @runtime/settings.yml -e '{"bt_archive_events":true}'
python3 tools/probe.py --url "https://$WAF_IP" --ca runtime/waf.crt > runtime/probe.json
MARK="$(jq -er .bt_probe runtime/probe.json)"
ansible-playbook -i "$INV" verify.yml -e @runtime/settings.yml -e "bt_probe=$MARK"
```

Confrontare transaction ID, access log e audit manager da agente waf; verificare agenti Active nella dashboard autenticata. A fine finestra: bt_archive_events=false e applicazione del ruolo SIEM; verificare secondo run/idempotenza. Lo spegnimento della raccolta non cancella gli archivi.

## Diagnostica

| Sintomo | Verifica |
|---|---|
| 502/504 | WEB:3000 dal WAF, container e SG |
| 200 senza audit | RelevantOnly, regola 10001 montata, UID 101 e permessi; nginx -t |
| Audit WAF assente sul manager | input syslog con bt_waf_audit, agente waf, porta 1514, clock e dimensione riga |
| Evento in archives ma non in dashboard | Regola di detection, alerts.json, Filebeat e indici; archivi non indicizzati automaticamente |
| TLS | SAN, scadenza, CA e IP client; chiavi private solo sui nodi |
| Bootstrap/capienza | Log privato installer, RAM/disco/iowait; niente bypass dei controlli installer |

Percorsi: WAF /opt/blue-team/logs (link a /opt/aizoon/logs nel Cloud), manager /var/ossec/logs/archives/archives.json e alerts/alerts.json. Audit seriale JSON AHZ, prefisso bt_waf_audit per evitare i limiti sugli array del decoder JSON. Logrotate copytruncate può perdere dati nella finestra di copia; definire retention archivi/indici e verificare logrotate -d.

Reference SIEM: 4 vCPU/8 GiB/50 GB; le EC2 da 2 vCPU sono ridotte. Misurare ritardo del marker, memoria, spazio e carico prima del tuning. Enrollment iniziale protetto dagli SG nel lab; in ambienti condivisi usare autenticazione e validazione del certificato manager. Prima di upgrade: backup e prova di ripristino, stack centrale prima degli agenti.
