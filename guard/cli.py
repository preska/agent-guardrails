"""guard: enforce a team's recorded decisions on Python code."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from guard.checker import Violation, find_violations
from guard.decisions import DECISIONS_DIR, Decision, load_decisions


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


def cmd_check(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    decisions = load_decisions(root)
    by_id = {d.id: d for d in decisions}
    violations = []
    for path in python_files(root, args.paths):
        source = (root / path).read_text(encoding="utf-8")
        try:
            violations += find_violations(source, path, decisions)
        except SyntaxError as err:
            print(f"{path}:{err.lineno}: skipped, does not parse: {err.msg}")
    for v in violations:
        print(describe(v, by_id))
    errors = sum(v.level == "error" for v in violations)
    print(f"{len(violations)} violation(s), {errors} blocking")
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="guard", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="check files against the decisions")
    check.add_argument("paths", nargs="*", help="files to check (default: every tracked .py file)")
    check.set_defaults(run=cmd_check)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
