"""A Claude Code PreToolUse hook: check an edit before it is written.

Claude Code runs `guard hook` before every Write or Edit and sends the call as
JSON on stdin. We rebuild the file as it would be after the edit, compare its
violations with the file as it is now, and answer:

- nothing (exit 0, empty stdout): no new violations, let it through;
- "deny" with a reason: a new error-level violation; Claude sees the reason;
- "additionalContext": only new warnings; the edit goes ahead with a note.

The hook fails open. If anything goes wrong (bad JSON, unreadable file, code
that doesn't parse yet) it says nothing and the edit proceeds: the pre-commit
gate in step 5 is the enforcement point. A guardrail that crashes into the
agent's work gets switched off.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from guard.baseline import fingerprinted, new_violations
from guard.checker import Violation, find_violations
from guard.decisions import DECISIONS_DIR, Decision, load_decisions


def run(payload: dict) -> dict | None:
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    target = Path(tool_input.get("file_path", ""))
    if tool not in ("Write", "Edit") or target.suffix != ".py":
        return None

    root = find_root(Path(payload.get("cwd") or "."))
    if root is None:
        return None
    try:
        path = target.resolve().relative_to(root).as_posix()
    except ValueError:
        return None  # outside the repo

    before = target.read_text(encoding="utf-8") if target.exists() else ""
    after = proposed(tool, tool_input, before)
    if after is None:
        return None

    decisions = load_decisions(root)
    try:
        after_found = find_violations(after, path, decisions)
    except SyntaxError:
        return None  # mid-edit; the gate will see the finished file
    try:
        known = {fp for fp, _ in fingerprinted(find_violations(before, path, decisions))}
    except SyntaxError:
        known = set()

    found = new_violations(after_found, known)
    errors = [v for v in found if v.level == "error"]
    by_id = {d.id: d for d in decisions}
    if errors:
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": explain(errors, by_id, "Blocked"),
        }}
    if found:
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": explain(found, by_id, "Allowed, but note"),
        }}
    return None


def proposed(tool: str, tool_input: dict, before: str) -> str | None:
    """The whole file as it would be after this call, or None if we can't tell."""
    if tool == "Write":
        return tool_input.get("content")
    old, new = tool_input.get("old_string"), tool_input.get("new_string")
    if old is None or new is None or old not in before:
        return None  # Claude Code will report the failed edit itself
    count = -1 if tool_input.get("replace_all") else 1
    return before.replace(old, new, count)


def explain(found: list[Violation], decisions: dict[str, Decision], verdict: str) -> str:
    lines = [f"{verdict}: this edit contradicts the team's recorded decisions."]
    for v in found:
        d = decisions[v.decision_id]
        lines += [
            f"- {d.id} {d.title} ({v.path}:{v.line}: `{v.line_text.strip()}`)",
            f"  Why: {d.why}",
            f"  Fix: {d.fix}",
        ]
    lines.append("Change the code to follow the decision. Don't work around the check.")
    return "\n".join(lines)


def find_root(start: Path) -> Path | None:
    start = start.resolve()
    for folder in (start, *start.parents):
        if (folder / DECISIONS_DIR).is_dir():
            return folder
    return None


def main() -> int:
    try:
        answer = run(json.load(sys.stdin))
    except Exception:  # fail open, see the module docstring
        return 0
    if answer:
        print(json.dumps(answer))
    return 0
