import unittest

from guard.baseline import fingerprinted, new_violations
from guard.checker import find_violations
from tests.helpers import decisions

DS = decisions()
PATH = "billing/export.py"


def found(source):
    return find_violations(source, PATH, DS)


def known(source):
    return {fp for fp, _ in fingerprinted(found(source))}


BEFORE = "def total(x):\n    return float(x)\n"


class BaselineTest(unittest.TestCase):
    def test_known_violations_are_not_new(self):
        self.assertEqual(new_violations(found(BEFORE), known(BEFORE)), [])

    def test_moving_code_down_does_not_make_it_new(self):
        after = "import logging\n\n\n" + BEFORE
        self.assertEqual(new_violations(found(after), known(BEFORE)), [])

    def test_reindenting_does_not_make_it_new(self):
        after = "def total(x):\n        return   float(x)\n"
        self.assertEqual(new_violations(found(after), known(BEFORE)), [])

    def test_a_new_violation_is_new(self):
        after = BEFORE + "def tax(x):\n    y = float(x)\n"
        self.assertEqual([v.line for v in new_violations(found(after), known(BEFORE))], [4])

    def test_a_repeat_of_an_existing_line_is_new(self):
        after = BEFORE + "def again(x):\n    return float(x)\n"
        self.assertEqual(len(new_violations(found(after), known(BEFORE))), 1)

    def test_same_code_in_another_file_is_new(self):
        other = find_violations(BEFORE, "billing/other.py", DS)
        self.assertEqual(len(new_violations(other, known(BEFORE))), 1)


if __name__ == "__main__":
    unittest.main()
