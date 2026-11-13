# Il lavoro Blue Team nel laboratorio aizoOn

Il nostro obiettivo è seguire una richiesta web dal suo ingresso nel laboratorio fino alla sua registrazione nel SIEM. Una pagina Juice Shop che risponde dimostra che l’applicazione è raggiungibile. Per dimostrare anche la copertura difensiva dobbiamo ritrovare sul manager Wazuh lo stesso evento osservato dal WAF.

## Il percorso di una richiesta

1. Il client contatta Nginx sul WAF. ModSecurity v3 ispeziona la richiesta con le regole OWASP CRS. Nella fase iniziale usiamo `DetectionOnly`: il motore registra le corrispondenze mentre il proxy inoltra la richiesta a Juice Shop.
2. Nginx registra l’accesso. Per le transazioni rilevanti ModSecurity produce anche un audit con la regola e l’identificatore della transazione. L’agente Wazuh sul WAF raccoglie questi file; quello sul nodo WEB raccoglie l’output del container dell’applicazione.
3. Il manager riceve gli eventi. Durante il collaudo consultiamo l’archivio per confermare la ricezione. La dashboard permette di verificare gli agenti connessi e consultare gli alert indicizzati. Una richiesta normale può comparire negli accessi senza produrre un alert.

## Cosa abbiamo preparato

Su Kali possiamo avviare WAF e backend con Compose. Usiamo `127.0.0.1:8088` per lasciare la 8080 a Burp. Lo script invia una richiesta innocua contrassegnata con un identificatore nuovo. La regola locale 10001 permette di riconoscerla nell’audit. Per tre VM Ubuntu dedicate abbiamo preparato ruoli Ansible per SIEM, proxy e agenti, più una verifica che confronta l’ID della transazione sul WAF e sul manager.

Su AWS il secondo tentativo Gouthier installa già i servizi tramite Terraform e cloud-init. Qui il nostro lavoro inizia controllando il completamento del bootstrap e lo stato dei due agenti. La regola 10001 appartiene al nostro laboratorio dedicato. Sullo stack Gouthier cerchiamo prima un marcatore nell’access log e nell’archivio centrale, poi scegliamo una transazione presente nell’audit e ne verifichiamo la consegna separatamente. La guida AWS ora contempla la configurazione del profilo CLI del Learner Lab.

## Cosa possiamo dimostrare al team

Il materiale Agosta documenta una precedente prova AWS con due agenti attivi e ritorno del WAF a DetectionOnly. Gouthier documenta i propri controlli statici per il secondo tentativo. Per il contributo Finocchielli sono stati verificati i file di configurazione e i test offline; la demo reale Kali e la verifica end-to-end sulle EC2 restano da eseguire.

Per la demo, Cloud conferma account, regione, CIDR autorizzati e istanze. Blue mostra prima la pagina su 8088 e il marker nell’audit locale. Nella prova completa mostra poi il record arrivato sul manager, l’agente di origine e l’ora UTC. Queste evidenze permettono a Red e Blue di concordare la successiva finestra di tuning. Nel report conserviamo digest, identificatori di prova ed esiti; credenziali e log integrali rimangono nell’ambiente del laboratorio.

I comandi per la demo sono nel [manuale operativo](RUNBOOK.md). Lo [stato della repository](AUDIT.md) e il [registro dei test](VALIDAZIONE.md) distinguono le prove già documentate da quelle ancora da effettuare.
