import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

os.environ.update(AWS_ACCESS_KEY_ID="testing", AWS_SECRET_ACCESS_KEY="testing", AWS_EC2_METADATA_DISABLED="true")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from botocore.exceptions import ClientError
from jinja2 import Environment, StrictUndefined
import yaml

import backup_test
from bootstrap import ensure_bucket
from configure import render_playbook
import ops


class ReplicationTests(unittest.TestCase):
    def test_bucket_denied_does_not_modify_foreign_or_inaccessible_bucket(self):
        s3 = MagicMock()
        s3.head_bucket.side_effect = ClientError({"Error": {"Code": "403"}}, "HeadBucket")
        with self.assertRaises(ClientError):
            ensure_bucket(s3, "example-bucket", "123456789012", "us-east-1")
        s3.create_bucket.assert_not_called()
        s3.put_public_access_block.assert_not_called()

    def test_bucket_creation_uses_region_and_enables_versioning(self):
        s3 = MagicMock()
        s3.head_bucket.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadBucket")
        ensure_bucket(s3, "example-bucket", "123456789012", "us-west-2", versioned=True)
        s3.create_bucket.assert_called_once_with(Bucket="example-bucket", CreateBucketConfiguration={"LocationConstraint": "us-west-2"})
        s3.head_bucket.assert_called_once_with(Bucket="example-bucket", ExpectedBucketOwner="123456789012")
        s3.put_bucket_versioning.assert_called_once()

    def test_bucket_in_another_region_is_not_reconfigured(self):
        s3 = MagicMock()
        s3.get_bucket_location.return_value = {"LocationConstraint": "us-west-2"}
        with self.assertRaisesRegex(RuntimeError, "region"):
            ensure_bucket(s3, "example-bucket", "123456789012", "us-east-1")
        s3.put_public_access_block.assert_not_called()

    def test_all_playbooks_render_with_new_environment_and_valid_embedded_python(self):
        state = {"region": "us-west-2", "project": "replication-test", "waf_ip": "203.0.113.10",
                 "instances": {"web": {"private_ip": "10.20.2.10"}, "siem": {"private_ip": "10.20.2.20"}}}
        images = json.loads((ops.ROOT / "images.lock.json").read_text())
        for path in (ops.ROOT / "configuration").glob("*.yml"):
            rendered = render_playbook(path.read_text(), "waf", state, images)
            self.assertNotIn("LAB_", rendered)
            self.assertNotIn("aizoon-private-test", rendered)
            rendered = Environment(undefined=StrictUndefined).from_string(rendered).render()
            data = yaml.safe_load(rendered)
            self.assertIsInstance(data, list)
            for task in data[0]["tasks"]:
                copy = task.get("ansible.builtin.copy", {})
                if copy.get("dest", "").endswith(".py"):
                    compile(copy["content"], str(path), "exec")

    def test_ssm_failure_prevents_following_configuration(self):
        with patch.object(ops, "SSM") as ssm, patch.object(ops, "outputs", return_value={"instances": {"web": {"id": "i-test"}}}), patch.object(ops, "poll"):
            ssm.get_command_invocation.return_value = {"Status": "Failed"}
            with self.assertRaisesRegex(RuntimeError, "Failed"):
                ops.wait("web", "example-command")

    def test_restore_verification_failure_still_cleans_owned_temporary_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "evidence").mkdir()
            backup, ec2, sts, ssm = (MagicMock() for _ in range(4))
            backup.start_backup_job.return_value = {"BackupJobId": "job-test"}
            backup.describe_backup_job.return_value = {"State": "COMPLETED", "RecoveryPointArn": "arn:aws:ec2:us-east-1::image/ami-test"}
            ec2.describe_images.return_value = {"Images": [{"State": "available", "OwnerId": "123456789012", "Public": False}]}
            ec2.create_security_group.return_value = {"GroupId": "sg-test"}
            ec2.run_instances.return_value = {"Instances": [{"InstanceId": "i-test"}]}
            sts.get_caller_identity.return_value = {"Account": "123456789012"}
            ssm.describe_instance_information.return_value = {"InstanceInformationList": [{"PingStatus": "Online"}]}
            ssm.send_command.return_value = {"Command": {"CommandId": "cmd-test"}}
            ssm.get_command_invocation.return_value = {"Status": "Failed", "StandardOutputContent": "", "StandardErrorContent": "Application unavailable"}
            state = {"project": "test-lab", "backup_vault": "test-vault", "backup_role_arn": "arn:aws:iam::123456789012:role/LabRole",
                     "vpc_id": "vpc-test", "private_subnet_id": "subnet-test", "instance_profile": "LabInstanceProfile",
                     "instances": {"web": {"arn": "arn:aws:ec2:us-east-1:123456789012:instance/i-web"}}}
            with patch.object(backup_test, "ROOT", root), patch.object(backup_test, "outputs", return_value=state), patch.object(backup_test, "SSM", ssm), patch.object(backup_test, "SESSION") as session:
                session.client.side_effect = lambda name: {"backup": backup, "ec2": ec2, "sts": sts}[name]
                with self.assertRaisesRegex(RuntimeError, "verification failed"):
                    backup_test.main()
            ec2.terminate_instances.assert_called_once_with(InstanceIds=["i-test"])
            ec2.delete_security_group.assert_called_once_with(GroupId="sg-test")
            self.assertTrue(json.loads((root / "evidence/backup-restore-test.json").read_text())["security_group_deleted"])


if __name__ == "__main__":
    unittest.main()
