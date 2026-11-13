"""Adopt a decision in a codebase that already breaks it.

The baseline records the violations that exist today; only new ones fail.
Each violation is identified by a content hash (decision, file, the code on the
line, and which repeat of that line it is), never by line number, so adding an
import at the top of a file doesn't make every old violation look new.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from guard.checker import Violation
from guard.decisions import DECISIONS_DIR

BASELINE_FILE = "baseline.json"


def fingerprinted(violations: list[Violation]) -> list[tuple[str, Violation]]:
    seen: Counter[tuple[str, str, str]] = Counter()
    out = []
    for v in violations:
        key = (v.decision_id, v.path, " ".join(v.line_text.split()))
        digest = hashlib.sha256("\0".join([*key, str(seen[key])]).encode()).hexdigest()
        out.append((digest[:16], v))
        seen[key] += 1
    return out


def new_violations(violations: list[Violation], known: set[str]) -> list[Violation]:
    return [v for fp, v in fingerprinted(violations) if fp not in known]


def load_baseline(root: Path) -> set[str]:
    path = root / DECISIONS_DIR / BASELINE_FILE
    if not path.exists():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8"))["fingerprints"])


def save_baseline(root: Path, violations: list[Violation]) -> int:
    fingerprints = sorted({fp for fp, _ in fingerprinted(violations)})
    path = root / DECISIONS_DIR / BASELINE_FILE
    path.write_text(json.dumps({"version": 1, "fingerprints": fingerprints}, indent=2) + "\n",
                    encoding="utf-8")
    return len(fingerprints)
