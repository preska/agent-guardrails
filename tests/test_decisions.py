import unittest
from pathlib import Path

from guard.decisions import DecisionError, glob_match, parse_decision
from tests.helpers import MODEL_SDKS, NO_FLOAT, decisions, make_repo


class ParseTest(unittest.TestCase):
    def test_reads_frontmatter_rules_and_prose(self):
        [d] = decisions(MODEL_SDKS)
        self.assertEqual((d.id, d.level), ("DEC-001", "error"))
        self.assertEqual(d.rules[0].kind, "import")
        self.assertEqual(d.rules[0].names, ["openai", "anthropic"])
        self.assertEqual(d.include, ["billing/**"])
        self.assertEqual(d.why, "Deterministic billing.")
        self.assertEqual(d.fix, "Pass generated text in as a string.")

    def test_scope(self):
        [d] = decisions(NO_FLOAT)
        self.assertTrue(d.applies_to("billing/invoice.py"))
        self.assertTrue(d.applies_to("billing/deep/er/tax.py"))
        self.assertFalse(d.applies_to("billing/legacy/old.py"))
        self.assertFalse(d.applies_to("web/views.py"))

    def test_unknown_rule_line_fails_loudly(self):
        bad = MODEL_SDKS.replace("forbid import", "forbid imports")
        root = make_repo({}, decisions=(bad,))
        with self.assertRaises(DecisionError):
            parse_decision(root / ".decisions/DEC-001.md")

    def test_unknown_level_fails_loudly(self):
        bad = MODEL_SDKS.replace("level: error", "level: must")
        root = make_repo({}, decisions=(bad,))
        with self.assertRaises(DecisionError):
            parse_decision(root / ".decisions/DEC-001.md")


class GlobTest(unittest.TestCase):
    def test_double_star_spans_folders(self):
        self.assertTrue(glob_match("a/b/c.py", "a/**"))
        self.assertTrue(glob_match("a/c.py", "a/**/c.py"))
        self.assertTrue(glob_match("a/x/y/c.py", "a/**/c.py"))

    def test_single_star_stays_in_one_folder(self):
        self.assertTrue(glob_match("a/c.py", "a/*.py"))
        self.assertFalse(glob_match("a/b/c.py", "a/*.py"))

    def test_the_repos_own_decisions_parse(self):
        repo = Path(__file__).resolve().parent.parent
        for path in sorted((repo / ".decisions").glob("*.md")):
            parse_decision(path)


if __name__ == "__main__":
    unittest.main()
