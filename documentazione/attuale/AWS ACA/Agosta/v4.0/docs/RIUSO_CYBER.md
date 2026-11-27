# Riuso delle configurazioni Cyber nella 4.0

La 4.0 usa le configurazioni difensive di Finocchielli, ma adotta solo una parte del pacchetto Cyber nel deploy AWS. Le sei copie in `v4.0/cyber/` sono quelle già revisionate per la 3.1. La [provenienza 3.1](../../v3.1/docs/provenienza.json) riporta gli hash con newline LF.

| Materiale Cyber | Uso nella 4.0 |
|---|---|
| Regole ModSecurity 10001 e 10011–10015 | Copia originale caricata sul WAF tramite SSM. |
| Template degli input Wazuh | Copia originale renderizzata per WAF e WEB. Sul WEB l’adattatore risolve il percorso effettivo dei log Docker. |
| Classificazioni Wazuh 110211–110217 | XML originale conservato. Per AWS l’adattatore deriva le regole dal log di audit JSON e le collega alla regola padre 100100. Gli ID Cyber restano gli stessi. |
| `probe.py`, `check_evidence.py`, `test_telemetry.py` | Copie originali per sonda, correlazione e test. L’adattatore distribuisce `check_evidence.py` sui nodi. |
| Ruoli Ansible, inventari, Compose, matrice e strumenti delle sfide | Restano nel [pacchetto Cyber](../../../../Cyber%20CYS/Defence/Finocchielli/README.md). Compose e ruoli Ansible servono al profilo su VM dedicate. Matrice e strumenti servono al collaudo, fuori dal deploy AWS. |

## Aggiunte e adattamenti Cloud

- **Mancava il deploy WEB.** Il playbook Cyber controlla Juice Shop già installato. La 4.0 aggiunge installazione Docker e avvio del container da immagine fissata con digest.
- **Trasporto e bootstrap AWS.** Ansible gira sulle EC2 tramite SSM Run Command. Ho scelto questa modalità per riusare IAM e nodo privato. Il playbook mantiene nome del proxy, CA, percorsi Wazuh e monitor HTTPS usati dal lab. Per il SIEM riprende dal ruolo Cyber i controlli su installazione incompleta e checksum dell’installer.

**Verificato:** Ansible sulle tre EC2 esistenti, play WEB con zero modifiche e alert 110213 osservato. **Da verificare:** bootstrap completo su EC2 nuove e le altre classificazioni dal vivo. [Report Ansible e Checkov](ANSIBLE.md)
