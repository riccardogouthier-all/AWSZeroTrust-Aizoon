"""Create a web backup, recover it to an isolated VM, verify Juice Shop, clean up."""
import json
import time

from ops import ROOT, SESSION, SSM, outputs


def main():
    state = outputs()
    backup, ec2 = SESSION.client("backup"), SESSION.client("ec2")
    project = state["project"]
    record = {}
    file = ROOT / "evidence" / "backup-restore-test.json"
    if file.exists():
        previous = json.loads(file.read_text())
        if previous.get("security_group") and not previous.get("security_group_deleted"):
            raise RuntimeError("Previous restore resources need cleanup; preserve and inspect the local manifest")

    def save():
        file.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")

    job = backup.start_backup_job(BackupVaultName=state["backup_vault"],
        ResourceArn=state["instances"]["web"]["arn"], IamRoleArn=state["backup_role_arn"],
        Lifecycle={"DeleteAfterDays": 1})
    record["backup_job_id"] = job["BackupJobId"]
    save()
    deadline = time.monotonic() + 3600
    while True:
        job = backup.describe_backup_job(BackupJobId=record["backup_job_id"])
        if job["State"] == "COMPLETED":
            break
        if job["State"] not in {"CREATED", "PENDING", "RUNNING"}:
            raise RuntimeError(f"Backup {job['State']}: {job.get('StatusMessage')}")
        if time.monotonic() > deadline:
            raise TimeoutError(f"Backup still running; inspect {record['backup_job_id']}")
        print("Backup: " + job["State"], flush=True)
        time.sleep(30)
    record["recovery_point"] = job["RecoveryPointArn"]
    image = job["RecoveryPointArn"].rsplit("/", 1)[-1]
    details = ec2.describe_images(ImageIds=[image])["Images"][0]
    account = SESSION.client("sts").get_caller_identity()["Account"]
    if details["State"] != "available" or details["OwnerId"] != account or details["Public"]:
        raise RuntimeError("Expected an available private recovery image owned by this account")
    tags = [{"Key": "Project", "Value": project}, {"Key": "Role", "Value": "restore-test"}]
    try:
        record["security_group"] = ec2.create_security_group(GroupName=project + "-restore",
            Description="Temporary restore test; no inbound access", VpcId=state["vpc_id"],
            TagSpecifications=[{"ResourceType": "security-group", "Tags": tags}])["GroupId"]
        save()
        sg = record["security_group"]
        ec2.revoke_security_group_egress(GroupId=sg, IpPermissions=[{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        ec2.authorize_security_group_egress(GroupId=sg, IpPermissions=[{"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        result = ec2.run_instances(ImageId=image, InstanceType="t3.small", MinCount=1, MaxCount=1,
            SubnetId=state["private_subnet_id"], SecurityGroupIds=[sg],
            IamInstanceProfile={"Name": state["instance_profile"]}, EbsOptimized=True,
            MetadataOptions={"HttpTokens": "required", "HttpPutResponseHopLimit": 1},
            TagSpecifications=[{"ResourceType": "instance", "Tags": tags + [{"Key": "Name", "Value": project + "-restore"}]}])
        record["instance"] = result["Instances"][0]["InstanceId"]
        save()
        deadline = time.monotonic() + 900
        while True:
            nodes = SSM.describe_instance_information(Filters=[{"Key": "InstanceIds", "Values": [record["instance"]]}])["InstanceInformationList"]
            if any(node["PingStatus"] == "Online" for node in nodes):
                break
            if time.monotonic() > deadline:
                raise TimeoutError("Restored node did not become Online in SSM")
            time.sleep(15)
        command = SSM.send_command(InstanceIds=[record["instance"]], DocumentName="AWS-RunShellScript",
            Comment="Verify isolated Juice Shop recovery", Parameters={"commands": [
                "set -eu; curl -fsS http://127.0.0.1:3000/ -o /tmp/restore.html; grep -q 'Juice Shop' /tmp/restore.html; echo RESTORED_JUICE_SHOP_OK"
            ]})["Command"]["CommandId"]
        deadline = time.monotonic() + 180
        while True:
            try:
                result = SSM.get_command_invocation(CommandId=command, InstanceId=record["instance"])
            except SSM.exceptions.InvocationDoesNotExist:
                if time.monotonic() > deadline:
                    raise TimeoutError("Restore verification invocation unavailable")
                time.sleep(5)
                continue
            if result["Status"] not in {"Pending", "InProgress", "Delayed"}:
                break
            if time.monotonic() > deadline:
                raise TimeoutError("Restore verification did not finish")
            time.sleep(5)
        record["verification"] = {key: result.get(key) for key in ["Status", "StandardOutputContent", "StandardErrorContent"]}
        save()
        if result["Status"] != "Success" or "RESTORED_JUICE_SHOP_OK" not in result["StandardOutputContent"]:
            raise RuntimeError("Restored application verification failed; inspect the local result")
        print("RESTORED_JUICE_SHOP_OK", flush=True)
    finally:
        if record.get("instance"):
            ec2.terminate_instances(InstanceIds=[record["instance"]])
            ec2.get_waiter("instance_terminated").wait(InstanceIds=[record["instance"]], WaiterConfig={"Delay": 5, "MaxAttempts": 120})
            record["instance_terminated"] = True
            save()
        if record.get("security_group"):
            ec2.delete_security_group(GroupId=record["security_group"])
            record["security_group_deleted"] = True
            save()
    print("Temporary restore resources removed; backup expires according to its lifecycle")


if __name__ == "__main__":
    main()
