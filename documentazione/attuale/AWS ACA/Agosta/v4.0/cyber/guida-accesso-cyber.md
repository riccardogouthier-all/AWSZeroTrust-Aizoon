# Accesso al laboratorio Cyber — v4.0

I segnaposto tra doppie graffe sono definiti nel file `variabili.txt` (privato, escluso da Git): sostituirli con i valori omonimi prima di eseguire i comandi.

**{{REFERENTE}} vi consegna le credenziali privatamente. Le password AWS e Wazuh sono diverse.**

L’utente AWS `{{UTENTE_BLUE}}` basta per consultare e modificare le difese. Per il collaudo, {{REFERENTE}} usa `{{UTENTE_VERIFICA}}` con lo stesso gruppo IAM e un proprio dispositivo MFA. In quel caso sostituisce `{{UTENTE_BLUE}}` con `{{UTENTE_VERIFICA}}` nei comandi e nel login Wazuh.

## Red Team

Apri il sito del lab con l'IP fornito dal referente e installa la CA pubblica dei test per verificare HTTPS.

## 1. Console AWS

1. Apri [la console del laboratorio](https://{{AWS_ACCOUNT_ID}}.signin.aws.amazon.com/console/).
2. Utente: **`{{UTENTE_BLUE}}`**. Usa la **password AWS** ricevuta e cambiala al primo accesso.
3. In **Credenziali di sicurezza → Assegna dispositivo MFA**, scegli un'app Authenticator e chiama il dispositivo **`{{UTENTE_BLUE}}`**.
4. Esci dalla sessione usata per registrare il dispositivo. Rientra come `{{UTENTE_BLUE}}` e verifica che AWS chieda il codice MFA.
5. Seleziona **Virginia settentrionale (`us-east-1`)**.

I log sono in **CloudWatch → Log → Gruppi di log**. I Flow Logs sono nel bucket S3 `{{PREFISSO_RISORSE}}-logs-{{AWS_ACCOUNT_ID}}`.

## 2. Dashboard Wazuh

Installa **AWS CLI 2.32+** e il **[plugin Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)** sul tuo PC.

Nel terminale esegui:

```powershell
aws login --profile {{UTENTE_BLUE}} --region us-east-1
aws sts get-caller-identity --profile {{UTENTE_BLUE}}
```

Completa il login nel browser con MFA. Se compare **Bad Request**, apri la console AWS in una finestra privata, rientra con MFA e usa `aws login --profile {{UTENTE_BLUE}} --region us-east-1 --remote`. Apri l’URL mostrato dalla CLI nella stessa finestra privata e incolla il codice nel terminale. Il profilo viene creato al termine del login.

Quando `get-caller-identity` restituisce l’ARN dell’utente `{{UTENTE_BLUE}}`, esegui:

```powershell
aws ssm start-session --profile {{UTENTE_BLUE}} --region us-east-1 --target {{ID_SIEM}} --document-name {{PREFISSO_RISORSE}}-WazuhDashboard --parameters localPortNumber=8443
```

Quando il terminale mostra `Port 8443 opened`, lascialo aperto. Sullo stesso PC apri **[https://127.0.0.1:8443/](https://127.0.0.1:8443/)** e accedi con utente **`{{UTENTE_BLUE}}`** e **password Wazuh**.

Se la pagina è irraggiungibile, in un secondo PowerShell esegui `Test-NetConnection 127.0.0.1 -Port 8443`. Se `TcpTestSucceeded` è `False`, controlla il terminale del tunnel. Se il browser mostra un avviso sul certificato, verifica l’impronta con {{REFERENTE}}. Usa **Overview** per gli agenti e **Threat Hunting → Events** per gli eventi.

## 3. Per modificare le difese live

Dallo stesso profilo CLI autenticato con MFA, scegli il nodo:

```powershell
# WAF
aws ssm start-session --profile {{UTENTE_BLUE}} --region us-east-1 --target {{ID_WAF}} --document-name SessionDocument-{{PREFISSO_RISORSE}}-BlueDefence
# SIEM
aws ssm start-session --profile {{UTENTE_BLUE}} --region us-east-1 --target {{ID_SIEM}} --document-name SessionDocument-{{PREFISSO_RISORSE}}-BlueDefence
```

La sessione apre Bash con `sudo` sul nodo scelto, viene registrata su CloudWatch e dura al massimo un’ora. Se la sessione era già aperta, chiudila e riaprila per usare Bash. La dashboard Wazuh resta in sola lettura.

[Comandi per la difesa live](../docs/DIFESA_LIVE.md).

**Se l'accesso è negato:** controlla MFA, regione e documento. Non inserire password nei log o su Git. Chiedi account, regione e ID istanze del nuovo ambiente al referente.
