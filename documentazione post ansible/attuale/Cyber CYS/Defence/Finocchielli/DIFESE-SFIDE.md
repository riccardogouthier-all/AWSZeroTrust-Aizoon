# Difendere le operazioni di Juice Shop

La [matrice](sfide.csv) contiene una riga per ciascuna delle 118 chiavi del catalogo v20.4.0. Cercare il nome visualizzato e leggere il criterio da verificare. Le 18 voci marcate `docker_disabilitata=si` sono dichiarate disabilitate in Docker dalla release. La configurazione dell’istanza può restringere ulteriormente le sfide. La voce **Score Board** è censita per completezza. La navigazione e l’API delle sfide seguono la configurazione ordinaria del proxy. [Catalogo ufficiale versionato](https://github.com/juice-shop/juice-shop/blob/v20.4.0/data/static/challenges.yml)

## Assegnare una riga al team

| Codice nella matrice | Responsabile e prova |
|---|---|
| 10011–10015 | Blue applica il file ModSecurity al WAF. Verifica il match sul proxy e la ricezione su Wazuh. WEB verifica separatamente il criterio della riga. |
| WEB/942, IAM/942, WEB/941 | Blue cerca un match CRS SQLi o XSS con alert 110211 o 110212. WEB verifica query, autenticazione o rendering con un test sul componente. Il solo ID di famiglia non identifica una sfida. |
| WEB, IAM | Il team applicativo implementa il criterio su una build dedicata del backend o del sistema d’identità. Verifica esito, stato persistito e funzionamento per il titolare. |
| UI | Il team frontend verifica il DOM o le richieste del browser con dati inerti. L’access log del WAF può contenere soltanto la richiesta iniziale. |
| BUILD | Chi prepara l’immagine controlla il bundle e conserva manifest o SBOM. Il controllo offline sotto copre alcuni tipi di file. |
| OPS, WEB3 | Cloud verifica permessi, egress e gestione segreti. Il proprietario del contratto verifica gli invarianti in un ambiente di test senza fondi. |
| PUB | Obiettivo didattico o lettura legittima. Nessun alert dedicato. |

## Regole nel pacchetto Blue

| Operazione sul proxy pubblico | ID ModSecurity → Wazuh | Confine della regola |
|---|---|---|
| File sotto il deposito FTP | 10011 → 110213 | L’unico documento ammesso dal profilo è `/ftp/legal.md`. Concordare altri documenti pubblici prima dell’enforcement. |
| Download dei log di supporto | 10012 → 110214 | L’operatore usa i log privati sul nodo o nel SIEM. |
| Lettura delle metriche pubbliche | 10013 → 110215 | Verificare che il collector disponga di un percorso privato prima di attivare il blocco. |
| Registrazione con ruolo admin | 10014 → 110216 | Riguarda POST e il campo ruolo riconosciuto dal parser. La whitelist dei campi va imposta anche nel backend. |
| Quantità negativa nel carrello | 10015 → 110217 | Riguarda quantità intere negative nei campi interpretati. Prezzo, totale, limiti e proprietà sono verifiche del backend. |

Le regole sono distribuite dal ruolo WAF e dal Compose locale. Il ruolo SIEM sostituisce il gruppo di classificazione sul manager. Il motore parte in `DetectionOnly`. Un alert indica una corrispondenza, anche quando l’applicazione restituisce 200. I test sul browser, le correzioni applicative e i controlli sul contratto indicati nella matrice sono attività da implementare o verificare sui componenti dei rispettivi team.

## Collaudo senza consultare l’applicazione delle sfide

1. **Inventario.** La variante Linux/amd64 del digest del lock contiene Juice Shop `20.4.0-SNAPSHOT`, revisione `266448a`. Il catalogo estratto dal filesystem dell’immagine ha SHA-256 `09e98ee2b10d10cc7ec3e749c4e251928f935db51dd6fc9e94fe40f8ce012c92`. Chiavi, nomi e flag Docker coincidono con tutte le 118 righe. Per controllare la versione realmente in esecuzione, impostare `CONTAINER_WEB`, annotare il digest e copiare il file statico dal container come sotto. [Sorgente della revisione](https://github.com/juice-shop/juice-shop/blob/266448a/data/static/challenges.yml)
2. **Build.** Passare a `check_public_assets.py` la directory effettivamente destinata alla pubblicazione, con i suoi percorsi relativi (incluso `ftp/` se esposto). In CI usare l’exit code come condizione del rilascio del profilo difeso. Il controllo segnala backup, log, alcuni file IaC, link simbolici e voci FTP fuori allowlist. Servizi che pubblicano directory esterne vanno inventariati separatamente.
3. **Kali.** Seguire il [manuale](RUNBOOK.md) per avviare Compose sulla porta 8088. Ricreare il servizio WAF dopo l’aggiornamento e controllare `nginx -t`. Una richiesta innocua a un nome di prova inesistente sotto il deposito deve produrre 10011 anche se il backend restituisce 404. Una richiesta all’informativa legale deve passare senza 10011. Conservare ID transazione e stato HTTP per entrambe.
4. **SIEM.** Sulle VM Ansible applicare il ruolo SIEM e verificare `wazuh-analysisd -t`. Controllare che l’agente WAF segua il file error.log, poi cercare 110213 nel manager con agente e timestamp del test. Se manca, confrontare location, precedenza delle regole locali e soglia di alert. Per 10014/10015 verificare in staging che ModSecurity analizzi JSON per il content type del client.
5. **AWS Agosta 3.1.** L’adattatore legge la copia in `v3.1/cyber/files/`. Cloud aggiorna quella copia con il file WAF revisionato. Sul manager adotta `roles/siem/files/blue_team_ctf.xml` in `/var/ossec/etc/rules/`, verifica gli ID, esegue `wazuh-analysisd -t` e ricarica il manager dopo il controllo. Il bootstrap 3.1 attuale configura l’archiviazione sul SIEM e richiede questa integrazione aggiuntiva per distribuire le classificazioni. Sul tentativo 2 Gouthier integrare le stesse modifiche nel cloud-init. Il Compose Kali contiene WAF e WEB. [Adattatore 3.1](https://github.com/riccardogouthier-all/AWSZeroTrust-Aizoon/blob/938458d/AWS%20ACA/Agosta/v3.1/apply_cyber.py) · [Difesa live](https://github.com/riccardogouthier-all/AWSZeroTrust-Aizoon/blob/938458d/AWS%20ACA/Agosta/v3.1/docs/DIFESA_LIVE.md)
6. **Accettazione per sfida.** Annotare chiave, digest, controllo, prova lecita, esito osservato, stato applicativo e titolare del prossimo intervento. Classificare come *previene* solo dopo un rifiuto verificato con stato integro e un controllo positivo autorizzato. Per la promozione al blocco usare un ambiente dedicato e tornare a DetectionOnly se si interrompe un flusso previsto.

```bash
mkdir -p runtime
docker cp "$CONTAINER_WEB:/juice-shop/data/static/challenges.yml" runtime/challenges.yml
python3 tools/check_challenges.py runtime/challenges.yml
python3 tools/check_public_assets.py "$WEBROOT_DI_RELEASE"
docker compose -f lab/compose.yml up -d --force-recreate waf
docker compose -f lab/compose.yml exec waf nginx -t
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8088/ftp/bt-file-inesistente.txt
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8088/ftp/legal.md
```

La documentazione ufficiale descrive le azioni disruptive in DetectionOnly e la sintassi delle regole locali Wazuh. [ModSecurity Reference Manual](https://github.com/owasp-modsecurity/ModSecurity/wiki/Reference-Manual-%28v3.x%29) · [Wazuh custom rules](https://documentation.wazuh.com/current/user-manual/ruleset/rules/custom.html)
