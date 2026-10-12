"""Render docs/screenshot.svg from a real session with Laya and scripted input.

uv run python scripts/screenshot.py
"""

from pathlib import Path

from rich.console import Console
from rich.text import Text

from you_decide.cli import load_laya, report, session

SCRIPT = [
    "My running shoes arrived in the wrong size. Can I swap them for a size 10?",
    "y",
    "I paid for express delivery and it took five days. I want the shipping fee back.",
    "n",
    "2",
]


def main() -> None:
    console = Console(record=True, width=82, force_terminal=True)
    backend = load_laya(Console(stderr=True))
    answers = iter(SCRIPT)

    def ask(prompt: str) -> str:
        # Echo the typed answer, as a terminal would.
        answer = next(answers)
        console.print(Text.from_markup(prompt) + Text(answer, style="bold white"))
        return answer

    played = session(backend, 2, console, ask)
    report(played, console)
    out = Path(__file__).resolve().parent.parent / "docs" / "screenshot.svg"
    console.save_svg(str(out), title="you-decide")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
