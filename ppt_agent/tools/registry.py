"""A minimal registry mapping tool names to schemas and Python callables.

The registry is intentionally provider-agnostic: it stores tool
definitions in OpenAI's function-calling JSON shape (name, description,
JSON-schema parameters), which every ``LLMClient`` backend already knows
how to adapt (see ``llm.anthropic_client._to_anthropic_tool`` for the one
backend that needs a translation).
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass
from typing import Callable

from ppt_agent.exceptions import ToolExecutionError


@dataclass
class ToolSpec:
    """A single registered tool: its schema plus the function that runs it."""

    name: str
    description: str
    parameters: dict
    handler: Callable[..., str]


class ToolRegistry:
    """Holds the tools currently available to the agent."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def add(
        self, name: str, description: str, parameters: dict, handler: Callable[..., str]
    ) -> None:
        """Register a tool. Raises if a tool with the same name already exists."""
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered.")
        self._tools[name] = ToolSpec(
            name=name, description=description, parameters=parameters, handler=handler
        )

    def schemas(self) -> list[dict]:
        """Return tool definitions in OpenAI function-calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters,
                },
            }
            for spec in self._tools.values()
        ]

    def dispatch(self, name: str, arguments: dict) -> str:
        """Run a registered tool by name and return its text result.

        Any exception raised by the handler is caught and turned into a
        descriptive string instead of propagating, since a tool failure
        should be reported back to the LLM (which can adjust and retry)
        rather than crash the whole agent loop.
        """
        spec = self._tools.get(name)
        if spec is None:
            return (
                f"Error: unknown tool '{name}'. Available tools: {sorted(self._tools)}."
            )

        try:
            return spec.handler(**arguments)
        except ToolExecutionError as exc:
            return f"Error: {exc}"
        except TypeError as exc:
            # Most commonly a missing/unexpected argument from the model.
            return f"Error: invalid arguments for tool '{name}': {exc}"
        except Exception as exc:  # noqa: BLE001 - last-resort guard around third-party calls
            return f"Error: tool '{name}' failed unexpectedly: {exc}\n{traceback.format_exc(limit=2)}"
