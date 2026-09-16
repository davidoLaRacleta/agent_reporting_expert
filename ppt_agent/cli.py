"""Interactive console front-end for the reporting agent.

Run with ``python -m ppt_agent`` (or the ``ppt-agent`` console script once
installed). Plain input lines are sent to the LLM agent; lines starting
with ``/`` are handled locally as deterministic shortcuts that don't cost
an LLM call (loading context documents, saving, listing slides, ...).

All terminal rendering (colors, panels, tables, spinners) lives in
``ppt_agent.ui``; this module only owns the REPL's control flow.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace

from ppt_agent.agent.core import ReportingAgent
from ppt_agent.config import AgentConfig
from ppt_agent.context.store import ContextStore
from ppt_agent.exceptions import PptAgentError
from ppt_agent.llm.factory import build_chat_model
from ppt_agent.presentation.manager import PresentationManager
from ppt_agent.tools import build_default_tools
from ppt_agent.ui import ConsoleUI
from ppt_agent.ui.completion import enable_slash_command_completion

_COMMAND_ROWS = [
    ("/new [template.pptx]", "Start a new, empty presentation (optionally from a template)"),
    ("/open <path.pptx>", "Open an existing presentation"),
    ("/save [path.pptx]", "Save the current presentation"),
    ("/slides", "List slides in the current presentation"),
    ("/context <path>", "Load a document into context (.txt/.md/.docx/.pdf)"),
    ("/documents", "List documents loaded into context"),
    ("/reset", "Clear the conversation history (keeps the presentation)"),
    ("/help", "Show this message"),
    ("/exit, /quit", "Exit the agent"),
]

# Bare command names (as typed) mapped to a short description, for Tab-completion.
_COMMAND_NAMES = {
    "/new": "Start a new, empty presentation",
    "/open": "Open an existing presentation",
    "/save": "Save the current presentation",
    "/slides": "List slides in the current presentation",
    "/context": "Load a document into context",
    "/documents": "List documents loaded into context",
    "/reset": "Clear the conversation history",
    "/help": "Show available commands",
    "/exit": "Exit the agent",
    "/quit": "Exit the agent",
}


def build_arg_parser() -> argparse.ArgumentParser:
    """Define CLI flags that override AgentConfig defaults/env vars."""
    parser = argparse.ArgumentParser(
        prog="ppt-agent",
        description="Console agent for creating and editing PowerPoint presentations.",
    )
    parser.add_argument(
        "--provider",
        dest="llm_provider",
        choices=["openai_compatible", "anthropic"],
        help="LLM backend to use.",
    )
    parser.add_argument("--model", help="Model name/tag as understood by the backend.")
    parser.add_argument("--base-url", dest="base_url", help="Base URL of an OpenAI-compatible endpoint.")
    parser.add_argument("--api-key", dest="api_key", help="API key/token for the backend.")
    parser.add_argument("--temperature", type=float, help="Sampling temperature.")
    return parser


def load_config(argv: list[str] | None = None) -> AgentConfig:
    """Merge environment-derived config with any CLI flag overrides."""
    args = build_arg_parser().parse_args(argv)
    config = AgentConfig.from_env()
    overrides = {key: value for key, value in vars(args).items() if value is not None}
    return replace(config, **overrides)


def main(argv: list[str] | None = None) -> int:
    config = load_config(argv)
    ui = ConsoleUI()

    try:
        chat_model = build_chat_model(config)
    except PptAgentError as exc:
        ui.error(f"Failed to initialize LLM backend: {exc}")
        return 1

    presentation_manager = PresentationManager()
    context_store = ContextStore()
    tools = build_default_tools(presentation_manager, context_store)

    agent = ReportingAgent(
        chat_model=chat_model,
        tools=tools,
        max_tool_iterations=config.max_tool_iterations,
        on_tool_call=ui.tool_call,
        on_tool_result=ui.tool_result,
    )

    enable_slash_command_completion(_COMMAND_NAMES)
    ui.banner(config.llm_provider, config.model)

    while True:
        try:
            user_input = ui.read_user_input().strip()
        except (EOFError, KeyboardInterrupt):
            ui.console.print()
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            should_exit = _handle_command(user_input, presentation_manager, context_store, agent, ui)
            if should_exit:
                break
            continue

        try:
            with ui.thinking():
                reply = agent.send_user_message(user_input)
        except PptAgentError as exc:
            ui.error(str(exc))
            continue

        ui.agent_reply(reply)

    return 0


def _handle_command(
    command_line: str,
    presentation_manager: PresentationManager,
    context_store: ContextStore,
    agent: ReportingAgent,
    ui: ConsoleUI,
) -> bool:
    """Handle one leading-'/' command. Returns True if the REPL should exit."""
    parts = command_line.split(maxsplit=1)
    command = parts[0].lower()
    argument = parts[1].strip() if len(parts) > 1 else None

    if command in ("/exit", "/quit"):
        return True

    if command == "/help":
        ui.help(_COMMAND_ROWS)

    elif command == "/new":
        presentation_manager.new(argument)
        ui.success(f"Started a new presentation{f' from {argument}' if argument else ''}.")

    elif command == "/open":
        if not argument:
            ui.warning("Usage: /open <path.pptx>")
        else:
            try:
                presentation_manager.open(argument)
                ui.success(f"Opened {argument}.")
            except PptAgentError as exc:
                ui.error(str(exc))

    elif command == "/save":
        try:
            saved_path = presentation_manager.save(argument)
            ui.success(f"Saved to {saved_path}.")
        except PptAgentError as exc:
            ui.error(str(exc))

    elif command == "/slides":
        try:
            ui.slides_table(presentation_manager.list_slides())
        except PptAgentError as exc:
            ui.error(str(exc))

    elif command == "/context":
        if not argument:
            ui.warning("Usage: /context <path to .txt/.md/.docx/.pdf>")
        else:
            try:
                document = context_store.add_document(argument)
                ui.success(f"Loaded {document.path.name} as {document.doc_id} ({len(document.text)} characters).")
            except (FileNotFoundError, ValueError) as exc:
                ui.error(str(exc))

    elif command == "/documents":
        ui.documents_table(context_store.list_documents())

    elif command == "/reset":
        agent.reset()
        ui.success("Conversation history cleared (presentation state is unaffected).")

    else:
        ui.warning(f"Unknown command '{command}'. Type /help for a list of commands.")

    return False


if __name__ == "__main__":
    sys.exit(main())
