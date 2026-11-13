# Evidenze — 13 novembre 2026

| File | Perimetro |
|---|---|
| [validazione.json](validazione.json) | Test del deploy privato; limiti espliciti |
| [controlli_pacchetto.json](controlli_pacchetto.json) | Validazione del pacchetto Git |
| [power-controls.json](power-controls.json) | 13 unit test e permessi AWS DryRun; niente stop reale |
| [browser-results.json](browser-results.json) | Sei motori/viewport; screenshot nella cartella |
| [waf-test-results.json](waf-test-results.json) | 200/403/rollback |
| [cyber-transaction.json](cyber-transaction.json) | Correlazione WAF/manager |
| [backup-status.json](backup-status.json) | Backup COMPLETED, identificativi operativi rimossi |
| [blue-team-wazuh-verification.json](blue-team-wazuh-verification.json) | Contesto manager readonly e diniego scrittura |
| [Overview](blue-team-wazuh-overview.png) / [Threat Hunting](blue-team-wazuh-events.png) | Login autenticato e dati consultabili |

Screenshot Overview: 403 sulle preferenze UI coerenti con readonly. Conteggi comprensivi di bootstrap/test, non tutti attacchi confermati. Esclusi state, piani, chiavi, credenziali, screenshot console amministrativa e log SSM integrali. Nessun nuovo deploy completo della copia Git.
