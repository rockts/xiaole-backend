import io
import subprocess
import sys
import unittest
from contextlib import redirect_stdout

from scripts.run_xiaole_reminder_acceptance import main


class AcceptanceScriptTests(unittest.TestCase):
    def test_default_is_dry_run_and_needs_no_credentials(self):
        output=io.StringIO()
        with redirect_stdout(output): code=main([])
        self.assertEqual(code,0)
        text=output.getvalue()
        self.assertIn('"mode":"dry-run"',text)
        self.assertIn('"source_system":"xiaole"',text)
        self.assertNotIn("token",text.lower())

    def test_script_is_runnable_from_repository_root(self):
        completed=subprocess.run([sys.executable,"scripts/run_xiaole_reminder_acceptance.py"],capture_output=True,text=True,check=False)
        self.assertEqual(completed.returncode,0,completed.stderr)
        self.assertIn('"mode":"dry-run"',completed.stdout)


if __name__ == "__main__": unittest.main()
