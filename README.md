# AWS Zero Trust Lab

Lab didattico Red/Blue su AWS. nginx con ModSecurity e OWASP CRS espone Juice Shop. WEB e Wazuh sono in subnet privata, con gestione tramite SSM.

## Aggiornamento Cyber del 19 novembre 2026

Il commit `868d1c1` di Finocchielli aggiunge una matrice per 118 sfide, cinque regole ModSecurity (10011–10015) e sette classificazioni Wazuh (110211–110217), incluse le famiglie CRS SQLi e XSS. La v3.1 include i due file di regole nel bootstrap e offre un aggiornamento mirato per i nodi esistenti. In `DetectionOnly` le corrispondenze producono telemetria. Il collaudo applicativo resta distinto.

## Stato

| Area | Stato |
|---|---|
| AWS | WAF, WEB e SIEM avviati il 19 novembre. Controlli EC2 e homepage HTTPS OK. Budget a 35 USD mensili, stop automatico riarmato. |
| Regole Cyber | Applicate su AWS. Una richiesta sintetica ha prodotto il match 10011 sul WAF e l’alert 110213 in Wazuh. Restano da collaudare dal vivo le altre classificazioni. |
| Monitoraggio e backup | CloudWatch, Flow Logs e recovery point WEB verificati nel deploy del 13 novembre. Ripristino completo sull’account personale da provare. |
| Blue Team | Wazuh in sola lettura verificato. Primo accesso console con MFA del membro da completare. |
| QA e CI/CD | Verificati Chromium, Firefox e WebKit con viewport desktop e mobile. Restano dispositivi fisici e GitHub Actions con approvazione. |

- [Deploy e operazioni v3.1](AWS%20ACA/Agosta/v3.1/README.md)
- [Switch EC2](AWS%20ACA/Agosta/v3.1/docs/ACCENSIONE_SPEGNIMENTO.md)
- [Accessi Blue Team](Cyber%20CYS/Defence/ACCESSO_BLUE_TEAM_v3.1.md)
- [Matrice e collaudo delle difese](Cyber%20CYS/Defence/Finocchielli/DIFESE-SFIDE.md)
- [Specifica originale aizoOn](Proposta%20Laboratorio%20Integrato_Ottobre%202026_aizoOn.docx)

## Adattamenti e decisioni operative

- **Soglia concordata.** Budget da 20 a 35 USD prima dei crediti. Ho riarmato l’azione di stop già eseguita prima di accendere le EC2 e allineato il Terraform del workspace di deploy.
- **Adattamento scelto durante il collaudo.** Il WAF scrive i match in `modsec_audit.log`. Ho mantenuto il file Cyber originale e derivato per AWS le sette classificazioni dal flusso JSON, come regole figlie della 100100. Il filtro riconosce il percorso anche quando Wazuh antepone i dati dell’agente.
- **Collaudo scelto senza passaggio in blocco.** Ho usato un nome fittizio e correlato la richiesta tra WAF e Wazuh. `DetectionOnly` limita la verifica alla telemetria. La risposta HTTP 403 osservata non dimostra l’enforcement della regola.
