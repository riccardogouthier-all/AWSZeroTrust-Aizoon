# AWS Lab v3 — archivio

Release originale: `b729167`. Terraform, cloud-init, adattatore Cyber, IAM Blue Team e controlli del deploy personale del 13/11/2026.

La [v3.1](../v3.1/README.md) contiene lo switch EC2 e la documentazione operativa corrente. Il codice v3 resta invariato; non include `start`, `stop` o `status`.

- [Report del deploy](docs/report_deploy_2026-11-13.md)
- [Evidenze](docs/evidenze/README.md)
- [Snapshot Cyber](cyber/README.md)
- [Accessi Blue Team](../../../Cyber%20CYS/Defence/ACCESSO_BLUE_TEAM_v3.1.md)

Per riprendere il deploy esistente serve lo state privato originale. Non applicare uno state vuoto nello stesso account. Segreti, state e output runtime sono esclusi da Git.
