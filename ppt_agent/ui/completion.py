"""Tab-completion for REPL slash commands, via the stdlib ``readline`` module.

This is the dependency-free alternative to a live-filtering dropdown: it
can't render suggestions as you type (that needs a full terminal-rendering
library like prompt_toolkit), but pressing Tab after typing '/' lists
matching commands with their descriptions, and completes an unambiguous
prefix. ``readline`` isn't in the standard library on Windows, so this
degrades to no completion there instead of adding a new dependency.
"""

from __future__ import annotations

try:
    import readline
except ImportError:  # pragma: no cover - platform-dependent (e.g. Windows)
    readline = None


def enable_slash_command_completion(commands: dict[str, str]) -> None:
    """Enable Tab-completion of slash commands at the REPL prompt.

    Args:
        commands: Mapping of command name (e.g. "/help") to a short
            description, shown when Tab lists multiple matches.
    """
    if readline is None:
        return

    command_names = sorted(commands)

    def complete(text: str, state: int) -> str | None:
        if not text.startswith("/"):
            return None
        matches = [name for name in command_names if name.startswith(text)]
        return matches[state] if state < len(matches) else None

    def display_matches(substitution: str, matches: list[str], longest_match_length: int) -> None:
        print()
        for match in matches:
            print(f"  {match:<16} {commands.get(match, '')}")
        readline.redisplay()

    readline.set_completer(complete)
    readline.set_completion_display_matches_hook(display_matches)

    # libedit (macOS's system Python) and GNU readline use different
    # parse_and_bind syntax for the same "Tab triggers completion" binding.
    if "libedit" in (readline.__doc__ or ""):
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

    # '/' is a default word-break character, which would otherwise make
    # readline try to complete only the text after the last '/'.
    readline.set_completer_delims(readline.get_completer_delims().replace("/", ""))
