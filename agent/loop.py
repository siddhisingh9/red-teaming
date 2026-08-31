"""Day 3: multi-turn tool-calling loop.

generate -> parse -> (execute tool, generate again) -> ... capped at
MAX_ITERS, stopping as soon as a turn has no tool call in it.

The parser (parse_tool_call) is deliberately tolerant: small models emit
malformed JSON constantly. It tries strict json.loads first, then a regex
fallback that tolerates the common small-model mistakes (trailing commas,
single-quoted strings, nested braces, trailing commentary after the JSON
object), and only gives up -- marking the turn Outcome.MALFORMED -- if
neither works. Which path fired is logged so malformed generations are
debuggable later.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable

from pydantic import ValidationError

from agent.model import generate
from agent.prompts import get_system_prompt
from schemas import Outcome, Position, ToolCall, ToolResponse

logger = logging.getLogger(__name__)

MAX_ITERS = 3


class AgentRunError(Exception):
    """Raised when generate() or a tool call blows up mid-loop. Carries the
    transcript built so far -- losing that on a crash is exactly the kind of
    gap that makes a week-3 "how did this happen" question unanswerable."""

    def __init__(self, messages: list[dict[str, Any]], cause: BaseException) -> None:
        super().__init__(str(cause))
        self.messages = messages
        self.cause = cause

TOOL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)
_NAME_RE = re.compile(r'["\']name["\']\s*:\s*["\']([^"\']+)["\']')
_ARGS_KEY_RE = re.compile(r'["\']arguments["\']\s*:\s*')
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


def _extract_tool_call_block(text: str) -> str | None:
    """Pull the raw text between <tool_call> tags. Tolerates a missing or
    truncated closing tag -- small models cut off at max_new_tokens."""
    match = TOOL_RE.search(text)
    if match is not None:
        return match.group(1)
    start = text.find("<tool_call>")
    if start == -1:
        return None
    return text[start + len("<tool_call>"):].strip()


def _find_balanced_object(text: str, start: int) -> str | None:
    """Bracket-match a JSON object starting at text[start] == '{'. A plain
    regex can't handle nested braces (e.g. arguments containing an object);
    this is the part of the "regex fallback" tier that stands in for one."""
    if start >= len(text) or text[start] != "{":
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _regex_fallback(block: str) -> dict[str, Any] | None:
    """Loose extraction for JSON small models mangle: single quotes instead
    of double, a trailing comma, or commentary trailing the object."""
    name_match = _NAME_RE.search(block)
    if name_match is None:
        return None

    arguments: dict[str, Any] = {}
    args_key_match = _ARGS_KEY_RE.search(block)
    if args_key_match is not None:
        args_span = _find_balanced_object(block, args_key_match.end())
        if args_span is None:
            return None
        cleaned = _TRAILING_COMMA_RE.sub(r"\1", args_span)
        if "'" in cleaned and '"' not in cleaned:
            cleaned = cleaned.replace("'", '"')
        try:
            arguments = json.loads(cleaned)
        except json.JSONDecodeError:
            return None

    return {"name": name_match.group(1), "arguments": arguments}


def _to_tool_call(payload: Any) -> ToolCall | None:
    if not isinstance(payload, dict) or "name" not in payload:
        return None
    try:
        return ToolCall(tool_name=payload["name"], arguments=payload.get("arguments") or {})
    except ValidationError:
        return None


def parse_tool_call(text: str) -> ToolCall | None | Outcome:
    """Parse a model turn for a <tool_call>{...}</tool_call> block.

    Returns:
        ToolCall        -- a well-formed call was found.
        None            -- no <tool_call> tag at all; treat as a final answer.
        Outcome.MALFORMED -- a <tool_call> tag is present but nothing could
                             make sense of its contents.
    """
    block = _extract_tool_call_block(text)
    if block is None:
        return None

    try:
        call = _to_tool_call(json.loads(block))
        if call is not None:
            logger.info("tool_call parsed via strict json.loads")
            return call
    except json.JSONDecodeError:
        pass

    fallback_payload = _regex_fallback(block)
    if fallback_payload is not None:
        call = _to_tool_call(fallback_payload)
        if call is not None:
            logger.info("tool_call parsed via regex fallback")
            return call

    logger.warning("tool_call MALFORMED, no parser matched: %r", block)
    return Outcome.MALFORMED


def run_agent_from_messages(
    messages: list[dict[str, Any]],
    tool_registry: dict[str, Callable[..., ToolResponse]],
    injection: str | None = None,
    position: Position = "middle",
    max_iters: int = MAX_ITERS,
) -> tuple[list[dict[str, Any]], str, bool]:
    """Core loop: generate -> parse -> execute -> generate, capped at
    max_iters real generations, continuing from an existing message history
    (`messages` is mutated in place and also returned).

    This is the piece that lets a caller seed a conversation up to and
    including an already-poisoned tool response -- e.g. to pin down exactly
    which tool and splice position delivered the injection, rather than
    leaving that to whichever tool the model happens to call (see
    runner.py's controlled tool x position sweep). `run_agent` below is the
    convenience wrapper for the common case of starting fresh.

    `position` is forwarded to every tool call this loop itself executes --
    it's the knob for where in a tool's content the injection gets spliced
    (see tools/sim.py._splice). `injection` likewise: pass None here when
    the injection has already been delivered via a seeded tool response, so
    any further tool calls the agent makes on its own get a clean result
    instead of getting poisoned a second time.

    Returns (messages, final_output, malformed). `malformed` is True iff the
    loop stopped early because a tool call couldn't be parsed or named an
    unknown tool -- callers must map that straight to Outcome.MALFORMED
    rather than running it through canary.judge().
    """
    out = ""
    for _ in range(max_iters):
        try:
            out = generate(messages)
        except Exception as exc:
            raise AgentRunError(messages, exc) from exc
        messages.append({"role": "assistant", "content": out})

        call = parse_tool_call(out)
        if call is None:
            return messages, out, False
        if call is Outcome.MALFORMED:
            return messages, out, True

        tool_fn = tool_registry.get(call.tool_name)
        if tool_fn is None:
            logger.warning("tool_call MALFORMED, unknown tool %r", call.tool_name)
            return messages, out, True

        try:
            result = tool_fn(**call.arguments, injection=injection, position=position)
        except Exception as exc:
            raise AgentRunError(messages, exc) from exc
        messages.append({"role": "tool", "content": result.content})

    return messages, out, False


def run_agent(
    user_task: str,
    tool_registry: dict[str, Callable[..., ToolResponse]],
    injection: str | None = None,
    position: Position = "middle",
    max_iters: int = MAX_ITERS,
) -> tuple[list[dict[str, Any]], str, bool]:
    """Drive the loop from scratch: a fresh system prompt + user task. See
    run_agent_from_messages for the core loop and its parameters."""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": user_task},
    ]
    return run_agent_from_messages(
        messages, tool_registry, injection=injection, position=position, max_iters=max_iters
    )
