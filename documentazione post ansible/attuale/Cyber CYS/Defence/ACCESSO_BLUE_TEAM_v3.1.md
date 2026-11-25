# Accesso Blue Team — v3.1

**Francesco vi consegna le credenziali privatamente. Le password AWS e Wazuh sono diverse.**

L’utente AWS `blue-team` basta per consultare e modificare le difese. Per il collaudo, Francesco usa `blue-verifica` con lo stesso gruppo IAM e un proprio dispositivo MFA. In quel caso sostituisce `blue-team` con `blue-verifica` nei comandi e nel login Wazuh.

## 1. Console AWS

1. Apri [la console del laboratorio](https://515917620173.signin.aws.amazon.com/console/).
2. Utente: **`blue-team`**. Usa la **password AWS** ricevuta e cambiala al primo accesso.
3. In **Credenziali di sicurezza → Assegna dispositivo MFA**, scegli un'app Authenticator e chiama il dispositivo **`blue-team`**.
4. Esci dalla sessione usata per registrare il dispositivo. Rientra come `blue-team` e verifica che AWS chieda il codice MFA.
5. Seleziona **Virginia settentrionale (`us-east-1`)**.

I log sono in **CloudWatch → Log → Gruppi di log**. I Flow Logs sono nel bucket S3 `aizoon-personal-logs-515917620173`.

## 2. Dashboard Wazuh

Installa **AWS CLI 2.32+** e il **[plugin Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)** sul tuo PC.

Nel terminale esegui:

```powershell
aws login --profile blue-team --region us-east-1
aws sts get-caller-identity --profile blue-team
```

Completa il login nel browser con MFA. Se compare **Bad Request**, apri la console AWS in una finestra privata, rientra con MFA e usa `aws login --profile blue-team --region us-east-1 --remote`. Apri l’URL mostrato dalla CLI nella stessa finestra privata e incolla il codice nel terminale. Il profilo viene creato al termine del login.

Quando `get-caller-identity` restituisce l’ARN dell’utente `blue-team`, esegui:

```powershell
aws ssm start-session --profile blue-team --region us-east-1 --target i-05e152bb6ec353ac1 --document-name aizoon-personal-WazuhDashboard --parameters localPortNumber=8443
```

Quando il terminale mostra `Port 8443 opened`, lascialo aperto. Sullo stesso PC apri **[https://127.0.0.1:8443/](https://127.0.0.1:8443/)** e accedi con utente **`blue-team`** e **password Wazuh**.

Se la pagina è irraggiungibile, in un secondo PowerShell esegui `Test-NetConnection 127.0.0.1 -Port 8443`. Se `TcpTestSucceeded` è `False`, controlla il terminale del tunnel. Se il browser mostra un avviso sul certificato, verifica l’impronta con Francesco. Usa **Overview** per gli agenti e **Threat Hunting → Events** per gli eventi.

## 3. Per modificare le difese live

Dallo stesso profilo CLI autenticato con MFA, scegli il nodo:

```powershell
# WAF
aws ssm start-session --profile blue-team --region us-east-1 --target i-0fe2d9e03e1dbd54f --document-name SessionDocument-aizoon-personal-BlueDefence
# SIEM
aws ssm start-session --profile blue-team --region us-east-1 --target i-05e152bb6ec353ac1 --document-name SessionDocument-aizoon-personal-BlueDefence
```

La sessione apre Bash con `sudo` sul nodo scelto, viene registrata su CloudWatch e dura al massimo un’ora. Se la sessione era già aperta, chiudila e riaprila per usare Bash. La dashboard Wazuh resta in sola lettura.

[Comandi per la difesa live](../../AWS%20ACA/Agosta/v3.1/docs/DIFESA_LIVE.md).

**Se l'accesso è negato:** controlla MFA, regione e documento. Non inserire password nei log o su Git. Gli ID indicati sono quelli del lab del 13 novembre 2026; dopo una ricreazione chiedi i nuovi riferimenti.
