# Evidenze selezionate

Risultati del laboratorio eseguito il 13 novembre 2026, conservati senza credenziali, state o log SSM integrali.

- [Riepilogo verifiche live](validazione.json).
- [Controlli del pacchetto Git](controlli_pacchetto.json): distinti dal deploy storico.
- [Test browser](browser-results.json): tre motori e viewport desktop/mobile; screenshot nella stessa cartella.
- [WAF 200/403 e ritorno a DetectionOnly](waf-test-results.json).
- [Transazione correlata WAF/manager](cyber-transaction.json).
- [Backup reale completato](backup-status.json): identificativi operativi rimossi.
- [Ruolo Wazuh readonly](blue-team-wazuh-verification.json).
- [Overview Wazuh](blue-team-wazuh-overview.png) e [Threat Hunting](blue-team-wazuh-events.png).

Gli avvisi 403 sulle preferenze UI nella schermata Overview sono coerenti con il profilo in lettura: non sono stati concessi permessi di scrittura per nasconderli. I conteggi includono bootstrap, test e attività del laboratorio; non rappresentano attacchi tutti confermati. Non sono inclusi gli screenshot della console amministrativa AWS, certificati/chiavi del deploy, piani Terraform o output SSM completi.
