# Guida — accesso al lab Cyber

19 novembre 2026 · AWS us-east-1

I segnaposto tra doppie graffe sono definiti nel file `guida-accesso-cyber-variabili.txt`: sostituirli prima di eseguire i comandi.

## Red Team

Apri `https://{{IP_WAF}}/`. {{REFERENTE}} fornisce la CA pubblica del lab (`lab-ca.crt`) per verificare HTTPS. Per aprire l'applicazione non serve un utente AWS.

## Blue Team — console AWS (referente)

- Console: `https://{{AWS_ACCOUNT_ID}}.signin.aws.amazon.com/console/`
- Utente IAM: `{{UTENTE_BLUE}}`
- Password attuale: chiedila al referente che ha effettuato il primo accesso. AWS non la mostra. Se non è reperibile, {{REFERENTE}} deve autorizzare un reset.

Al primo accesso utile: Credenziali di sicurezza → Assegna dispositivo MFA → App Authenticator. Chiama il dispositivo `{{UTENTE_BLUE}}`, poi esci e rientra con MFA. Seleziona Virginia settentrionale (us-east-1). Per consultare i log: CloudWatch → Gruppi di log.

## Blue Team — dashboard Wazuh

Installa AWS CLI 2.32+ e il [plugin Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html). Dopo avere attivato MFA, nel terminale esegui:

```powershell
aws login --profile {{UTENTE_BLUE}}
aws ssm start-session --profile {{UTENTE_BLUE}} --region us-east-1 --target {{ID_SIEM}} --document-name {{PREFISSO_RISORSE}}-WazuhDashboard --parameters localPortNumber=8443
```

Lascia aperto il terminale e visita `https://localhost:8443`. Se il browser avvisa del certificato, verifica con {{REFERENTE}} l'impronta SHA-256: `{{SHA256_DASHBOARD}}`

- Utente Wazuh: `{{UTENTE_BLUE}}`
- Password Wazuh: `{{PASSWORD_WAZUH_BLUE}}`

Per gli eventi: Threat Hunting → Events.

## Blue Team — difesa live

Console AWS → Cambia ruolo. Account `{{AWS_ACCOUNT_ID}}`, ruolo `{{PREFISSO_RISORSE}}-BlueDefence`.

Systems Manager → Session Manager → Avvia sessione. Scegli WAF o SIEM e il documento `SessionDocument-{{PREFISSO_RISORSE}}-BlueDefence`. Shell con sudo, registrata e valida fino a un'ora.

## Solo per {{REFERENTE}} — riferimento storico

Password iniziale AWS archiviata: `{{PASSWORD_AWS_BLUE_STORICA}}`

L'identità IAM è già stata usata e il cambio iniziale non risulta più in sospeso. Questa password non è verificata come attuale e non va consegnata come password di accesso.
