"""Offline safety checks for the operator helpers; all AWS calls are mocked."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

with patch("boto3.Session"):
    import ops
    import lab


class ToolsTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
