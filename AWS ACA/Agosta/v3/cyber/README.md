# Componenti del Blue Team utilizzati nella v3

Questa cartella conserva soltanto i cinque file necessari all'adattatore e ai suoi test, copiati senza modifiche da `Cyber CYS/Defence/Finocchielli` al commit `169a747`:

- `files/REQUEST-900-BLUE-TEAM.conf`: regola di integrazione 10001.
- `roles/agents/templates/inputs.xml.j2`: sorgenti di log degli agenti.
- `tools/check_evidence.py` e `tools/probe.py`: sonda e correlazione delle transazioni.
- `tests/test_telemetry.py`: test originali della telemetria.

I playbook completi del contributo restano nella cartella originale del team cyber. La v3 configura le VM con cloud-init e adotta questi file tramite `apply_cyber.py`, senza avviare un secondo stack Ansible o reinstallare Wazuh.

Le modifiche future del contributo non vengono copiate automaticamente qui: confrontare le configurazioni e ripetere i test prima di aggiornare la versione.
