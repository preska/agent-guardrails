# agent-guardrails

Companion code for the tutorial
**[Build a guardrail that stops coding agents breaking your team's decisions](https://daami.dev/tutorials/agent-guardrails/)**.

Your team decides things: money is `Decimal`, billing never calls a model API,
use the logger. Coding agents forget those decisions at the start of every
session. `guard` records each decision as a file and enforces it at three
points:

| Where | When | What happens |
|---|---|---|
| Claude Code `PreToolUse` hook | before an agent's edit is written | the edit is denied, and the agent is told why and what to do instead |
| `pre-commit` | before anyone's commit | the commit fails on new violations in the staged code |
| GitHub Actions | on every pull request | annotations on the PR lines, alerts in code scanning (SARIF) |

It is standard-library Python (3.11+), deterministic and offline: no model calls, no network.

## The steps

Each step of the tutorial is a tag. `git checkout step-N` gives you the code as of that step, with passing tests.

| Tag | Step |
|---|---|
| [`step-1`](../../tree/step-1) | Decisions as files, and the obvious checker (and why it's wrong) |
| [`step-2`](../../tree/step-2) | Check the syntax tree, not the text |
| [`step-3`](../../tree/step-3) | Adopt it in a codebase that already breaks the rules: a baseline keyed by content hash |
| [`step-4`](../../tree/step-4) | Stop the agent before it writes: a Claude Code hook |
| [`step-5`](../../tree/step-5) | Gate commits on what is staged |
| [`step-6`](../../tree/step-6) | CI: annotate the pull request, upload SARIF |

## Try it

```sh
git clone https://github.com/preska/agent-guardrails && cd agent-guardrails
python3 -m venv .venv && . .venv/bin/activate
pip install -e .
python -m unittest discover -s tests

guard check                           # the examples are clean against the baseline
git config core.hooksPath hooks       # turn on the pre-commit gate
claude                                # the hook in .claude/settings.json is active;
                                      # ask for a float in examples/billing/ and watch
```

`examples/billing/` is a small billing service that the three decisions in
`.decisions/` apply to.

## Limits

These are deliberate, and the tutorial explains each one:

- It checks Python only, and only imports and calls. An aliased call (`f = float; f(x)`) or a dynamic import (`importlib.import_module("openai")`) gets through.
- The agent hook is a guardrail, not a boundary. The pre-commit gate and CI are where it's enforced.
- The hook fails open: if it can't decide, the edit goes ahead.
