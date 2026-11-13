"""Find code that contradicts a decision.

Step 2: check the syntax tree, not the text. A comment, a docstring or a string
that mentions `openai` is not a use of it; `from openai import OpenAI` is.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
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
    """Raises SyntaxError if the source doesn't parse: callers decide what that means."""
    applicable = [d for d in decisions if d.applies_to(path)]
    if not applicable:
        return []
    tree = ast.parse(source, filename=path)
    lines = source.splitlines()
    found = []
    for node in ast.walk(tree):
        for kind, used in uses(node):
            for decision in applicable:
                for rule in decision.rules:
                    if rule.kind == kind and any(is_or_inside(used, n) for n in rule.names):
                        found.append(Violation(
                            decision.id, decision.level, path, node.lineno,
                            node.col_offset + 1, used, lines[node.lineno - 1],
                        ))
    return sorted(found, key=lambda v: (v.line, v.col, v.decision_id))


def uses(node: ast.AST) -> Iterator[tuple[str, str]]:
    """What a node imports or calls, as ("import", "openai.types") or ("call", "os.system")."""
    if isinstance(node, ast.Import):
        for alias in node.names:
            yield "import", alias.name
    elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
        yield "import", node.module
    elif isinstance(node, ast.Call):
        name = dotted_name(node.func)
        if name:
            yield "call", name


def dotted_name(expr: ast.expr) -> str | None:
    """`os.path.join` for an attribute chain on a plain name; None for anything else."""
    parts = []
    while isinstance(expr, ast.Attribute):
        parts.append(expr.attr)
        expr = expr.value
    if not isinstance(expr, ast.Name):
        return None
    parts.append(expr.id)
    return ".".join(reversed(parts))


def is_or_inside(used: str, forbidden: str) -> bool:
    """Forbidding `openai` also forbids `openai.types`, but not `openai_helpers`."""
    return used == forbidden or used.startswith(forbidden + ".")
