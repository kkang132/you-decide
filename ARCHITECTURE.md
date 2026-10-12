# Architecture

How you-decide works inside. Terms in *italics* are defined in [GLOSSARY.md](./GLOSSARY.md).

## The idea in one line

The model scores, the code decides. The model is called once per complaint and returns numbers. Everything a person sees or acts on (the options, the reason, the rule for doubt, the grade) is ordinary code.

## Files

```
src/you_decide/
├── decisions.py   Choice (a typed question) and Decision (the model's answer)
├── backends.py    LayaBackend: the only place the model is called
├── routing.py     the teams, their scopes, and the rule for doubt
├── grade.py       turns the person's verdicts into a grade
└── cli.py         the interactive session: show, ask, record, report
scripts/
├── check.sh       lint, format, type check, tests; what CI runs
└── screenshot.py  renders docs/screenshot.svg from a real session
tests/test_app.py  the application side, with a fake backend; no model
```

## A decision, step by step

A decision passes through five steps. The model is in one of them.

**1. The application defines the question.** `routing.py` fixes the candidates before the model sees anything:

```python
TEAMS = {
    "returns": "Returns and exchanges: wrong size or colour, faulty or damaged items, ...",
    "shipping": "Shipping and delivery: tracking, late or lost parcels, ...",
    "billing": "Billing and payments: charges, refunds to a card, invoices, ...",
    "technical": "Website and app: login problems, error messages, crashes, ...",
}

QUESTION = Choice("Which support team should handle this complaint?", TEAMS)
```

`Choice.to_wire()` turns that into the payload Laya expects:

```json
{"type": "choice",
 "instructions": "Which support team should handle this complaint?",
 "criteria": {"returns": "Returns and exchanges: ...", "shipping": "Shipping and delivery: ...", "...": "..."}}
```

Laya joins each option to its scope (`returns: Returns and exchanges: ...`) before scoring, so the scope text guides the model.

**2. The model scores.** `backends.py` is the only place the model is called. For "My running shoes arrived in the wrong size. Can I swap them for a size 10?", Laya answers:

```json
{"type": "choice", "choice": "returns",
 "probabilities": {"returns": 0.78, "shipping": 0.11, "technical": 0.07, "billing": 0.03},
 "confidence": 0.47,
 "action": {"act_probability": 1.0}}
```

The backend keeps the top pick, the *distribution*, and the *confidence*. It drops `act_probability` (see caveats).

**3. The result is evidence, not an action.** A `Decision` is a frozen record of what the model said. It has no method that routes anything.

**4. Code applies the rule for doubt.** Back in `routing.py`:

```python
UNSURE_BELOW = 0.3


def is_unsure(d: Decision) -> bool:
    return d.confidence < UNSURE_BELOW
```

One constant and one comparison. It can be changed, reviewed in a diff, and unit-tested, which a sentence in a prompt cannot.

**5. The application acts and records.** `cli.py` shows the routing, takes the person's verdict, and records it next to the confidence. The reason on screen is `TEAMS[d.top]`: the application's own text, indexed by the model's choice. `grade.py` splits the person's agreement by the unsure flag, which shows whether the confidence is worth automating on.

In this demo the person judges every round, so an unsure routing is only flagged. In production, step 5 is where code takes over:

```python
team = d.top if not is_unsure(d) else HUMAN_QUEUE
```

## Why the scopes matter

Asked to choose between bare team names, Laya sends the wrong-size complaint to `shipping` at 79%, with confidence 0.53. That is above the unsure line, so the rule for doubt would not catch it. With the scopes, the same complaint goes to `returns` at 78%.

A threshold only catches the errors a model knows it might be making. A badly posed question produces confident mistakes. The options and their descriptions are the first thing to get right, and they are code.

## Laya caveats

Checked on `laya==0.4.4` at the pinned revision:

- **Use `confidence`, not `action.act_probability`.** The latter reads 1.0 for every input, including the nonsense string "asdf qwerty" (confidence 0.03). `backends.py` ignores it.
- **Treat confidence as a ranking, not a probability.** The shipped *calibration* is off; Laya warns about it on load. A routing at 0.47 is more trustworthy than one at 0.2, but 0.47 is not a 47% chance of being right. The session grades are the evidence.
- **Laya's confidence is not Jev's.** Laya's `confidence` is normalised entropy; Jev uses its own formula. The article's 0.3 is a Jev number, so `UNSURE_BELOW = 0.3` here is a starting point to tune, not a value carried over. `laya-serve` returns `x_jev_confidence` for anyone porting a Jev threshold.
- **This is the base checkpoint, untuned.** Fine-tuning on real tickets would raise the grade. That is a separate project.

## Swapping the model

A backend is any object with this method:

```python
def decide(self, state: str, question: Choice) -> Decision: ...
```

To run the demo on Jev, or any other decision model, write one and pass it to `session()` in place of `LayaBackend`. `routing.py`, `grade.py`, and `cli.py` stay as they are. The tests already do this with a fake backend.

## Security

- **Dependencies** are pinned in `uv.lock`. `pip-audit` against the lockfile reported no known vulnerabilities on 12 October 2026. To rerun:

  ```bash
  uv export --no-hashes --no-emit-project > req.txt
  uvx pip-audit -r req.txt --no-deps --disable-pip
  ```

- **Model weights** load from `safetensors`, not pickle, with no `trust_remote_code`. The *revision* is pinned in `backends.py`, so a later upload to the model repository cannot change what runs.
- **Input** has control characters stripped, so a pasted escape sequence cannot restyle the terminal.
- **Complaints** never leave the machine. They are saved in `sessions/`, which git ignores.

## CI

`.github/workflows/ci.yml` runs `scripts/check.sh` and the proofs from [AGENTS.md](./AGENTS.md) on every pull request and every push to `main`. It installs only the `dev` dependency group (`uv sync --only-group dev`): the check tools and `rich`, about 100 MB. It never installs Laya, torch, or CUDA, which would add several gigabytes for checks that never call the model. The cost is that CI never exercises the real model; that path is checked only by running the app.
