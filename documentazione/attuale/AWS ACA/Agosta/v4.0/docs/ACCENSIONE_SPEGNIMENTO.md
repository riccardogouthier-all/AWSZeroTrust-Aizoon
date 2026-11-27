# Switch EC2

Eseguire nel workspace dell'operatore con profilo AWS, dipendenze installate e evidence/outputs.json dello state corretto. Il clone Git non include gli ID del deploy privato.

```powershell
.\lab.ps1 status
.\lab.ps1 stop
.\lab.ps1 start
# Singolo ruolo: waf, web, siem
.\lab.ps1 stop -Role waf
.\lab.ps1 start -Role waf
# Solo verifica dei permessi
.\lab.ps1 stop -DryRun
```

Equivalenti Python: `python lab.py status|stop|start`, con `--role waf` e `--dry-run`. Il wrapper usa .venv locale oppure python nel PATH. Sul PC del titolare i comandi sono installati anche nel workspace privato AWS-Personale-Aizoon/2026-11-13.

## Semantica

- Solo EC2 EBS-backed degli output, con account/regione/Project/Role verificati.
- Stop ordinario, niente Force/SkipOsShutdown/Terminate/destroy. Già accesa/ferma: no-op; stato transitorio: attendere e riprovare.
- Start rifiutato se il consumo mensile rilevato ha raggiunto il budget o i dati non sono disponibili. Non annulla i ritardi di fatturazione.
- Richieste asincrone: running non significa servizi pronti. Attendere WEB/Wazuh prima dei test.
- EBS, configurazioni, IP privati ed EIP restano; RAM e sessioni si perdono.
- Permessi richiesti: StartInstances/StopInstances, DescribeInstances, DescribeBudget. Profili Blue non ampliati.

| Risorse | Esito dello stop |
|---|---|
| Tre EC2 | Compute fermo, riavviabile |
| VPC/subnet/route/SG/IAM | Invariate; nessun on/off equivalente |
| NAT | Resta attivo e fatturato; nessuna cancellazione/ricreazione |
| EBS/EIP/S3/log/backup | Persistono e possono generare costi |
| Allarmi/piano Backup | Invariati; HTTPS ALARM durante stop previsto |

Validazione: 13 test unitari, stato reale e DryRun AWS start/stop; nessun ciclo reale forzato. [Persistenza EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-lifecycle.html) · [NAT/IPv4](https://aws.amazon.com/vpc/pricing/).
