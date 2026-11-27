"""Offline safety checks for the operator helpers; all AWS calls are mocked."""
import ast
import base64
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zlib
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

with patch("boto3.Session"):
    import ops
    import lab
    import configure


class ToolsTests(unittest.TestCase):
    def test_web_egress_payload_starts_with_a_shebang(self):
        command = configure.payload("web", {}, verify_only=False)
        packed = command.split("base64.b64decode(", 1)[1].split(")", 1)[0]
        scripts = json.loads(zlib.decompress(base64.b64decode(ast.literal_eval(packed))))
        self.assertEqual(scripts["web-egress.sh"].splitlines()[0], "#!/usr/bin/env bash")

    def test_wrong_account_is_rejected(self):
        session = MagicMock()
        session.client.return_value.get_caller_identity.return_value = {"Account": "other"}
        with patch.object(ops, "SESSION", session), patch.object(ops, "outputs", return_value={"account_id": "expected"}):
            with self.assertRaises(RuntimeError):
                ops.checked_account()

    def test_existing_login_without_private_handoff_is_not_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory)
            session = MagicMock()
            with patch.object(lab, "SESSION", session), patch.object(lab, "checked_account", return_value="123456789012"), \
                 patch.object(lab, "secure_private", return_value=private), patch.object(lab, "send") as send:
                with self.assertRaises(RuntimeError):
                    lab.blue_init()
                session.client.return_value.create_login_profile.assert_not_called()
                session.client.return_value.update_login_profile.assert_not_called()
                send.assert_not_called()

    def test_new_login_resets_password_and_keeps_secrets_private(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / "private"
            private.mkdir()
            (root / "evidence").mkdir()
            (root / "provision_wazuh_blue.py").write_text("# fixture\n")
            session = MagicMock()
            class Missing(Exception):
                pass
            iam = session.client.return_value
            iam.exceptions.NoSuchEntityException = Missing
            iam.get_login_profile.side_effect = Missing
            def openssl(*args):
                if args[0] == "genpkey":
                    Path(args[-1]).write_text("fixture-key")
                    return b""
                return b"fixture-public-key" if args[0] == "pkey" else b"Fixture-Wazuh-Pass9!"
            result = json.dumps({"encrypted_password": "Y2lwaGVy", "verification": {"fixture": True}})
            output = io.StringIO()
            with patch.object(lab, "ROOT", root), patch.object(lab, "SESSION", session), \
                 patch.object(lab, "checked_account", return_value="123456789012"), \
                 patch.object(lab, "secure_private", return_value=private), patch.object(lab, "openssl", side_effect=openssl), \
                 patch.object(lab, "send", return_value="fixture-command"), patch.object(lab, "completed", return_value=result), \
                 contextlib.redirect_stdout(output):
                lab.blue_init()
            credentials = json.loads((private / "blue-team-credentials.json").read_text())
            self.assertTrue(iam.create_login_profile.call_args.kwargs["PasswordResetRequired"])
            self.assertNotIn(credentials["aws_initial_password"], output.getvalue())
            self.assertNotIn(credentials["wazuh_password"], output.getvalue())
            for path in (root / "evidence").iterdir():
                self.assertNotIn(credentials["aws_initial_password"], path.read_text())
                self.assertNotIn(credentials["wazuh_password"], path.read_text())


class PowerTests(unittest.TestCase):
    def setUp(self):
        self.state = {"account_id": "123456789012", "region": "us-east-1", "project": "fixture",
                      "instances": {role: {"id": "i-" + role} for role in ("waf", "web", "siem")}}
        self.hosts = [{"InstanceId": "i-" + role, "RootDeviceType": "ebs", "State": {"Name": "running"},
                       "Tags": [{"Key": "Project", "Value": "fixture"}, {"Key": "Role", "Value": role}]}
                      for role in ("waf", "web", "siem")]
        self.ec2, self.budgets, self.session = MagicMock(), MagicMock(), MagicMock()
        self.session.region_name = "us-east-1"
        self.session.client.side_effect = {"ec2": self.ec2, "budgets": self.budgets}.__getitem__
        self.ec2.describe_instances.return_value = {"Reservations": [{"Instances": self.hosts}]}
        self.budget = {"CostTypes": {"IncludeCredit": False, "IncludeRefund": False},
                       "BudgetLimit": {"Amount": "20", "Unit": "USD"},
                       "CalculatedSpend": {"ActualSpend": {"Amount": "1", "Unit": "USD"}}}
        self.budgets.describe_budget.return_value = {"Budget": self.budget}

    def run_power(self, command, **kwargs):
        with patch.object(lab, "SESSION", self.session), patch.object(lab, "outputs", return_value=self.state), \
             patch.object(lab, "checked_account", return_value="123456789012"), contextlib.redirect_stdout(io.StringIO()):
            lab.power(command, **kwargs)

    def test_stop_targets_only_running_instances_without_force(self):
        self.hosts[1]["State"]["Name"] = "stopped"
        self.run_power("stop")
        self.ec2.stop_instances.assert_called_once_with(InstanceIds=["i-waf", "i-siem"], DryRun=False)
        self.ec2.terminate_instances.assert_not_called()

    def test_single_role_only_targets_that_instance(self):
        self.ec2.describe_instances.return_value = {"Reservations": [{"Instances": [self.hosts[1]]}]}
        self.run_power("stop", role="web")
        self.ec2.stop_instances.assert_called_once_with(InstanceIds=["i-web"], DryRun=False)

    def test_start_checks_budget_and_targets_only_stopped_instances(self):
        self.hosts[1]["State"]["Name"] = "stopped"
        self.run_power("start")
        self.budgets.describe_budget.assert_called_once_with(AccountId="123456789012", BudgetName="fixture-cost-budget")
        self.ec2.start_instances.assert_called_once_with(InstanceIds=["i-web"], DryRun=False)

    def test_start_refuses_exhausted_budget(self):
        self.hosts[0]["State"]["Name"] = "stopped"
        self.budget["CalculatedSpend"]["ActualSpend"]["Amount"] = "20"
        with self.assertRaises(RuntimeError):
            self.run_power("start")
        self.ec2.start_instances.assert_not_called()

    def test_start_refuses_missing_budget_data(self):
        self.hosts[0]["State"]["Name"] = "stopped"
        self.budget.pop("CalculatedSpend")
        with self.assertRaises(RuntimeError):
            self.run_power("start")
        self.ec2.start_instances.assert_not_called()

    def test_wrong_project_or_transitional_state_never_changes_any_instance(self):
        for invalid in ("project", "state"):
            with self.subTest(invalid=invalid):
                self.hosts[2]["Tags"][0]["Value"] = "unrelated" if invalid == "project" else "fixture"
                self.hosts[2]["State"]["Name"] = "stopping" if invalid == "state" else "running"
                with self.assertRaises(RuntimeError):
                    self.run_power("stop")
                self.ec2.stop_instances.assert_not_called()

    def test_already_stopped_and_status_do_not_mutate(self):
        for host in self.hosts:
            host["State"]["Name"] = "stopped"
        self.run_power("stop")
        self.run_power("status")
        self.ec2.stop_instances.assert_not_called()
        self.ec2.start_instances.assert_not_called()

    def test_dry_run_requests_permission_check_only(self):
        self.ec2.stop_instances.side_effect = ClientError({"Error": {"Code": "DryRunOperation"}}, "StopInstances")
        self.run_power("stop", dry_run=True)
        self.ec2.stop_instances.assert_called_once_with(InstanceIds=["i-waf", "i-web", "i-siem"], DryRun=True)

    def test_wrong_region_is_rejected_before_ec2_call(self):
        self.session.region_name = "eu-west-1"
        with self.assertRaises(RuntimeError):
            self.run_power("stop")
        self.ec2.describe_instances.assert_not_called()

    def test_wrong_account_is_rejected_before_any_ec2_call(self):
        with patch.object(lab, "SESSION", self.session), patch.object(lab, "checked_account", side_effect=RuntimeError("Wrong account")):
            with self.assertRaises(RuntimeError):
                lab.power("stop")
        self.session.client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
