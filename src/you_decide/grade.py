"""Grade a session from the person's verdicts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Round:
    complaint: str
    routed_to: str
    confidence: float
    unsure: bool
    agreed: bool
    correct_team: str | None = None


@dataclass(frozen=True)
class Grade:
    rounds: int
    agreed: int
    sure_agreed: int
    sure_total: int
    unsure_agreed: int
    unsure_total: int

    @property
    def score(self) -> float:
        return self.agreed / self.rounds if self.rounds else 0.0

    @property
    def letter(self) -> str:
        for cut, letter in ((0.9, "A"), (0.8, "B"), (0.7, "C"), (0.6, "D")):
            if self.score >= cut:
                return letter
        return "F"


def grade(rounds: list[Round]) -> Grade:
    sure = [r for r in rounds if not r.unsure]
    unsure = [r for r in rounds if r.unsure]
    return Grade(
        rounds=len(rounds),
        agreed=sum(r.agreed for r in rounds),
        sure_agreed=sum(r.agreed for r in sure),
        sure_total=len(sure),
        unsure_agreed=sum(r.agreed for r in unsure),
        unsure_total=len(unsure),
    )
