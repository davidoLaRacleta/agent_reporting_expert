"""ppt_agent: a console agent that builds and edits PowerPoint presentations.

The package is organized by role:

- ``llm``: pluggable connectors to a chat-completion backend (local or hosted).
- ``agent``: the conversation loop that turns user intent into tool calls.
- ``tools``: the concrete PowerPoint operations exposed to the LLM.
- ``presentation``: a stateful wrapper around ``python-pptx`` documents.
- ``context``: ingestion of source documents used to ground slide content.
"""

__version__ = "0.1.0"
