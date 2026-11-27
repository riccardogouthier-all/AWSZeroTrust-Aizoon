# State Terraform

`AWS ACA/Agosta/v3.1/backend` crea il bucket S3 dell'account, con versioning, accesso pubblico bloccato, cifratura e HTTPS obbligatorio. Lo state dell'ambiente usa `lab/terraform.tfstate` e il lock nativo S3.

In un account nuovo, creare il backend con il profilo AWS e la regione previsti. Dalla cartella v3.1:

```powershell
terraform -chdir=backend init
terraform -chdir=backend plan "-var=region=us-east-1" "-out=bootstrap.tfplan"
terraform -chdir=backend apply bootstrap.tfplan
$bucket = terraform -chdir=backend output -raw bucket
terraform -chdir=project init "-backend-config=bucket=$bucket" "-backend-config=region=us-east-1"
```

Per spostare uno stack esistente, fermare gli apply concorrenti, salvare una copia privata dello state e verificare che il bucket appartenga allo stesso account e che la chiave sia vuota. Usare `init -migrate-state` con gli stessi parametri. Confrontare risorse e output completi con la copia originaria e verificare la lineage del backend contro l'oggetto in S3. Lo state del vecchio account non va caricato sul nuovo laboratorio.

## GitHub Actions

Il proprietario del repository configura l'environment `aws-lab` con un revisore del gruppo, divieto di autoapprovazione e deploy solo da `main`. Verificare che un avvio manuale resti in attesa del revisore prima di collegare il ruolo AWS.

Impostare nell'environment `AWS_REGION`, `AWS_ACCOUNT_ID`, `TF_BACKEND_BUCKET`, `AWS_DEPLOY_ROLE_ARN` e `CONFIGURE_WITH_ANSIBLE`. Per un nuovo stack usare `true` e fornire `WAZUH_VERSION` e `WAZUH_INSTALLER_SHA256` dell'installer revisionato. Per lo stack avviato con cloud-init usare `false` per evitare sostituzioni.

Configurare il ruolo OIDC in AWS con audience `sts.amazonaws.com` e subject esatto `repo:riccardogouthier-all/AWSZeroTrust-Aizoon:environment:aws-lab`. Limitare il ruolo alle risorse del lab e alla chiave S3 dello state con relativo lock. Il workflow rifiuta piani con eliminazioni o sostituzioni, poi avvia Ansible se abilitato. Inizializzare gli account Blue Team separatamente, come indicato nel [README](../README.md).
