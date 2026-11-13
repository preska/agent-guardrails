import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from guard.checker import find_violations
from guard.decisions import load_decisions
from guard.sarif import annotation, to_sarif
from tests.helpers import make_repo

REPO = Path(__file__).resolve().parent.parent


class SarifTest(unittest.TestCase):
    def setUp(self):
        self.root = make_repo({"billing/invoice.py": "x = float(y)\nprint(x)\n"})
        self.decisions = load_decisions(self.root)
        self.found = find_violations("x = float(y)\nprint(x)\n", "billing/invoice.py", self.decisions)

    def test_sarif_shape(self):
        log = json.loads(to_sarif(self.found, self.decisions))
        self.assertEqual(log["version"], "2.1.0")
        run = log["runs"][0]
        self.assertEqual([r["id"] for r in run["tool"]["driver"]["rules"]], ["DEC-001", "DEC-002", "DEC-003"])
        first = run["results"][0]
        self.assertEqual((first["ruleId"], first["level"]), ("DEC-002", "error"))
        region = first["locations"][0]["physicalLocation"]["region"]
        self.assertEqual((region["startLine"], region["startColumn"]), (1, 5))
        self.assertEqual(run["results"][1]["level"], "warning")
        self.assertIn("guardFingerprint/v1", first["partialFingerprints"])

    def test_annotation_escapes_github_syntax(self):
        by_id = {d.id: d for d in self.decisions}
        line = annotation(self.found[0], by_id["DEC-002"])
        self.assertTrue(line.startswith("::error file=billing/invoice.py,line=1,col=5,title=DEC-002 Money"))
        self.assertEqual(line.count("::"), 2)
        self.assertNotIn("\n", line)

    def test_ci_command_on_this_repo(self):
        # The repo's own baseline covers the examples' existing violations.
        env = {**os.environ, "GITHUB_ACTIONS": "true", "PYTHONPATH": str(REPO)}
        run = subprocess.run([sys.executable, "-m", "guard", "ci"], cwd=REPO,
                             capture_output=True, text=True, env=env)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("0 new violation(s)", run.stdout)


if __name__ == "__main__":
    unittest.main()
