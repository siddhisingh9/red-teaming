"""Step 6: real model in the loop. Builds a trivial single-turn prompt from
the tool response and calls agent/model.py's generate(). No system prompt or
canary wiring yet, and no multi-turn tool-call handling -- that's day 3."""

from __future__ import annotations

from agent.model import generate
from schemas import AgentTurn, ToolResponse


def run(case_name: str, tool_response: ToolResponse) -> AgentTurn:
    messages = [{"role": "user", "content": tool_response.content}]
    content = generate(messages)
    return AgentTurn(role="assistant", content=content)
