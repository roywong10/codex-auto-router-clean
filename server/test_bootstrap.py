"""Offline bootstrap boundaries; no installer or service manager is executed."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
REMOTE = "https://github.com/roywong10/codex-auto-router.git"


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source with spaces"
        self.source.mkdir()
        self.commands = self.root / "bin"
        self.commands.mkdir()
        self.trace = self.root / "git-trace"
        git = self.commands / "git"
        git.write_text("""#!/bin/sh
printf '%s\\n' "$*" >> "$TEST_GIT_TRACE"
case "$*" in
  *rev-parse*) exit 0 ;;
  *remote*) printf '%s\\n' "$TEST_ORIGIN" ;;
  *status*) printf '%s' "${TEST_DIRTY:-}" ;;
  *fetch*|*merge*) exit "${TEST_GIT_FAILURE:-0}" ;;
  clone*)
    for destination do :; done
    mkdir -p "$destination"
    cp "$TEST_INSTALLER" "$destination/install.sh"
    ;;
  *) exit 91 ;;
esac
""")
        git.chmod(0o700)
        installer = self.source / "install.sh"
        installer.write_text('#!/bin/sh\nprintf "installer:%s\\n" "$*"\n')
        installer.chmod(0o700)
        self.env = {
            **os.environ,
            "PATH": str(self.commands) + os.pathsep + os.environ["PATH"],
            "HOME": str(self.root),
            "JEV_ROUTER_SOURCE_DIR": str(self.source),
            "TEST_GIT_TRACE": str(self.trace),
            "TEST_ORIGIN": REMOTE,
            "TEST_INSTALLER": str(installer),
        }

    def run_bootstrap(self, *args):
        return subprocess.run(
            ["sh", str(ROOT / "scripts/bootstrap.sh"), *args],
            env=self.env, text=True, capture_output=True, check=False,
        )

    def test_clean_distribution_checkout_updates_and_forwards_prepare_flag(self):
        for remote in (REMOTE, "git@github.com:roywong10/codex-auto-router.git"):
            with self.subTest(remote=remote):
                self.env["TEST_ORIGIN"] = remote
                result = self.run_bootstrap("--prepare-only")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), "installer:--prepare-only")
                self.assertIn("merge --ff-only --quiet origin/main", self.trace.read_text())

    def test_other_remote_is_not_updated(self):
        self.env["TEST_ORIGIN"] = "https://github.com/example/other.git"
        result = self.run_bootstrap("--prepare-only")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("different remote", result.stderr)
        self.assertNotIn("fetch", self.trace.read_text())
        self.assertNotIn("installer:", result.stdout)

    def test_dirty_checkout_is_not_updated(self):
        self.env["TEST_DIRTY"] = " M README.md"
        result = self.run_bootstrap("--prepare-only")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("local changes", result.stderr)
        self.assertNotIn("fetch", self.trace.read_text())

    def test_update_command_uses_its_own_checkout(self):
        (self.source / "bin").mkdir()
        (self.source / "scripts").mkdir()
        shutil.copy2(ROOT / "bin/jev-codex-router", self.source / "bin/jev-codex-router")
        shutil.copy2(ROOT / "scripts/bootstrap.sh", self.source / "scripts/bootstrap.sh")
        self.env["JEV_ROUTER_SOURCE_DIR"] = str(self.root / "must-not-use")
        result = subprocess.run(
            ["sh", str(self.source / "bin/jev-codex-router"), "update", "--prepare-only"],
            env=self.env, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "installer:--prepare-only")
        self.assertFalse((self.root / "must-not-use").exists())

    def test_invalid_arguments_stop_before_git(self):
        for args in (("--unknown",), ("--prepare-only", "unexpected")):
            with self.subTest(args=args):
                result = self.run_bootstrap(*args)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(self.trace.exists())

    def test_fresh_bootstrap_clones_distribution_into_default_path(self):
        self.env.pop("JEV_ROUTER_SOURCE_DIR")
        result = self.run_bootstrap("--prepare-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "installer:--prepare-only")
        source = self.root / ".local/share/codex-auto-router-source"
        self.assertTrue((source / "install.sh").exists())
        self.assertIn(f"clone --quiet --depth 1 --branch main {REMOTE}", self.trace.read_text())

    def test_fetch_failure_never_runs_installer(self):
        self.env["TEST_GIT_FAILURE"] = "17"
        result = self.run_bootstrap("--prepare-only")
        self.assertEqual(result.returncode, 17)
        self.assertNotIn("merge", self.trace.read_text())
        self.assertNotIn("installer:", result.stdout)


if __name__ == "__main__":
    unittest.main()
