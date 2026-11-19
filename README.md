# AWS Zero Trust Lab

Lab didattico Red/Blue su AWS. nginx con ModSecurity e OWASP CRS espone Juice Shop. WEB e Wazuh sono in subnet privata, con gestione tramite SSM.

## Aggiornamento Cyber del 19 novembre 2026

Il commit `868d1c1` di Finocchielli aggiunge una matrice per 118 sfide, cinque regole ModSecurity (10011–10015) e sette classificazioni Wazuh (110211–110217), incluse le famiglie CRS SQLi e XSS. La v3.1 include i due file di regole nel bootstrap e offre un aggiornamento mirato per i nodi esistenti. In `DetectionOnly` le corrispondenze producono telemetria. Il collaudo applicativo resta distinto.

## Stato

| Area | Stato |
|---|---|
| AWS | VPC, WAF, WEB e SIEM distribuiti. Le tre EC2 risultano ferme al controllo del 19 novembre. |
| Regole Cyber | Integrate nel repository. Passati 23 test offline e il controllo di sintassi su 9 payload SSM. Applicazione AWS e correlazione WAF → Wazuh da verificare al prossimo avvio. |
| Monitoraggio e backup | CloudWatch, Flow Logs e recovery point WEB verificati nel deploy del 13 novembre. Ripristino completo sull’account personale da provare. |
| Blue Team | Wazuh in sola lettura verificato. Primo accesso console con MFA del membro da completare. |
| QA e CI/CD | Verificati Chromium, Firefox e WebKit con viewport desktop e mobile. Restano dispositivi fisici e GitHub Actions con approvazione. |

Al prossimo avvio, attendere WAF e SIEM online in SSM, applicare `python update_cyber_rules.py` dal workspace v3.1 con gli output dello stack e verificare la ricezione di un alert di prova.

- [Deploy e operazioni v3.1](AWS%20ACA/Agosta/v3.1/README.md)
- [Switch EC2](AWS%20ACA/Agosta/v3.1/docs/ACCENSIONE_SPEGNIMENTO.md)
- [Accessi Blue Team](Cyber%20CYS/Defence/ACCESSO_BLUE_TEAM_v3.1.md)
- [Matrice e collaudo delle difese](Cyber%20CYS/Defence/Finocchielli/DIFESE-SFIDE.md)
- [Specifica originale aizoOn](Proposta%20Laboratorio%20Integrato_Ottobre%202026_aizoOn.docx)
