"""Interactive console front-end for the reporting agent.

Run with ``python -m ppt_agent`` (or the ``ppt-agent`` console script once
installed). Plain input lines are sent to the LLM agent; lines starting
with ``/`` are handled locally as deterministic shortcuts that don't cost
an LLM call (loading context documents, saving, listing slides, ...).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace

from ppt_agent.agent.core import ReportingAgent
from ppt_agent.config import AgentConfig
from ppt_agent.context.store import ContextStore
from ppt_agent.exceptions import PptAgentError
from ppt_agent.llm.factory import build_llm_client
from ppt_agent.presentation.manager import PresentationManager
from ppt_agent.tools import build_default_registry

_HELP_TEXT = """
Available commands:
  /new [template.pptx]   Start a new, empty presentation (optionally from a template)
  /open <path.pptx>      Open an existing presentation
  /save [path.pptx]      Save the current presentation
  /slides                List slides in the current presentation
  /context <path>        Load a document into context (.txt/.md/.docx/.pdf)
  /documents             List documents loaded into context
  /reset                 Clear the conversation history (keeps the presentation)
  /help                  Show this message
  /exit, /quit           Exit the agent

Anything else is sent to the agent as a natural-language request.
""".strip()


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
    parser.add_argument(
        "--base-url", dest="base_url", help="Base URL of an OpenAI-compatible endpoint."
    )
    parser.add_argument(
        "--api-key", dest="api_key", help="API key/token for the backend."
    )
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

    try:
        llm_client = build_llm_client(config)
    except PptAgentError as exc:
        print(f"Failed to initialize LLM backend: {exc}", file=sys.stderr)
        return 1

    presentation_manager = PresentationManager()
    context_store = ContextStore()
    tool_registry = build_default_registry(presentation_manager, context_store)

    def on_tool_call(name: str, arguments: dict) -> None:
        print(f"  -> {name}({_format_arguments(arguments)})")

    def on_tool_result(name: str, result: str) -> None:
        first_line = result.splitlines()[0] if result else ""
        print(f"     {first_line}")

    agent = ReportingAgent(
        llm_client=llm_client,
        tool_registry=tool_registry,
        max_tool_iterations=config.max_tool_iterations,
        on_tool_call=on_tool_call,
        on_tool_result=on_tool_result,
    )

    print(
        f"ppt_agent ready (provider={config.llm_provider}, model={config.model}). "
        "Type /help for commands, or just describe the presentation you want."
    )

    while True:
        try:
            user_input = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            should_exit = _handle_command(
                user_input, presentation_manager, context_store, agent
            )
            if should_exit:
                break
            continue

        try:
            reply = agent.send_user_message(user_input)
        except PptAgentError as exc:
            print(f"agent> [error] {exc}")
            continue

        print(f"agent> {reply}")

    return 0


def _handle_command(
    command_line: str,
    presentation_manager: PresentationManager,
    context_store: ContextStore,
    agent: ReportingAgent,
) -> bool:
    """Handle one leading-'/' command. Returns True if the REPL should exit."""
    parts = command_line.split(maxsplit=1)
    command = parts[0].lower()
    argument = parts[1].strip() if len(parts) > 1 else None

    if command in ("/exit", "/quit"):
        return True

    if command == "/help":
        print(_HELP_TEXT)

    elif command == "/new":
        presentation_manager.new(argument)
        print(f"Started a new presentation{f' from {argument}' if argument else ''}.")

    elif command == "/open":
        if not argument:
            print("Usage: /open <path.pptx>")
        else:
            try:
                presentation_manager.open(argument)
                print(f"Opened {argument}.")
            except PptAgentError as exc:
                print(f"[error] {exc}")

    elif command == "/save":
        try:
            saved_path = presentation_manager.save(argument)
            print(f"Saved to {saved_path}.")
        except PptAgentError as exc:
            print(f"[error] {exc}")

    elif command == "/slides":
        try:
            for slide in presentation_manager.list_slides():
                marker = " (active)" if slide["is_active"] else ""
                print(
                    f"[{slide['index']}]{marker} title='{slide['title']}' shapes={slide['shape_count']}"
                )
        except PptAgentError as exc:
            print(f"[error] {exc}")

    elif command == "/context":
        if not argument:
            print("Usage: /context <path to .txt/.md/.docx/.pdf>")
        else:
            try:
                document = context_store.add_document(argument)
                print(
                    f"Loaded {document.path.name} as {document.doc_id} ({len(document.text)} characters)."
                )
            except (FileNotFoundError, ValueError) as exc:
                print(f"[error] {exc}")

    elif command == "/documents":
        documents = context_store.list_documents()
        if not documents:
            print("No documents loaded.")
        for document in documents:
            print(
                f"{document.doc_id}: {document.path} ({len(document.text)} characters)"
            )

    elif command == "/reset":
        agent.reset()
        print("Conversation history cleared (presentation state is unaffected).")

    else:
        print(f"Unknown command '{command}'. Type /help for a list of commands.")

    return False


def _format_arguments(arguments: dict) -> str:
    return ", ".join(f"{key}={value!r}" for key, value in arguments.items())


if __name__ == "__main__":
    sys.exit(main())
