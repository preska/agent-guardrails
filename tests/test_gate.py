import subprocess
import sys
import unittest
from pathlib import Path

from guard.gate import staged_violations
from tests.helpers import git, make_repo, write

CLEAN = "from decimal import Decimal\n\n\ndef total(x):\n    return Decimal(x)\n"


class GateTest(unittest.TestCase):
    def setUp(self):
        self.root = make_repo({"billing/invoice.py": CLEAN})

    def gate(self):
        return [(v.decision_id, v.path) for v in staged_violations(self.root)]

    def test_nothing_staged_passes(self):
        self.assertEqual(self.gate(), [])

    def test_a_staged_violation_is_found(self):
        write(self.root, "billing/invoice.py", CLEAN.replace("Decimal(x)", "float(x)"))
        git(self.root, "add", "billing/invoice.py")
        self.assertEqual(self.gate(), [("DEC-002", "billing/invoice.py")])

    def test_only_the_staged_copy_counts(self):
        # Stage the clean version, then break the working copy: the commit is clean.
        write(self.root, "billing/tax.py", CLEAN)
        git(self.root, "add", "billing/tax.py")
        write(self.root, "billing/tax.py", "import openai\n")
        self.assertEqual(self.gate(), [])
        # And the other way round: a staged violation fixed only in the working copy still fails.
        write(self.root, "billing/rates.py", "import openai\n")
        git(self.root, "add", "billing/rates.py")
        write(self.root, "billing/rates.py", CLEAN)
        self.assertEqual(self.gate(), [("DEC-001", "billing/rates.py")])

    def test_the_hook_blocks_a_real_commit(self):
        hooks = self.root / "hooks"
        hooks.mkdir()
        (hooks / "pre-commit").write_text(f"#!/bin/sh\nexec {sys.executable} -m guard gate\n")
        (hooks / "pre-commit").chmod(0o755)
        git(self.root, "config", "core.hooksPath", "hooks")
        write(self.root, "billing/invoice.py", CLEAN.replace("Decimal(x)", "float(x)"))
        git(self.root, "add", "billing/invoice.py")
        commit = subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-m", "float"],
            cwd=self.root, capture_output=True, text=True,
            env={"PYTHONPATH": str(Path(__file__).resolve().parent.parent),
                 "PATH": "/usr/bin:/bin", "HOME": str(self.root)},
        )
        self.assertEqual(commit.returncode, 1)
        self.assertIn("commit blocked", commit.stdout + commit.stderr)


if __name__ == "__main__":
    unittest.main()
