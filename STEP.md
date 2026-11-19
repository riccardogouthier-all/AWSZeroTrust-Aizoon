# Stato tecnico — 13 novembre 2026

Per lo stato corrente del 19 novembre, vedere il [README](README.md). Le verifiche sotto si riferiscono al deploy del 13 novembre.

Riferimento operativo: [Agosta v3.1](AWS%20ACA/Agosta/v3.1/README.md).

| Componente | Stato |
|---|---|
| VPC, routing, SG, NAT, tre EC2 | Distribuiti; WAF pubblico, WEB/SIEM privati |
| Juice Shop, ModSecurity/CRS, Wazuh | Operativi; due agenti Active; WAF finale DetectionOnly |
| Telemetria cyber | Regola 10001 e transaction ID coincidente tra WAF e manager |
| CloudWatch / Flow Logs | Metriche, 13 allarmi, SNS→SQS, Flow Logs S3 verificati |
| Backup personale | Recovery point COMPLETED; ripristino completo non provato |
| Blue Team | Lettura log con MFA; ruolo sudo WAF/SIEM separato; login Wazuh provato |
| Switch EC2 | Start/stop/status; 13 test unitari e DryRun AWS; nessun ciclo reale forzato |
| CI/CD | GitHub Actions con approvazione ancora da implementare |
| QA | Chromium/Firefox/WebKit, desktop/mobile viewport; dispositivi fisici non provati |

Da completare: primo login AWS/MFA del membro Blue, carico durante attacchi intensivi, ripristino completo sul conto personale e workflow approvato da un membro del gruppo.

Le prove Learner Lab del 12 novembre e quelle dell'account personale del 13 novembre sono ambienti distinti. Stato corrente e scadenza crediti vanno verificati via API, non dedotti dalle evidenze storiche.
