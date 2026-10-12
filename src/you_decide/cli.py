"""you-decide: type a customer complaint, see where Laya routes it, say whether you agree."""

from __future__ import annotations

import argparse
import json
import os
import time
import warnings
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from rich import box
from rich.console import Console, Group, RenderableType
from rich.padding import Padding
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .backends import Backend
from .decisions import Decision
from .grade import Grade, Round, grade
from .routing import TEAMS, UNSURE_BELOW, is_unsure, route

TEAM_NAMES = list(TEAMS)
COLOURS = {"returns": "cyan", "shipping": "magenta", "billing": "green", "technical": "blue"}
GRADE_COLOURS = {"A": "bold green", "B": "bold green", "C": "bold yellow", "D": "bold yellow", "F": "bold red"}

PANEL_WIDTH = 76

Ask = Callable[[str], str]


def team_label(team: str) -> Text:
    return Text(team.capitalize(), style=f"bold {COLOURS[team]}")


def bar(p: float, colour: str, width: int = 28) -> Text:
    n = round(p * width)
    return Text("━" * n, style=colour) + Text("━" * (width - n), style="grey23")


def confidence_line(d: Decision) -> Text:
    line = Text("Confidence ", style="dim") + Text(f"{d.confidence:.2f}", style="bold")
    if is_unsure(d):
        line += Text(f"   ▲ unsure, below {UNSURE_BELOW:.1f}: check this one closely", style="yellow")
    else:
        line += Text("   ● confident", style="green")
    return line


def routing_panel(d: Decision) -> Panel:
    dist = Table.grid(padding=(0, 2))
    dist.add_column(min_width=10)
    dist.add_column()
    dist.add_column(justify="right")
    for team, p in d.ranked():
        chosen = team == d.top
        name = Text(team, style=f"bold {COLOURS[team]}" if chosen else "dim")
        pct = Text(f"{p:.0%}", style="bold" if chosen else "dim")
        dist.add_row(name, bar(p, COLOURS[team] if chosen else "grey50"), pct)

    body = Group(
        Text(TEAMS[d.top], style="italic"),
        Text(""),
        confidence_line(d),
        Text(""),
        dist,
    )
    title = Text("Route to ") + team_label(d.top)
    return Panel(
        body,
        title=title,
        title_align="left",
        border_style=COLOURS[d.top],
        box=box.ROUNDED,
        padding=(1, 2),
        width=PANEL_WIDTH,
    )


def ask_agree(ask: Ask) -> bool:
    while True:
        a = ask("  Agree with this routing? [bold]\\[y/n][/] ").strip().lower()
        if a in ("y", "yes"):
            return True
        if a in ("n", "no"):
            return False


def ask_correct_team(ask: Ask, console: Console, routed_to: str) -> str | None:
    others = [t for t in TEAM_NAMES if t != routed_to]
    options = Text("  ")
    for i, team in enumerate(others, 1):
        options += Text(f"{i} ", style="bold") + team_label(team) + Text("    ")
    console.print(options)
    a = ask("  Which team should it go to? [dim](number, or Enter to skip)[/] ").strip()
    if a.isdigit() and 1 <= int(a) <= len(others):
        return others[int(a) - 1]
    return None


def session(backend: Backend, rounds: int, console: Console, ask: Ask | None = None) -> list[Round]:
    ask = ask or (lambda prompt: console.input(prompt))
    console.print(
        Padding(
            Text.assemble(
                ("Type a complaint. ", ""),
                ("Laya routes it, you judge. ", "bold"),
                (f"{rounds} rounds; empty line to stop.", "dim"),
            ),
            (0, 0, 1, 0),
        )
    )
    played: list[Round] = []
    for n in range(1, rounds + 1):
        label = f" Round {n} of {rounds} "
        console.print(Padding(Text("──" + label + "─" * (PANEL_WIDTH - len(label) - 2), style="grey42"), (0, 2)))
        try:
            raw = ask("\n  [bold]Customer complaint[/] [dim]›[/] ")
            # Drop control characters so pasted escape sequences cannot restyle the terminal.
            complaint = "".join(ch for ch in raw if ch.isprintable()).strip()
            if not complaint:
                break
            d = route(complaint, backend)
            console.print()
            console.print(Padding(routing_panel(d), (0, 2)))
            agreed = ask_agree(ask)
            correct = None if agreed else ask_correct_team(ask, console, d.top)
        except (KeyboardInterrupt, EOFError):
            # Keep the rounds already played; an unfinished round is dropped.
            console.print()
            break
        mark = Text("  ✓ agreed", style="green") if agreed else Text("  ✗ overruled", style="red")
        if correct:
            mark += Text(" → ") + team_label(correct)
        console.print(mark, "\n")
        played.append(Round(complaint, d.top, d.confidence, is_unsure(d), agreed, correct))
    return played


