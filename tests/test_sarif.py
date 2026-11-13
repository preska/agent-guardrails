import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from guard.checker import find_violations
from guard.decisions import load_decisions
from guard.sarif import annotation, to_sarif
from tests.helpers import git, make_repo, write

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

    def test_ci_command_annotates_new_violations_only(self):
        env = {**os.environ, "GITHUB_ACTIONS": "true", "PYTHONPATH": str(REPO)}

        def ci():
            return subprocess.run([sys.executable, "-m", "guard", "ci", "--sarif", "out.sarif"],
                                  cwd=self.root, capture_output=True, text=True, env=env)

        subprocess.run([sys.executable, "-m", "guard", "baseline"], cwd=self.root, env=env, check=True)
        self.assertEqual(ci().returncode, 0)
        write(self.root, "billing/tax.py", "rate = float(r)\n")
        git(self.root, "add", "-A")
        run = ci()
        self.assertEqual(run.returncode, 1)
        self.assertIn("::error file=billing/tax.py,line=1,col=8,title=DEC-002", run.stdout)
        sarif = json.loads((self.root / "out.sarif").read_text())
        self.assertEqual([r["ruleId"] for r in sarif["runs"][0]["results"]], ["DEC-002"])

if __name__ == "__main__":
    unittest.main()
