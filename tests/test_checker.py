import unittest

from guard.checker import find_violations
from tests.helpers import decisions


def check(source, path="billing/invoice.py"):
    return [(v.decision_id, v.line) for v in find_violations(source, path, decisions())]


class CheckerTest(unittest.TestCase):
    def test_finds_a_forbidden_import(self):
        self.assertEqual(check("import openai\n"), [("DEC-001", 1)])

    def test_finds_a_forbidden_call(self):
        self.assertEqual(check("total = float(amount)\n"), [("DEC-002", 1)])

    def test_respects_scope(self):
        self.assertEqual(check("import openai\n", path="web/chat.py"), [])

    def test_naive_search_also_flags_comments(self):
        # The problem step 2 fixes: a comment that mentions a name is not a use.
        self.assertEqual(check("# never use openai here\n"), [("DEC-001", 1)])


if __name__ == "__main__":
    unittest.main()
