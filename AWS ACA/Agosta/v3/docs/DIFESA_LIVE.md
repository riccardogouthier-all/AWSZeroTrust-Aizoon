# Difesa live — v3

Accesso tramite ruolo MFA `aizoon-personal-BlueDefence`, solo WAF/SIEM, sessione SSM registrata con `sudo`, massimo un'ora. Documento: `SessionDocument-aizoon-personal-BlueDefence`.

Le procedure compatibili con questo deploy sono nella [guida corrente](../../v3.1/docs/DIFESA_LIVE.md): modalità ModSecurity, regole locali, log e archivi Wazuh. Prima di modificare le difese concordare la finestra con Red Team; mantenere il rollback.

Il ruolo Blue non può amministrare IAM, fatturazione o ciclo di vita EC2. Lo switch operatore è stato aggiunto nella v3.1.
