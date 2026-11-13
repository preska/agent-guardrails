import json
import subprocess
import sys
import unittest

from guard import hook
from tests.helpers import make_repo

INVOICE = "from decimal import Decimal\n\n\ndef total(x):\n    return Decimal(x)\n"
LEGACY = "def total(x):\n    return float(x)\n"


class HookTest(unittest.TestCase):
    def setUp(self):
        self.root = make_repo({"billing/invoice.py": INVOICE, "billing/export.py": LEGACY})

    def call(self, tool, **tool_input):
        return hook.run({"tool_name": tool, "cwd": str(self.root), "tool_input": tool_input})

    def path(self, rel):
        return str(self.root / rel)

    def test_write_with_a_new_violation_is_denied(self):
        answer = self.call("Write", file_path=self.path("billing/new.py"),
                           content="import openai\n")
        out = answer["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("DEC-001", out["permissionDecisionReason"])
        self.assertIn("Fix: Pass generated text in as a string.", out["permissionDecisionReason"])

    def test_edit_is_checked_on_the_whole_resulting_file(self):
        answer = self.call("Edit", file_path=self.path("billing/invoice.py"),
                           old_string="Decimal(x)", new_string="float(x)")
        self.assertEqual(answer["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_existing_violations_do_not_block_unrelated_edits(self):
        answer = self.call("Edit", file_path=self.path("billing/export.py"),
                           old_string="def total(x):", new_string="def total(x):  # CSV")
        self.assertIsNone(answer)

    def test_warnings_go_through_with_a_note(self):
        answer = self.call("Write", file_path=self.path("billing/new.py"), content="print('hi')\n")
        out = answer["hookSpecificOutput"]
        self.assertNotIn("permissionDecision", out)
        self.assertIn("DEC-003", out["additionalContext"])

    def test_clean_edits_get_no_answer(self):
        self.assertIsNone(self.call("Write", file_path=self.path("billing/new.py"), content="x = 1\n"))

    def test_code_that_does_not_parse_yet_goes_through(self):
        self.assertIsNone(self.call("Write", file_path=self.path("billing/new.py"),
                                    content="import openai\ndef broken(:\n"))

    def test_out_of_scope_and_other_tools_go_through(self):
        self.assertIsNone(self.call("Write", file_path=self.path("web/chat.py"), content="import openai\n"))
        self.assertIsNone(self.call("Write", file_path=self.path("billing/notes.md"), content="openai"))
        self.assertIsNone(self.call("Bash", command="pip install openai"))

    def test_edit_whose_old_string_is_missing_goes_through(self):
        self.assertIsNone(self.call("Edit", file_path=self.path("billing/invoice.py"),
                                    old_string="nope", new_string="import openai"))

    def test_the_command_fails_open_on_garbage(self):
        run = subprocess.run([sys.executable, "-m", "guard", "hook"], input="not json",
                             capture_output=True, text=True)
        self.assertEqual((run.returncode, run.stdout), (0, ""))

    def test_the_command_prints_the_answer_as_json(self):
        payload = {"tool_name": "Write", "cwd": str(self.root),
                   "tool_input": {"file_path": self.path("billing/new.py"), "content": "import anthropic\n"}}
        run = subprocess.run([sys.executable, "-m", "guard", "hook"], input=json.dumps(payload),
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0)
        self.assertEqual(json.loads(run.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()
