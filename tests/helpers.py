"""Shared test fixtures: decisions written into a temporary repo."""

from __future__ import annotations

import subprocess
import tempfile
import textwrap
from pathlib import Path

from guard.decisions import Decision, load_decisions

MODEL_SDKS = """\
---
id: DEC-001
title: Billing never calls a model API
level: error
---
## Why
Deterministic billing.
## Rules
```rule
forbid import openai, anthropic
in billing/**
```
## Fix
Pass generated text in as a string.
"""

NO_FLOAT = """\
---
id: DEC-002
title: Money is Decimal, never float
level: error
---
## Rules
```rule
forbid call float
in billing/**
except billing/legacy/**
```
## Fix
Use Decimal.
"""

NO_PRINT = """\
---
id: DEC-003
title: Log with the logger, not print
level: warning
---
## Rules
```rule
forbid call print
```
## Fix
Use logging.
"""


def make_repo(files: dict[str, str], decisions=(MODEL_SDKS, NO_FLOAT, NO_PRINT)) -> Path:
    """A throwaway git repo with .decisions/ and the given files committed."""
    root = Path(tempfile.mkdtemp(prefix="guard-test-"))
    for i, text in enumerate(decisions, 1):
        write(root, f".decisions/DEC-{i:03}.md", text)
    for path, text in files.items():
        write(root, path, text)
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
    return root


def write(root: Path, path: str, text: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(textwrap.dedent(text), encoding="utf-8")


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True,
                          text=True, check=True).stdout


def decisions(*texts: str) -> list[Decision]:
    root = make_repo({}, decisions=texts or (MODEL_SDKS, NO_FLOAT, NO_PRINT))
    return load_decisions(root)
