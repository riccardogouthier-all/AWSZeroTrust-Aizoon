# Registro di validazione · 13 novembre 2026

| Verifica | Esito osservato |
|---|---|
| Base storica del primo audit | ZIP ufficiale con commento `90a1dca2b5f218f9b3af267c0d38604871bd3386`; tree Git dei 79 file identico a `021e7f6b9564ccf5d7fed620e63edc0c71cc9c74`. Oggetto commit verificato per SHA. Il clone HTTPS diretto ha fallito la risoluzione DNS; il checkout locale usa questa revisione come limite di una cronologia shallow. |
| Sintassi dei file | 12 YAML letti con un parser YAML. Template Jinja renderizzato per WAF e WEB con variabili obbligatorie e analizzato come XML. Tre input WAF e un input WEB nell’output. |
| Verificatori Python | Cinque test offline passati. Coprono risposta applicativa attesa, rifiuto di Burp e 403, identità dell’agente, provenienza, correlazione, modalità errata, CRS o regola assenti, righe parziali e marker diverso. Dati sintetici. |
| Sesta prova HTTP su server locale | Connessione a loopback negata da Windows (10013). Il test riporta skip per questo errore specifico ed è ripetibile su Kali. |
| Integrazione | Docker, Ansible eseguibile, Terraform e Checkov indisponibili su questo host. Nessuna esecuzione su AWS, dashboard, endpoint o account condivisi. Il parsing YAML non esercita i moduli Ansible. L’idempotenza runtime, la consegna Wazuh e la capacità del SIEM devono essere misurate sui target. |

Per ripetere i test dal percorso Blue Team:

```bash
python3 -B -m unittest discover -s tests -v
ansible-galaxy collection install -r requirements.yml
ansible-playbook -i inventory/vm.example.yml site.yml -e @settings.example.yml --syntax-check
ansible-playbook -i inventory/vm.example.yml verify.yml --syntax-check
```

Su Kali eseguire poi la prova Compose in [RUNBOOK.md](RUNBOOK.md). Su AWS raccogliere i risultati del secondo run Ansible, la sonda locale e centrale con ID coincidente, lo stato dei due agenti e il test dell’allowlist. Eseguire Checkov anche sul codice di questa PR e archiviare una copia sanitizzata del report per il corso. I risultati Checkov nel sottoprogetto Agosta appartengono al suo Terraform e alla sua prova storica.

Al nuovo controllo il branch di lavoro è stato riallineato al commit pubblico `c00b9d9`. La guida Gouthier riporta propri controlli statici. Questa revisione Blue Team non ha eseguito un deploy AWS.
