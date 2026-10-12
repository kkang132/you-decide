# you-decide

**The model scores. The code decides. You judge.**

A small, working demonstration of the pattern in [*You Decide*](https://www.linkedin.com/pulse/you-decide-kris-kang-o9hpc/): using a decision model inside an application.

You type a customer complaint. [Laya](https://huggingface.co/convaiinnovations/laya), an open decision model running on your machine, says which support team should handle it and why. You say whether you agree. After ten complaints, Laya gets a grade.

## Run it

Requires Python 3.11 or 3.12 and [uv](https://docs.astral.sh/uv/). Runs locally on Apple Silicon, CUDA or CPU. No API key. The first run downloads the model (up to about 2 GB).

```bash
uv sync
uv run you-decide
```

![A two-round session: Laya routes a wrong-size complaint to Returns, then an express-delivery refund to Shipping, which the person overrules to Billing](docs/screenshot.svg)

Each round shows the team Laya chose, that team's scope as the reason, its confidence, and how it weighed every team. If you disagree, pick the team it should have gone to. After the last round you get a grade, split by whether Laya was confident or unsure, with every routing you overruled.

The screenshot is a real session. Regenerate it with `uv run python scripts/screenshot.py`.

Each session is saved to `sessions/` as JSON lines. Use `--rounds N` to change the length, or press Enter on an empty line to stop early.

## Why Laya, not Jev

The article is about Jev, TypeSafe's hosted decision model. This demo runs [Laya](https://huggingface.co/convaiinnovations/laya) instead, for four reasons:

1. **Anyone can run it.** Laya's weights are open (Apache-2.0) and run on a laptop. There is no account, no API key and no bill, so `uv sync && uv run you-decide` is the whole setup. A demo of a pattern should not be gated behind a vendor sign-up.
2. **Complaints stay on your machine.** Nothing you type is sent to a third party. That matters once you try it on real customer text.
3. **The shape is the same.** Laya answers the same typed questions with the same fields: a choice, a probability per candidate and a confidence. Its bundled server, `laya-serve`, speaks Jev's `/v1/systemone` wire protocol, so a client written for Jev can point at it unchanged. The application code here is what carries over, and it does not care which model fills in the `Decision`.
4. **The article names it.** Laya is the open-source alternative the piece points to.

The trade-offs are real:

- **Quality.** TypeSafe claims a new architecture and calibration training for Jev. This demo uses Laya's base checkpoint, untuned and with known calibration problems (see caveats). Read the grades you get as a floor for the pattern, not a verdict on Jev.
- **Confidence is computed differently.** Laya's `confidence` is normalised entropy; Jev uses its own formula. The article's 0.3 cut-off is a Jev number, so `UNSURE_BELOW = 0.3` here is a starting point to tune from your sessions, not a value carried over. `laya-serve` also returns `x_jev_confidence` for anyone porting a Jev threshold.

To run the demo on Jev, write a backend with the same `decide()` method as [`LayaBackend`](src/you_decide/backends.py). `routing.py`, `grade.py` and `cli.py` stay as they are.

## How it works

A decision model does not write prose. You send it a state and a typed question with a fixed set of candidates, and it returns a probability for each candidate plus a confidence. The application does everything else.

| Field | Here |
|---|---|
| State | the complaint you typed |
| Type | Choice |
| Instructions | "Which support team should handle this complaint?" |
| Criteria | the four teams, each with its scope |

## A decision, step by step

A decision passes through five steps. The model is in one of them.

**1. The application defines the question.** [`routing.py`](src/you_decide/routing.py) fixes the candidates before the model sees anything:

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

**2. The model scores.** [`backends.py`](src/you_decide/backends.py) is the only place the model is called. For the wrong-size complaint, Laya answers:

```json
{"type": "choice", "choice": "returns",
 "probabilities": {"returns": 0.78, "shipping": 0.11, "technical": 0.07, "billing": 0.03},
 "confidence": 0.47,
 "action": {"act_probability": 1.0}}
```

The backend keeps the top pick, the distribution and the confidence, and drops `act_probability` (see caveats).

**3. The result is evidence, not an action.** A [`Decision`](src/you_decide/decisions.py) is a frozen record of what the model said. It has no method that routes anything.

**4. Code applies the rule for doubt.** Back in `routing.py`:

```python
UNSURE_BELOW = 0.3

def is_unsure(d: Decision) -> bool:
    return d.confidence < UNSURE_BELOW
```

One constant and one comparison. It can be changed, reviewed in a diff and unit-tested, which a sentence in a prompt cannot.

**5. The application acts and records.** [`cli.py`](src/you_decide/cli.py) shows the routing, takes your verdict and records it next to the confidence. The "why" on screen is `TEAMS[d.top]`: the application's own text, indexed by the model's choice. [`grade.py`](src/you_decide/grade.py) splits your agreement by the unsure flag, which tells you whether the confidence is worth automating on.

In this demo you judge every round, so an unsure routing is only flagged. In production, step 5 is where code takes over:

```python
team = d.top if not is_unsure(d) else HUMAN_QUEUE
```

### Why this shape

1. **The application owns the options.** The model only scores which scope fits. It cannot invent a fifth team.
2. **The explanation cannot be hallucinated.** The scope text guides the model and is shown to you as the reason. The model writes no prose, so there is nothing to make up. The bar chart shows what it weighed against what.
3. **Doubt is handled in code.** The threshold is a line you own, and the session log is the evidence for moving it.

The scopes matter more than you might expect. Asked to pick between bare team names, Laya sends the wrong-size example to `shipping`. With the scopes, it picks `returns` at 78%.

## Laya caveats

Observed directly on `laya==0.3.21`:

- **Use `confidence`, not `action.act_probability`.** The latter reads 1.0 regardless of input on the shipped checkpoint, so [`backends.py`](src/you_decide/backends.py) ignores it.
- **Treat confidence as a ranking signal, not a probability.** The shipped calibration is off (Laya warns about it on load). A routing at 0.47 is more trustworthy than one at 0.2, but do not read 0.47 as a 47% chance of being right. Your session grades are the evidence.
- **This is the base checkpoint, untuned.** Fine-tuning on real tickets would raise the grade. That is a separate project.

## Security

- **Dependencies** are pinned in `uv.lock`. `pip-audit` against the lockfile reported no known vulnerabilities on 12 October 2026; rerun with `uv export --no-hashes --no-emit-project > req.txt && uvx pip-audit -r req.txt --no-deps --disable-pip`.
- **Model weights** load from `safetensors`, not pickle, with no `trust_remote_code`. The Hub revision is pinned in [`backends.py`](src/you_decide/backends.py), so a later upload to the model repo cannot change what runs.
- **Your complaints** never leave the machine. They are saved in `sessions/` (git-ignored); delete it when you are done.

## Layout

```
src/you_decide/
  decisions.py   Choice and Decision
  backends.py    LayaBackend; any object with decide() works
  routing.py     the teams, their scopes, and the unsure rule
  grade.py       turns your verdicts into a grade
  cli.py         the interactive session
scripts/screenshot.py   renders docs/screenshot.svg from a real session
tests/           the application side, no model needed
```

```bash
uv run pytest
```

## License

MIT
