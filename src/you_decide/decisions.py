"""A typed question and the decision it produces.

A question is bounded: it names its candidates up front. A decision is the
model's full distribution over those candidates, plus a confidence. Nothing in
this module acts on a decision. That is the application's job.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Choice:
    """Pick one of a fixed set of options. Each option may carry a description."""

    instructions: str
    options: dict[str, str]

    def to_wire(self) -> dict:
        return {"type": "choice", "instructions": self.instructions, "criteria": dict(self.options)}


@dataclass(frozen=True)
class Decision:
    """What the model returns for one question. It is evidence, not an action."""

    top: str
    probabilities: dict[str, float]
    confidence: float

    def ranked(self) -> list[tuple[str, float]]:
        return sorted(self.probabilities.items(), key=lambda kv: kv[1], reverse=True)
