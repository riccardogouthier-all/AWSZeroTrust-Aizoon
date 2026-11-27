# State Terraform

`AWS ACA/Agosta/v4.0/backend` crea il bucket S3 dell'account, con versioning, accesso pubblico bloccato, cifratura e HTTPS obbligatorio. Lo state dell'ambiente usa `lab/terraform.tfstate` e il lock nativo S3. Backend e progetto usano la stessa versione del provider AWS nei rispettivi lockfile.

In un account nuovo, creare il backend con il profilo AWS e la regione previsti. Dalla cartella 4.0:

```powershell
terraform -chdir=backend init
terraform -chdir=backend plan "-var=region=us-east-1" "-out=bootstrap.tfplan"
terraform -chdir=backend apply bootstrap.tfplan
$bucket = terraform -chdir=backend output -raw bucket
terraform -chdir=project init "-backend-config=bucket=$bucket" "-backend-config=region=us-east-1"
```

Per spostare uno stack esistente, fermare gli apply concorrenti, salvare una copia privata dello state e verificare che il bucket appartenga allo stesso account e che la chiave sia vuota. Usare `init -migrate-state` con gli stessi parametri. Confrontare risorse e output completi con la copia originaria e verificare la lineage del backend contro l'oggetto in S3. Lo state del vecchio account non va caricato sul nuovo laboratorio.

Il collaudo del deploy GitHub Actions resta sospeso fino alla disponibilità del repository.
