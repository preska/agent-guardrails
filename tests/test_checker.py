import unittest

from guard.checker import find_violations
from tests.helpers import decisions

NO_SYSTEM = """\
---
id: DEC-009
title: No shelling out
---
```rule
forbid call os.system
```
"""


def check(source, path="billing/invoice.py"):
    return [(v.decision_id, v.line) for v in find_violations(source, path, decisions())]


class CheckerTest(unittest.TestCase):
    def test_finds_a_forbidden_import(self):
        self.assertEqual(check("import openai\n"), [("DEC-001", 1)])

    def test_finds_a_forbidden_call(self):
        self.assertEqual(check("total = float(amount)\n"), [("DEC-002", 1)])

    def test_respects_scope(self):
        self.assertEqual(check("import openai\n", path="web/chat.py"), [])

    def test_comments_strings_and_docstrings_are_not_uses(self):
        source = '"""Never openai."""\n# no openai\nhint = "use float"\n'
        self.assertEqual(check(source), [])

    def test_from_import_and_submodules(self):
        self.assertEqual(check("from openai import OpenAI\n"), [("DEC-001", 1)])
        self.assertEqual(check("import openai.types as t\n"), [("DEC-001", 1)])
        self.assertEqual(check("import openai_helpers\n"), [])

    def test_relative_imports_are_local(self):
        self.assertEqual(check("from .openai import summary\n"), [])

    def test_dotted_calls(self):
        ds = decisions(NO_SYSTEM)
        found = find_violations("import os\nos.system('ls')\nsystem()\n", "a.py", ds)
        self.assertEqual([(v.name, v.line) for v in found], [("os.system", 2)])

    def test_a_method_named_like_a_builtin_is_not_the_builtin(self):
        self.assertEqual(check("parser.float(x)\n"), [])

    def test_source_that_does_not_parse_raises(self):
        with self.assertRaises(SyntaxError):
            check("def broken(:\n")


if __name__ == "__main__":
    unittest.main()
