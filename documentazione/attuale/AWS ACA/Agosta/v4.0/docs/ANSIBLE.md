# Ansible su AWS

La proposta del professore richiede Terraform per rete e VM, Ansible per Juice Shop, ModSecurity e Wazuh, e un report Checkov per i due tipi di codice. Per il progetto di gruppo le risorse Azure sono sostituite dai corrispondenti servizi AWS.

| Componente | Configurazione adottata |
|---|---|
| WEB | Il playbook Cyber verificava un servizio già predisposto. Il nuovo playbook installa Docker e crea il container Juice Shop dal digest Terraform. Un WEB nuovo usa il bridge dedicato e applica il filtro egress prima di avviare il container. Un container preesistente viene verificato e preservato. |
| WAF | Ansible esegue il bootstrap AWS esistente e il monitor HTTPS. Conserva il container `aizoon-waf`, la CA privata e i percorsi usati da SSM. Il ruolo Cyber per VM dedicate usa invece un altro nome del container e un proprio certificato. |
| SIEM | Adotta le verifiche del ruolo Cyber su installazioni parziali e checksum dell’installer. Mantiene il percorso AWS necessario al provisioning dell’utente Blue Team e la regola padre 100100. |
| Agenti e regole | Bootstrap gestito da Ansible. Il passaggio `apply_cyber.py` distribuisce regole, template degli agenti e classificazioni dai file Git del team Cyber. Su AWS le classificazioni leggono anche il flusso di audit previsto dal lab. |

Il controller invia il playbook via SSM Run Command. Ansible gira localmente sulle EC2. Per la 4.0 ho scelto il modello già usato nel Learner Lab 2.0 per riusare ruoli IAM e nodi privati senza aggiungere un bucket di trasferimento. Il profilo Cyber su VM dedicate resta in [Finocchielli](../../../../Cyber%20CYS/Defence/Finocchielli/RUNBOOK.md).

Per un nuovo stack il profilo Ansible è predefinito. Prima di pianificare sullo state storico impostare `configure_with_ansible=false` per conservare lo user data originario. Per verificare lo stack in servizio usare `python configure.py --verify-only`. Per un’installazione da zero serve il SHA-256 dell’installer ufficiale Wazuh 4.14 revisionato e va verificata la versione attesa, 4.14.11 per il nuovo lab. I comandi di deploy sono nel [README](../README.md).

I risultati sull'intero repository sono in [Revisione Checkov](CHECKOV.md). Bootstrap integrale verificato su tre EC2 nuove con Wazuh 4.14.11. Sul WEB temporaneo il filtro ha mantenuto l'ingresso dal WAF e impedito l'egress del container prima e dopo un riavvio di Docker. Un test sul pacchetto SSM verifica lo shebang dello script usato da systemd.
