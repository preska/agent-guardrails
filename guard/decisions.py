"""Decisions are Markdown files in .decisions/.

Each file has a little frontmatter, prose for people (and agents), and a
```rule block that the checker enforces:

    ---
    id: DEC-002
    title: Money is Decimal, never float
    level: error
    ---
    ## Why
    ...
    ## Rules
    ```rule
    forbid call float
    in examples/billing/**
    ```
    ## Fix
    ...
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

DECISIONS_DIR = ".decisions"
LEVELS = ("error", "warning")  # error blocks; warning reports

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
RULE_BLOCK = re.compile(r"^```rule\n(.*?)^```", re.S | re.M)


class DecisionError(ValueError):
    """A decision file that can't be read. Never guess: fail loudly."""


@dataclass
class Rule:
    kind: str  # "import" or "call"
    names: list[str]


@dataclass
class Decision:
    id: str
    title: str
    level: str
    rules: list[Rule]
    include: list[str] = field(default_factory=list)  # empty: every file
    exclude: list[str] = field(default_factory=list)
    why: str = ""
    fix: str = ""

    def applies_to(self, path: str) -> bool:
        if self.include and not any(glob_match(path, g) for g in self.include):
            return False
        return not any(glob_match(path, g) for g in self.exclude)


def load_decisions(root: Path) -> list[Decision]:
    folder = root / DECISIONS_DIR
    return [parse_decision(p) for p in sorted(folder.glob("*.md"))]


def parse_decision(path: Path) -> Decision:
    text = path.read_text(encoding="utf-8")
    front = FRONTMATTER.match(text)
    if not front:
        raise DecisionError(f"{path}: no frontmatter")
    meta = {}
    for line in front.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip()
    for key in ("id", "title"):
        if not meta.get(key):
            raise DecisionError(f"{path}: frontmatter needs {key}")
    level = meta.get("level", "error")
    if level not in LEVELS:
        raise DecisionError(f"{path}: level must be one of {LEVELS}, not {level!r}")

    decision = Decision(
        id=meta["id"],
        title=meta["title"],
        level=level,
        rules=[],
        why=section(text, "Why"),
        fix=section(text, "Fix"),
    )
    for block in RULE_BLOCK.findall(text):
        for line in block.splitlines():
            parse_rule_line(decision, line.strip(), path)
    if not decision.rules:
        raise DecisionError(f"{path}: no forbid lines in a ```rule block")
    return decision


def parse_rule_line(decision: Decision, line: str, path: Path) -> None:
    if not line or line.startswith("#"):
        return
    verb, _, rest = line.partition(" ")
    if verb == "forbid":
        kind, _, names = rest.partition(" ")
        if kind in ("import", "call") and names:
            decision.rules.append(Rule(kind, split_list(names)))
            return
    elif verb == "in" and rest:
        decision.include += split_list(rest)
        return
    elif verb == "except" and rest:
        decision.exclude += split_list(rest)
        return
    raise DecisionError(f"{path}: can't read rule line {line!r}")


def split_list(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip()]


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {heading}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return " ".join(match.group(1).split()) if match else ""


def glob_match(path: str, pattern: str) -> bool:
    """Match a repo-relative path against a glob where ** spans folders."""
    regex = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            regex += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            regex += ".*"
            i += 2
        elif pattern[i] == "*":
            regex += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            regex += "[^/]"
            i += 1
        else:
            regex += re.escape(pattern[i])
            i += 1
    return re.fullmatch(regex, path) is not None
