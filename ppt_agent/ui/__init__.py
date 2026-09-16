"""Rich-based terminal UI: banners, colored transcript lines, tables, spinners.

Kept separate from ``cli.py`` so the REPL's control flow (what happens on
each command) stays independent of how it's rendered. ``cli.py`` calls the
functions here instead of using ``print`` directly.
"""

from ppt_agent.ui.console import ConsoleUI

__all__ = ["ConsoleUI"]
