"""Find code that contradicts a decision.

Step 1: the obvious version. Search each line for the forbidden names.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from guard.decisions import Decision


@dataclass(frozen=True)
class Violation:
    decision_id: str
    level: str
    path: str
    line: int
    col: int
    name: str
    line_text: str


def find_violations(source: str, path: str, decisions: list[Decision]) -> list[Violation]:
    found = []
    for decision in decisions:
        if not decision.applies_to(path):
            continue
        for rule in decision.rules:
            for name in rule.names:
                pattern = re.compile(rf"\b{re.escape(name)}\b")
                for lineno, text in enumerate(source.splitlines(), 1):
                    for match in pattern.finditer(text):
                        found.append(
                            Violation(decision.id, decision.level, path, lineno,
                                      match.start() + 1, name, text)
                        )
    return sorted(found, key=lambda v: (v.line, v.col, v.decision_id))
