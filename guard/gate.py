"""The pre-commit gate: the enforcement point.

Agent hooks are a guardrail, not a boundary. People edit files too, other
agents have no hook, and some tool paths skip hooks entirely. Every change
still has to be committed, so the gate runs there.

It checks what is *staged*, not what is in the working tree: after
`git add -p`, the working file and the commit can differ, and only the commit
matters. New violations are measured against the baseline.

It fails closed. A staged file that a decision applies to but that doesn't
parse can't be checked, so it blocks the commit instead of slipping through.
(The agent hook in step 4 fails open on purpose: it is advice; this is the
enforcement point.)
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from guard.baseline import load_baseline, new_violations
from guard.checker import Violation, find_violations
from guard.decisions import load_decisions


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True,
                          text=True, check=True).stdout


def staged_python_files(root: Path) -> list[str]:
    out = git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z", "--", "*.py")
    return sorted(p for p in out.split("\0") if p)


def staged_violations(root: Path) -> tuple[list[Violation], list[str]]:
    """New violations in the staged code, and the in-scope files that couldn't be checked."""
    decisions = load_decisions(root)
    found, unchecked = [], []
    for path in staged_python_files(root):
        source = git(root, "show", f":{path}")  # ":path" is the staged copy
        try:
            found += find_violations(source, path, decisions)
        except SyntaxError as err:
            unchecked.append(f"{path}:{err.lineno}: can't check, does not parse: {err.msg}")
    return new_violations(found, load_baseline(root)), unchecked
