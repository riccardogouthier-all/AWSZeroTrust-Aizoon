# Flussi Blue Team

```text
Client → WAF:443 → Juice Shop:3000
          ↓ access/error/audit
       agent WAF ──1514──→ Wazuh manager → Filebeat → indexer → dashboard
       agent WEB ──1514──↗
Enrollment agent: TCP 1515
```

| Dato | Fonte / uso |
|---|---|
| Access log | Richieste HTTP; una richiesta normale può non produrre audit/alert |
| Audit ModSecurity | JSON seriale, parti AHZ, regole CRS e transaction ID |
| Agent WEB | LogPath json-file del solo container Juice Shop |
| archives.json | Eventi ricevuti dal manager con logall_json=yes |
| alerts.json / wazuh-alerts-* | Eventi che soddisfano regole di detection e vengono indicizzati |
| Flow Logs | ACCEPT/REJECT di rete; nessun payload HTTP |

L'audit viene inoltrato come syslog con prefisso `bt_waf_audit`: evita i limiti del decoder JSON sugli array di oggetti. La sonda 10001 forza l'audit del marker; il verificatore confronta transaction ID, agente waf, location, CRS, modalità e HTTP 200. Non dimostra l'efficacia di tutte le regole CRS.

Baseline DetectionOnly. Prova asincrona: attacco → analisi → modifica → replay. Prova sincrona: Red invia traffico, Blue modifica WAF/SIEM tramite ruolo operativo. In entrambi i casi registrare timestamp UTC, marker, rule ID, esito e regressioni sul traffico normale.

[Runbook](RUNBOOK.md) · [Difesa live](../../../AWS%20ACA/Agosta/v3.1/docs/DIFESA_LIVE.md).

Per **Payback Time**, Blue cerca il match WAF 10015 e l’alert Wazuh 110217. WEB verifica separatamente che il checkout ricalcoli quantità e totale. Per **View Basket**, WEB verifica che due account fittizi vedano soltanto il proprio carrello. Per ciascuna prova il team registra sia il segnale osservato sia il risultato applicativo. [Difese per sfida](DIFESE-SFIDE.md) · [Matrice](sfide.csv).
