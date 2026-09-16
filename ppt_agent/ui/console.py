"""``ConsoleUI``: a thin, themed wrapper around ``rich.console.Console``.

Visual language, loosely modeled on Claude Code's transcript style:
a bullet ("⏺") marks each tool call, an indented corner ("⎿") marks its
result, and the agent's final reply is rendered as markdown in the
terminal's accent color. Everything here is presentation only -- no
business logic, no state beyond the underlying ``Console``.
"""

from __future__ import annotations

from contextlib import contextmanager

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

_BANNER_TITLE = "ppt_agent"
_MAX_ARG_VALUE_LENGTH = 60


class ConsoleUI:
    """Groups every piece of terminal output the CLI produces."""

    def __init__(self) -> None:
        self.console = Console(highlight=False)

    # -- startup / help -----------------------------------------------

    def banner(self, provider: str, model: str) -> None:
        body = Text()
        body.append("provider ", style="dim")
        body.append(provider, style="bold cyan")
        body.append("   model ", style="dim")
        body.append(model, style="bold cyan")
        body.append("\n")
        body.append("Type ", style="dim")
        body.append("/help", style="bold yellow")
        body.append(" for commands, or just describe the presentation you want.", style="dim")
        self.console.print(
            Panel(body, title=f"[bold magenta]{_BANNER_TITLE}[/bold magenta]", border_style="magenta", expand=False)
        )

    def help(self, command_rows: list[tuple[str, str]]) -> None:
        table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
        table.add_column(style="bold yellow")
        table.add_column(style="white")
        for command, description in command_rows:
            table.add_row(command, description)
        self.console.print(Panel(table, title="Commands", border_style="blue", expand=False))
        self.console.print("[dim]Anything else is sent to the agent as a natural-language request.[/dim]")

    # -- input -----------------------------------------------------------

    def read_user_input(self) -> str:
        """Print a styled prompt and read one line from stdin.

        Lets EOFError/KeyboardInterrupt propagate to the caller, which is
        responsible for exiting the REPL cleanly on Ctrl-D/Ctrl-C.
        """
        self.console.print("\n[bold blue]you[/bold blue] [dim]›[/dim] ", end="")
        return input()

    @contextmanager
    def thinking(self):
        """Context manager showing a spinner while the LLM is generating."""
        with self.console.status("[bold green]thinking…[/bold green]", spinner="dots"):
            yield

    # -- agent transcript --------------------------------------------------

    def tool_call(self, name: str, arguments: dict) -> None:
        formatted_args = ", ".join(f"{key}={_format_value(value)}" for key, value in arguments.items())
        self.console.print(f"  [bold magenta]⏺[/bold magenta] [white]{name}[/white][dim]({formatted_args})[/dim]")

    def tool_result(self, name: str, result: str) -> None:
        first_line = result.splitlines()[0] if result else ""
        style = "red" if first_line.startswith("Error") else "dim"
        self.console.print(f"    [dim]⎿[/dim] [{style}]{first_line}[/{style}]")

    def agent_reply(self, text: str) -> None:
        if not text.strip():
            return
        self.console.print("[bold green]⏺[/bold green] ", end="")
        self.console.print(Markdown(text))

    # -- status messages -------------------------------------------------

    def info(self, message: str) -> None:
        self.console.print(f"[cyan]{message}[/cyan]")

    def success(self, message: str) -> None:
        self.console.print(f"[green]✓[/green] {message}")

    def error(self, message: str) -> None:
        self.console.print(f"[bold red]✗[/bold red] [red]{message}[/red]")

    def warning(self, message: str) -> None:
        self.console.print(f"[yellow]{message}[/yellow]")

    # -- tables --------------------------------------------------------

    def slides_table(self, slides: list[dict]) -> None:
        if not slides:
            self.info("The presentation has no slides yet.")
            return
        table = Table(border_style="blue")
        table.add_column("#", justify="right")
        table.add_column("Title")
        table.add_column("Shapes", justify="right")
        table.add_column("Active", justify="center")
        for slide in slides:
            table.add_row(
                str(slide["index"]),
                slide["title"] or "[dim](untitled)[/dim]",
                str(slide["shape_count"]),
                "[green]●[/green]" if slide["is_active"] else "",
            )
        self.console.print(table)

    def documents_table(self, documents: list) -> None:
        if not documents:
            self.info("No documents loaded.")
            return
        table = Table(border_style="blue")
        table.add_column("doc_id")
        table.add_column("Path")
        table.add_column("Characters", justify="right")
        for document in documents:
            table.add_row(document.doc_id, str(document.path), str(len(document.text)))
        self.console.print(table)


def _format_value(value) -> str:
    text = repr(value)
    if len(text) > _MAX_ARG_VALUE_LENGTH:
        text = text[:_MAX_ARG_VALUE_LENGTH] + "…"
    return text
