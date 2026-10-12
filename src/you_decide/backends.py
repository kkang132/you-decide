"""Decision backends.

`LayaBackend` runs the open Laya model locally (MPS, CUDA or CPU). Any object
with a matching `decide` method will do, which is how the tests run without a
model.
"""

from __future__ import annotations

from typing import Protocol

from .decisions import Choice, Decision


class Backend(Protocol):
    def decide(self, state: str, question: Choice) -> Decision: ...


# The Hub commit this demo was tested against. Pinned so a later upload to the
# model repo, benign or not, cannot change what users run without a code change.
LAYA_REVISION = "7b928d828b7b0e022f929d9bd2e44165aa270148"


class LayaBackend:
    def __init__(
        self, model: str = "convaiinnovations/laya", device: str | None = None, revision: str | None = LAYA_REVISION
    ):
        import laya  # heavy import; deferred so the rest of the package loads without torch

        self._agent = laya.load(model, device=device, revision=revision)

    def decide(self, state: str, question: Choice) -> Decision:
        a = self._agent.predict(state, {"q": question.to_wire()})["answers"]["q"]
        # Laya also returns `action.act_probability`. On the shipped checkpoint it
        # reads 1.0 regardless of input, so it is deliberately ignored.
        return Decision(a["choice"], a["probabilities"], a["confidence"])
