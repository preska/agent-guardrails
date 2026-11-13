"""Report violations where reviewers look: on the pull request.

Two outputs, because they reach different people:

- SARIF 2.1.0, uploaded to GitHub code scanning: each violation becomes an
  alert that stays open until the code is fixed, with the decision's Why and
  Fix as its help text.
- Workflow commands (::error file=...::), which GitHub turns into annotations
  on the PR's changed lines without any extra permissions.
"""

from __future__ import annotations

import json

from guard.baseline import fingerprinted
from guard.checker import Violation
from guard.decisions import Decision

SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"


def to_sarif(found: list[Violation], decisions: list[Decision]) -> str:
    rules = [{
        "id": d.id,
        "name": d.id.replace("-", ""),
        "shortDescription": {"text": d.title},
        "fullDescription": {"text": d.why or d.title},
        "help": {"text": f"Why: {d.why}\nFix: {d.fix}", "markdown": f"**Why:** {d.why}\n\n**Fix:** {d.fix}"},
        "defaultConfiguration": {"level": d.level},
    } for d in decisions]
    by_id = {d.id: d for d in decisions}
    results = [{
        "ruleId": v.decision_id,
        "level": v.level,
        "message": {"text": f"{by_id[v.decision_id].title}. Fix: {by_id[v.decision_id].fix}"},
        "locations": [{"physicalLocation": {
            "artifactLocation": {"uri": v.path},
            "region": {"startLine": v.line, "startColumn": v.col},
        }}],
        "partialFingerprints": {"guardFingerprint/v1": fp},
    } for fp, v in fingerprinted(found)]
    log = {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "guard",
                "informationUri": "https://github.com/preska/agent-guardrails",
                "rules": rules,
            }},
            "results": results,
        }],
    }
    return json.dumps(log, indent=2) + "\n"


def annotation(v: Violation, d: Decision) -> str:
    """One GitHub workflow command; GitHub shows it on the PR line."""
    props = f"file={prop(v.path)},line={v.line},col={v.col},title={prop(f'{d.id} {d.title}')}"
    return f"::{v.level} {props}::{data(f'{d.title}. Why: {d.why} Fix: {d.fix}')}"


def data(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def prop(text: str) -> str:
    return data(text).replace(":", "%3A").replace(",", "%2C")
