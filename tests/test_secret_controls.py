"""Test prevention with generated fake credentials, never production keys."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GITLEAKS = os.environ.get("GITLEAKS_BIN") or shutil.which("gitleaks")


class SecretControlsTests(unittest.TestCase):
    def test_local_env_files_are_ignored_but_template_is_not(self):
        for name in (".env", ".env.local", ".env.production", "nested/.env"):
            result = subprocess.run(["git", "check-ignore", "--no-index", name],
                                    cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 0, name)
        result = subprocess.run(["git", "check-ignore", "--no-index", ".env.example"],
                                cwd=ROOT, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("ORS_API_KEY=\n", (ROOT / ".env.example").read_text())

    @unittest.skipUnless(GITLEAKS, "Set GITLEAKS_BIN to run scanner integration tests")
    def test_scanner_rejects_current_and_staged_fake_keys_without_printing_them(self):
        fake = "synthetic-only-" + "0123456789abcdef" * 5
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
            commit = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                      "commit", "-q", "--allow-empty", "-m", "test fixture"]
            subprocess.run(commit, cwd=root, check=True)
            subprocess.run(["git", "checkout", "-q", "-b", "new-branch"], cwd=root, check=True)
            (root / "config.py").write_text('ORS_API_KEY = "' + fake + '"\n')
            subprocess.run(["git", "add", "config.py"], cwd=root, check=True)
            for mode in (["dir", "."], ["git", "--pre-commit", "--staged", "."]):
                result = subprocess.run([GITLEAKS, *mode, "--redact=100", "--no-banner",
                                         "--config", str(ROOT / ".gitleaks.toml")],
                                        cwd=root, capture_output=True, text=True)
                self.assertEqual(result.returncode, 1, "Scanner must reject fake key")
                self.assertNotIn(fake, result.stdout + result.stderr)
            subprocess.run(commit, cwd=root, check=True)
            (root / "config.py").write_text('import os\nkey = os.environ["ORS_API_KEY"]\n')
            subprocess.run(["git", "add", "config.py"], cwd=root, check=True)
            subprocess.run(commit, cwd=root, check=True)
            result = subprocess.run([GITLEAKS, "dir", ".", "--redact=100", "--no-banner",
                                     "--config", str(ROOT / ".gitleaks.toml")],
                                    cwd=root, capture_output=True)
            self.assertEqual(result.returncode, 0, "Environment lookup must pass")
            base = subprocess.check_output(["git", "merge-base", "main", "HEAD"],
                                           cwd=root, text=True).strip()
            result = subprocess.run([GITLEAKS, "git", ".", "--redact=100", "--no-banner",
                                     "--config", str(ROOT / ".gitleaks.toml"),
                                     "--log-opts=" + base + "..HEAD"],
                                    cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, "First push must scan intermediate commits")
            self.assertNotIn(fake, result.stdout + result.stderr)
