# Accesso Blue Team

**Francesco vi consegna le credenziali privatamente. Le password AWS e Wazuh sono diverse.**

## 1. Console AWS

1. Apri [la console del laboratorio](https://515917620173.signin.aws.amazon.com/console/).
2. Utente: **`blue-team`**. Usa la **password AWS** ricevuta e cambiala al primo accesso.
3. In **Credenziali di sicurezza → Assegna dispositivo MFA**, scegli un'app Authenticator e chiama il dispositivo **`blue-team`**.
4. Esci e rientra con password e MFA.
5. Seleziona **Virginia settentrionale (`us-east-1`)**.

I log sono in **CloudWatch → Log → Gruppi di log**. I Flow Logs sono nel bucket S3 `aizoon-personal-logs-515917620173`.

## 2. Dashboard Wazuh

Installa **AWS CLI 2.32+** e il **[plugin Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)** sul tuo PC.

Nel terminale esegui:

```powershell
aws login --profile blue-team
```

Completa il login AWS nel browser con MFA; se chiede la regione inserisci `us-east-1`. Poi esegui:

```powershell
aws ssm start-session --profile blue-team --region us-east-1 --target i-05e152bb6ec353ac1 --document-name aizoon-personal-WazuhDashboard --parameters localPortNumber=8443
```

**Lascia il terminale aperto**, visita **https://localhost:8443** e accedi con utente **`blue-team`** e **password Wazuh**.

La CA è privata: chiedi a Francesco la verifica del certificato. Usa **Overview** per gli agenti e **Threat Hunting → Events** per gli eventi.

## 3. Per modificare le difese live

Nella console AWS scegli **Cambia ruolo / Switch role**:

- Account: **`515917620173`**.
- Ruolo: **`aizoon-personal-BlueDefence`**.

Poi apri **Systems Manager → Session Manager → Avvia sessione**, scegli **WAF o SIEM** e il documento **`SessionDocument-aizoon-personal-BlueDefence`**. Avrai una shell con `sudo`, registrata, per massimo un'ora.

[Comandi per la difesa live](../../AWS%20ACA/Agosta/v3/docs/DIFESA_LIVE.md).

**Se l'accesso è negato:** controlla MFA, regione e documento. Non inserire password nei log o su Git. Gli ID indicati sono quelli del lab del 13 novembre 2026; dopo una ricreazione chiedi i nuovi riferimenti.
