# AGENTS.md

Guidance for AI agents in this repository.

This is a small demo of one idea: the model scores, the code decides. Most changes that break the demo break that idea, so the rules below protect it. When in doubt, keep the change small and run the proofs.

## Rules (never break these)

- Never call the model outside `src/you_decide/backends.py`. Everything else works on a `Decision`.
- Never let the model write the reason shown to the person. The "why" is the scope text in `TEAMS`, indexed by the model's choice.
- Never move the rule for doubt (`UNSURE_BELOW`) into a prompt, a question, or model output. It stays a constant in `routing.py`.
- Never unpin `LAYA_REVISION`, or change it, without running the app and regenerating `docs/screenshot.svg`.
- Never gate on `action.act_probability`. It reads 1.0 for every input on this checkpoint. Use `confidence`.
- Never weaken, skip, or delete a test to make it pass. Fix the code.
- Never commit `sessions/`. It holds what people typed.

## Working

- Run `scripts/check.sh` (lint, format, type check, tests) and keep it green. Install with `uv sync`.
- No check may load the model. Tests use a fake backend; CI does not install Laya.
- Write for a reader who knows neither Python nor machine learning.
- Every file opens with a comment: what it is for, and why.
- Comment intent, not mechanics. Plain names over clever ones. Small functions, one job each.
- Define new terms in [GLOSSARY.md](./GLOSSARY.md). Describe new moving parts in [ARCHITECTURE.md](./ARCHITECTURE.md).
- British spelling. No em-dashes.

## Adding a team

1. Add it to `TEAMS` in `src/you_decide/routing.py`, with a scope that says what the team owns in plain words. The scope is both the model's guidance and the reason the person sees, so write it for both.
2. Add a colour for it in `COLOURS` in `src/you_decide/cli.py`.
3. Run `scripts/check.sh`, then `uv run you-decide` with a few complaints that should land on the new team and a few that should not.

Overlapping scopes make the model unsure. That is information, not a bug: it shows up as a low confidence and a split bar chart.

## Proofs

Run these to confirm the project's invariants hold. Each is deterministic and uses no model. CI runs the same checks and fails the build on any of them.

```bash
# 1. lint, format, type check, and tests pass
scripts/check.sh

# 2. the model is called only from backends.py
grep -rnE "^\s*(import laya|from laya)|\.predict\(" src --include=*.py \
  | grep -v "^src/you_decide/backends.py:" && echo "LEAK" || echo "ok"

# 3. the model revision is pinned to a full commit hash
grep -qE '^LAYA_REVISION = "[0-9a-f]{40}"$' src/you_decide/backends.py && echo "ok" || echo "UNPINNED"

# 4. the reason shown to the person comes from TEAMS, not the model
grep -q 'TEAMS\[d\.top\]' src/you_decide/cli.py && echo "ok" || echo "REASON NOT FROM TEAMS"

# 5. nothing local or secret is tracked by git
git ls-files | grep -E "^sessions/|(^|/)\.env$|^\.venv/" && echo "TRACKED: remove it" || echo "ok"
```
