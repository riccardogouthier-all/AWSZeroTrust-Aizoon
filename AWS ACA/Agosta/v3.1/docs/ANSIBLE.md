# Ansible su AWS

La proposta del professore richiede Terraform per rete e VM, Ansible per Juice Shop, ModSecurity e Wazuh, e un report Checkov per i due tipi di codice. Per il progetto di gruppo le risorse Azure sono sostituite dai corrispondenti servizi AWS.

| Componente | Configurazione adottata |
|---|---|
| WEB | Il playbook Cyber verificava un servizio già predisposto. Il nuovo playbook installa Docker e crea il container Juice Shop dal digest Terraform. Se il container esiste, controlla immagine, stato e HTTP senza ricrearlo. |
| WAF | Ansible esegue il bootstrap AWS esistente e il monitor HTTPS. Conserva il container `aizoon-waf`, la CA privata e i percorsi usati da SSM. Il ruolo Cyber per VM dedicate usa invece un altro nome del container e un proprio certificato. |
| SIEM | Adotta le verifiche del ruolo Cyber su installazioni parziali e checksum dell’installer. Mantiene il percorso AWS necessario al provisioning dell’utente Blue Team e la regola padre 100100. |
| Agenti e regole | Bootstrap gestito da Ansible. Il passaggio `apply_cyber.py` distribuisce regole, template degli agenti e classificazioni dai file Git del team Cyber. Su AWS le classificazioni leggono anche il flusso di audit previsto dal lab. |

Il controller invia il playbook via SSM Run Command. Ansible gira localmente sulle EC2. Per la v3.1 ho scelto il modello già usato nel Learner Lab 2.0 per riusare ruoli IAM e nodi privati senza aggiungere un bucket di trasferimento. Il profilo Cyber su VM dedicate resta in [Finocchielli](../../../../Cyber%20CYS/Defence/Finocchielli/RUNBOOK.md).

Per un nuovo stack il profilo Ansible è predefinito. Prima di pianificare sullo state storico impostare `configure_with_ansible=false` per conservare lo user data originario. Per verificare lo stack in servizio usare `python configure.py --verify-only`. Per un’installazione da zero serve il SHA-256 dell’installer ufficiale Wazuh 4.14 revisionato e va verificata la patch 4.14.10. I comandi di deploy sono nel [README](../README.md).

## Checkov

Scansione statica del 19 novembre 2026 con Checkov 3.4.6. Zero esclusioni e zero errori di parsing.

| Ambito | Pass | Finding |
|---|---:|---:|
| Terraform v3.1 | 176 | 18 |
| Ansible v3.1 | 4 | 5 |
| Ansible Cyber | 7 | 3 |

Ansible segnala HTTP sul controllo WEB locale o privato (CKV2_ANSIBLE_1). TLS termina sul WAF. CKV2_ANSIBLE_3 segnala i blocchi privi di `rescue`. La v3.1 interrompe il play al primo errore. Un’installazione Wazuh parziale richiede diagnosi prima di riprovare.

I finding Terraform riguardano IAM (273, 355), sessioni SSM (112, 113), cifratura e retention CloudWatch (158, 338), cifratura SNS e Backup (26, 166), disponibilità (394), associazione SG (CKV2_AWS_5) e bucket log S3 (18, 21, 144, 145, CKV2_AWS_62). Sono da revisionare prima di un rilascio. La scansione statica non accerta i controlli AWS a runtime.

## Verifica sul lab esistente

Terraform `fmt` e `validate` passati. Sintassi Ansible passata. Ansible è stato installato sui tre nodi e il controllo SSM ha verificato Wazuh, risposta HTTP di Juice Shop e configurazione nginx. Il play WEB completo ha riconosciuto l’immagine già distribuita e ha chiuso con `changed=0` e `failed=0`. Ancora da collaudare il bootstrap integrale su tre EC2 nuove, incluso l’installer Wazuh.
