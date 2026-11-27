# Blue-verifica — accesso e difesa live

I segnaposto tra doppie graffe sono definiti nel file `blue-verifica-variabili.txt`: sostituirli prima di eseguire i comandi.

## Console AWS

- Console: `https://{{AWS_ACCOUNT_ID}}.signin.aws.amazon.com/console/`
- Utente IAM: `{{UTENTE_VERIFICA}}`
- Password AWS iniziale (da cambiare): `{{PASSWORD_AWS_VERIFICA}}`

Apri la console in una finestra privata per separarla dalla tua sessione admin. Cambia la password, registra un dispositivo MFA con nome `{{UTENTE_VERIFICA}}`, esci e accedi di nuovo con MFA.

## Login da PowerShell

```powershell
$PROFILO=
aws login --profile {{UTENTE_VERIFICA}} --region us-east-1 --remote
aws sts get-caller-identity --profile {{UTENTE_VERIFICA}}
```

Apri l'URL del login nella finestra privata, scegli `{{UTENTE_VERIFICA}}` e incolla il codice nel terminale.

## Dashboard in sola lettura

```powershell
aws ssm start-session --profile {{UTENTE_VERIFICA}} --region us-east-1 --target {{ID_SIEM}} --document-name {{PREFISSO_RISORSE}}-WazuhDashboard --parameters localPortNumber=8443
```

Lascia aperto il tunnel e apri `https://127.0.0.1:8443/`.

- Utente Wazuh: `{{UTENTE_VERIFICA}}`
- Password Wazuh: `{{PASSWORD_WAZUH_VERIFICA}}`
- Impronta SHA-256 dashboard: `{{SHA256_DASHBOARD}}`

## Difesa live

Sullo stesso profilo, in un altro terminale:

```powershell
# WAF
aws ssm start-session --profile {{UTENTE_VERIFICA}} --region us-east-1 --target {{ID_WAF}} --document-name SessionDocument-{{PREFISSO_RISORSE}}-BlueDefence
# SIEM
aws ssm start-session --profile {{UTENTE_VERIFICA}} --region us-east-1 --target {{ID_SIEM}} --document-name SessionDocument-{{PREFISSO_RISORSE}}-BlueDefence
```

Per verificare il privilegio senza cambiare configurazioni: `sudo -n id`
