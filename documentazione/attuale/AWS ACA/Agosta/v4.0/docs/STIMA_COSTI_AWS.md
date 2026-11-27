# Stima AWS del laboratorio ACA–CYS

**Budget proposto: 150 USD al mese per le lezioni.** Se l'ambiente deve rimanere acceso 24/7, prevedere **250 USD al mese**. Tariffe AWS On-Demand in `us-east-1` (Virginia del Nord), rilevate il 27 novembre 2026. Importi in USD al netto delle imposte, prima di crediti e sconti.

## Dimensionamento

Un ambiente condiviso in una zona di disponibilità. WAF e WEB su due `t3.small`, SIEM Wazuh su `m7i-flex.large` (2 vCPU e 8 GiB). Tre volumi gp3 da 20, 20 e 50 GiB, un NAT Gateway, due IPv4 pubblici e backup incrementali ogni 6 ore con conservazione di 7 giorni. WAF ModSecurity e certificato della CA locale girano sul WAF EC2 e non comportano tariffe AWS WAF o AWS Private CA.

| Voce | Ipotesi di calcolo | Lezioni, 120 ore EC2 | Sempre acceso, 744 ore EC2 |
|---|---|---:|---:|
| EC2 Linux | 2 × 0,0208 + 0,09576 USD/ora | 16,48 | 102,20 |
| Volumi gp3 | 90 GiB × 0,08 USD/GiB-mese | 7,20 | 7,20 |
| NAT Gateway e IPv4 | 744 ore × (0,045 + 2 × 0,005) USD/ora | 40,92 | 40,92 |
| Dati NAT e Internet | 100 GB NAT × 0,045 + 100 GB in uscita × 0,09 USD, senza sottrarre la franchigia | 13,50 | 13,50 |
| AWS Backup | 160 GB-mese di snapshot a 0,05 USD, con 90 GB iniziali e 10 GB di variazioni al giorno per 7 giorni | 8,00 | 8,00 |
| CloudWatch, metriche e allarmi | Fino a 43 serie a 0,30 USD/mese, riproporzionate alle ore EC2, e 16 metriche di allarme a 0,10 USD/mese | 3,68 | 14,50 |
| CloudWatch Logs | 25 GB di ingestione a 0,50 USD/GB e 25 GB-mese di storage a 0,03 USD/GB-mese | 13,25 | 13,25 |
| Flow Logs e S3 | 25 GB consegnati a S3 a 0,25 USD/GB, 15 GB-mese di storage a 0,023 USD/GB-mese e 1 USD per richieste | 7,60 | 7,60 |
| Riserva operativa | Un restore di prova di breve durata e costi minori (es. SNS/SQS, crediti CPU T3) | 10,00 | 10,00 |
| **Stima mensile** | Totale su valori non arrotondati | **120,63** | **217,16** |
| **Budget mensile proposto** | Include margine sui volumi di log, rete e snapshot | **150** | **250** |

120 ore equivalgono a 15 sessioni da 8 ore. Il costo di NAT, IPv4, volumi e dati già archiviati continua quando si spengono le EC2. Entrambi gli scenari usano gli stessi volumi mensili di traffico e log per tenere un margine sulle prove. I volumi sono ipotesi di pianificazione.

## Budget per il periodo

| Scenario | 3 mesi | 6 mesi |
|---|---:|---:|
| Lezioni, 150 USD/mese | 450 USD | 900 USD |
| Accesso continuo, 250 USD/mese | 750 USD | 1.500 USD |

Se il SIEM richiedesse **4 vCPU e 8 GiB**, una `c7i-flex.xlarge` a 0,16958 USD/ora porterebbe lo scenario 24/7 a **272,08 USD/mese**. Per quella variante prevedere **300 USD/mese**. Il dimensionamento attuale conserva 2 vCPU e 8 GiB sulla base delle prove svolte.

Tariffe AWS consultate tramite [Price List API](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/using-price-list-query-api.html) e pagine [EC2](https://aws.amazon.com/ec2/pricing/on-demand/), [EBS](https://aws.amazon.com/ebs/pricing/), [VPC](https://aws.amazon.com/vpc/pricing/), [CloudWatch](https://aws.amazon.com/cloudwatch/pricing/), [S3](https://aws.amazon.com/s3/pricing/) e [AWS Backup](https://aws.amazon.com/backup/pricing/).
