# Validazione Blue Team — 13 novembre 2026

| Perimetro | Esito |
|---|---|
| Contributo originale | 12 YAML parsati; template Jinja WAF/WEB validi come XML; tre input WAF, uno WEB |
| Host originale Blue | Cinque test offline passati, HTTP loopback saltato per Windows 10013 |
| Controller del deploy Cloud | Sei test fixture/HTTP passati; sonda reale 10001 correlata WAF/manager tramite adattatore |
| Account personale | Due agenti Active; login Wazuh readonly e Threat Hunting verificati; nessun bootstrap Ansible completo su VM dedicate |
| Limiti | Idempotenza runtime Ansible, carico intenso e nuova installazione dedicata non verificati |

```bash
python3 -B -m unittest discover -s tests -v
ansible-galaxy collection install -r requirements.yml
ansible-playbook -i inventory/vm.example.yml site.yml -e @settings.example.yml --syntax-check
ansible-playbook -i inventory/vm.example.yml verify.yml --syntax-check
```

Sintassi YAML/XML non equivale all'esecuzione dei moduli. Il primo host Blue non disponeva di Docker/Ansible/Terraform/Checkov eseguibili; i risultati successivi dell'account personale non retroattestano quel run. [Evidenze Cloud](../../../AWS%20ACA/Agosta/v3.1/docs/evidenze/README.md).

Per un nuovo collaudo: cloud-init done, versioni allineate, NTP, agenti Active, marker con stesso transaction ID, traffico normale 200, test di blocco con rollback, controllo CPU/RAM/disco/latenza e secondo run Ansible sulle sole VM dedicate.
