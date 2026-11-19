# Snapshot Cyber v3.1

Regole ModSecurity e classificazioni Wazuh dal commit Finocchielli `868d1c1`. Input agenti, probe e test di telemetria dal commit `169a747`. Hash SHA-256 con newline LF in [provenienza](../docs/provenienza.json).

Su AWS l’adattatore deriva le classificazioni dal file originale e le applica al flusso JSON `modsec_audit.log`, come regole figlie dell’alert generico 100100 del lab.

Per il deploy completo usare `apply_cyber.py`. Per aggiornare soltanto le regole su un lab esistente usare `update_cyber_rules.py`. La [matrice delle sfide](../../../../Cyber%20CYS/Defence/Finocchielli/DIFESE-SFIDE.md) distingue telemetria e controlli applicativi.
