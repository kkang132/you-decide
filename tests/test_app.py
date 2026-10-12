"""Tests for the application side. No model is loaded."""

import io

from rich.console import Console

from you_decide import Decision
from you_decide.cli import report, session
from you_decide.grade import Round, grade


class FakeBackend:
    def __init__(self, decisions):
        self.decisions = iter(decisions)

    def decide(self, state, question):
        return next(self.decisions)


def scripted(answers):
    it = iter(answers)

    def ask(prompt):
        a = next(it)
        if isinstance(a, BaseException):
            raise a
        return a

    return ask


def console():
    return Console(file=io.StringIO(), width=100, color_system=None)


def output(c):
    return c.file.getvalue()


def test_session_records_verdicts_and_corrections():
    backend = FakeBackend([
        Decision("returns", {"returns": 0.8, "shipping": 0.2}, 0.7),
        Decision("shipping", {"shipping": 0.5, "returns": 0.5}, 0.1),
    ])
    c = console()
    played = session(backend, 2, c, scripted([
        "wrong size, can I swap?", "y",
        "parcel never came", "n", "1",
    ]))
    assert [r.agreed for r in played] == [True, False]
    # The routed team (shipping) is not offered, so 1 is returns.
    assert played[1].correct_team == "returns"
    assert played[1].unsure and not played[0].unsure
    text = output(c)
    assert "Returns and exchanges" in text
    assert "unsure" in text
    assert "2 Shipping" not in text


def test_blank_complaint_ends_session_early():
    assert session(FakeBackend([]), 10, console(), scripted([""])) == []


def test_interrupt_keeps_completed_rounds():
    backend = FakeBackend([Decision("billing", {"billing": 1.0}, 0.9)] * 2)
    played = session(backend, 5, console(), scripted(["charged twice", "y", "again", KeyboardInterrupt()]))
    assert len(played) == 1


def test_reprompts_until_yes_or_no():
    backend = FakeBackend([Decision("billing", {"billing": 1.0}, 0.9)])
    played = session(backend, 1, console(), scripted(["charged twice", "maybe", "Y"]))
    assert played[0].agreed


def test_grade_splits_by_confidence():
    rounds = [Round("a", "returns", 0.8, False, True)] * 7 + [Round("b", "billing", 0.1, True, False)] * 3
    g = grade(rounds)
    assert (g.agreed, g.rounds, g.letter) == (7, 10, "C")
    assert (g.sure_agreed, g.sure_total, g.unsure_agreed, g.unsure_total) == (7, 7, 0, 3)


def test_report_prints_grade_and_overrules():
    c = console()
    report([Round("x", "returns", 0.9, False, True),
            Round("parcel lost", "returns", 0.2, True, False, "shipping")], c)
    text = output(c)
    assert "Laya's grade" in text and " F " in text
    assert "Where you overruled it" in text and "parcel lost" in text


def test_control_characters_are_stripped_from_complaints():
    backend = FakeBackend([Decision("billing", {"billing": 1.0}, 0.9)])
    played = session(backend, 1, console(), scripted(["\x1b[31mcharged twice\x07", "y"]))
    assert played[0].complaint == "[31mcharged twice"
