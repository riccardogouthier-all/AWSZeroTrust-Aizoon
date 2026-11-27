"""Check the age of completed EC2 recovery points for the current lab."""
from datetime import datetime, timedelta, timezone

from ops import SESSION, checked_account, outputs


if __name__ == "__main__":
    checked_account()
    config = outputs()
    backup = SESSION.client("backup")
    pages = backup.get_paginator("list_recovery_points_by_backup_vault").paginate(
        BackupVaultName=config["backup_vault"], ByResourceType="EC2",
    )
    latest = {}
    for page in pages:
        for point in page["RecoveryPoints"]:
            if point["Status"] == "COMPLETED":
                arn = point["ResourceArn"]
                created = point["CreationDate"]
                if arn not in latest or created > latest[arn]:
                    latest[arn] = created

    now = datetime.now(timezone.utc)
    within_rpo = []
    for role, instance in sorted(config["instances"].items()):
        arn = f"arn:aws:ec2:{config['region']}:{config['account_id']}:instance/{instance['id']}"
        age = now - latest[arn] if arn in latest else None
        compliant = age is not None and age <= timedelta(hours=12)
        within_rpo.append(compliant)
        print(f"{role}: {'OK' if compliant else 'RPO superato'}, ultimo backup {latest.get(arn, 'assente')}")
    raise SystemExit(0 if all(within_rpo) else 1)