def scorecard(played: list[Round], g: Grade) -> Panel:
    stats = Table.grid(padding=(0, 3))
    stats.add_column(style="dim")
    stats.add_column(justify="right")
    stats.add_row("Routings you agreed with", f"[bold]{g.agreed}[/] / {g.rounds}")
    if g.sure_total:
        stats.add_row("When Laya was confident", f"[bold]{g.sure_agreed}[/] / {g.sure_total}")
    if g.unsure_total:
        stats.add_row("When Laya was unsure", f"[bold]{g.unsure_agreed}[/] / {g.unsure_total}")

    header = Table.grid(padding=(0, 4))
    header.add_column(justify="center", vertical="middle")
    header.add_column(vertical="middle")
    letter = Text(f" {g.letter} ", style=f"{GRADE_COLOURS[g.letter]} reverse")
    header.add_row(Group(letter, Text(f"{g.score:.0%}", style="dim", justify="center")), stats)

    parts: list[RenderableType] = [header]
    missed = [(r, r.correct_team) for r in played if not r.agreed and r.correct_team]
    if missed:
        table = Table(box=box.SIMPLE_HEAD, show_edge=False, pad_edge=False, header_style="dim")
        table.add_column("Laya said", no_wrap=True)
        table.add_column("You said", no_wrap=True)
        table.add_column("Complaint", overflow="ellipsis", no_wrap=True, max_width=48)
        for r, correct in missed:
            table.add_row(team_label(r.routed_to), team_label(correct), Text(r.complaint, style="italic"))
        parts += [Text(""), Text("Where you overruled it", style="bold"), table]
    return Panel(
        Group(*parts),
        title="[bold]Laya's grade[/]",
        title_align="left",
        border_style=GRADE_COLOURS[g.letter].split()[-1],
        box=box.ROUNDED,
        padding=(1, 2),
        width=PANEL_WIDTH,
    )


def report(played: list[Round], console: Console) -> None:
    if not played:
        console.print("[dim]No rounds played.[/]")
        return
    console.print(Padding(scorecard(played, grade(played)), (0, 2)))


def save(played: list[Round], directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / time.strftime("session-%Y%m%d-%H%M%S.jsonl")
    with path.open("w") as f:
        for r in played:
            f.write(json.dumps(asdict(r)) + "\n")
    return path


def load_laya(console: Console) -> Backend:
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    from .backends import LayaBackend

    with console.status("[dim]Loading Laya…[/]", spinner="dots"), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        backend = LayaBackend()
    if any("uncalibrated" in str(w.message) for w in caught):
        console.print(
            "[dim]  Note: Laya's shipped calibration is off. Read confidence as a ranking, not a probability.[/]"
        )
    return backend


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="you-decide", description=__doc__)
    p.add_argument("--rounds", type=int, default=10)
    p.add_argument("--save-dir", type=Path, default=Path("sessions"))
    args = p.parse_args(argv)

    console = Console()
    console.print()
    console.print(
        Padding(
            Text.assemble(
                ("you-decide", "bold"),
                ("  ·  ", "dim"),
                ("The model scores. The code decides. You judge.", "italic dim"),
            ),
            (0, 0, 1, 0),
        )
    )
    backend = load_laya(console)
    console.print()
    played = session(backend, args.rounds, console)
    report(played, console)
    if played:
        console.print(f"\n[dim]  Session saved to {save(played, args.save_dir)}[/]\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
