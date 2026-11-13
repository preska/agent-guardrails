"""guard: enforce a team's recorded decisions on Python code."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import guard.hook
from guard.baseline import load_baseline, new_violations, save_baseline
from guard.checker import Violation, find_violations
from guard.decisions import DECISIONS_DIR, Decision, load_decisions
from guard.gate import staged_violations
from guard.sarif import annotation, to_sarif


def find_root(start: Path) -> Path:
    """The nearest folder, at or above start, that holds .decisions/."""
    for folder in (start, *start.parents):
        if (folder / DECISIONS_DIR).is_dir():
            return folder
    raise SystemExit(f"guard: no {DECISIONS_DIR}/ folder at or above {start}")


def python_files(root: Path, paths: list[str]) -> list[str]:
    """Repo-relative paths: the ones given, or every tracked .py file."""
    if paths:
        return [Path(p).resolve().relative_to(root).as_posix() for p in paths]
    out = subprocess.run(["git", "ls-files", "-z", "--", "*.py"], cwd=root,
                         capture_output=True, text=True, check=True).stdout
    return sorted(p for p in out.split("\0") if p)


def describe(v: Violation, decisions: dict[str, Decision]) -> str:
    d = decisions[v.decision_id]
    return (f"{v.path}:{v.line}:{v.col}: {v.level.upper()} {d.id} {d.title}\n"
            f"    {v.line_text.strip()}\n"
            f"    fix: {d.fix}")


def collect(root: Path, paths: list[str], decisions: list[Decision]) -> list[Violation]:
    violations = []
    for path in python_files(root, paths):
        source = (root / path).read_text(encoding="utf-8")
        try:
            violations += find_violations(source, path, decisions)
        except SyntaxError as err:
            print(f"{path}:{err.lineno}: skipped, does not parse: {err.msg}")
    return violations


def report(found: list[Violation], decisions: list[Decision], known: int | None = None) -> int:
    by_id = {d.id: d for d in decisions}
    for v in found:
        print(describe(v, by_id))
    errors = sum(v.level == "error" for v in found)
    summary = f"{len(found)} new violation(s), {errors} blocking"
    print(summary if known is None else f"{summary}; {known} known in the baseline")
    return 1 if errors else 0


def cmd_check(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    decisions = load_decisions(root)
    violations = collect(root, args.paths, decisions)
    found = new_violations(violations, load_baseline(root))
    return report(found, decisions, len(violations) - len(found))


def cmd_baseline(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    count = save_baseline(root, collect(root, [], load_decisions(root)))
    print(f"recorded {count} existing violation(s) in .decisions/baseline.json")
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    status = report(staged_violations(root), load_decisions(root))
    if status:
        print("commit blocked: fix the code, or change the decision if the team has changed its mind")
    return status


def cmd_ci(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    decisions = load_decisions(root)
    violations = collect(root, [], decisions)
    found = new_violations(violations, load_baseline(root))
    if args.sarif:
        Path(args.sarif).write_text(to_sarif(found, decisions), encoding="utf-8")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        by_id = {d.id: d for d in decisions}
        for v in found:
            print(annotation(v, by_id[v.decision_id]))
    return report(found, decisions, len(violations) - len(found))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="guard", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="check files against the decisions")
    check.add_argument("paths", nargs="*", help="files to check (default: every tracked .py file)")
    check.set_defaults(run=cmd_check)
    baseline = commands.add_parser("baseline", help="record today's violations as known")
    baseline.set_defaults(run=cmd_baseline)
    hook = commands.add_parser("hook", help="Claude Code PreToolUse hook (reads JSON on stdin)")
    hook.set_defaults(run=lambda _args: guard.hook.main())
    gate = commands.add_parser("gate", help="pre-commit: check the staged changes")
    gate.set_defaults(run=cmd_gate)
    ci = commands.add_parser("ci", help="check the whole repo; annotate the PR; write SARIF")
    ci.add_argument("--sarif", metavar="FILE", help="also write the results as SARIF 2.1.0")
    ci.set_defaults(run=cmd_ci)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
