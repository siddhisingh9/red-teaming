"""Tests for the day 3 tool-calling loop: the tolerant parser
(agent.loop.parse_tool_call) and the generate -> parse -> execute ->
generate loop (agent.loop.run_agent). agent.model.generate is monkeypatched
throughout so these run on CPU without the real model."""

from __future__ import annotations

import pytest

from schemas import Outcome, ToolCall, ToolResponse
from agent.loop import AgentRunError, parse_tool_call, run_agent


# --- parse_tool_call ------------------------------------------------------


def test_parses_well_formed_json_strictly():
    text = '<tool_call>{"name": "web_search", "arguments": {"query": "x"}}</tool_call>'
    call = parse_tool_call(text)
    assert call == ToolCall(tool_name="web_search", arguments={"query": "x"})


def test_no_tag_means_final_answer():
    assert parse_tool_call("The answer is 42.") is None


def test_regex_fallback_tolerates_single_quotes():
    text = "<tool_call>{'name': 'web_search', 'arguments': {'query': 'x'}}</tool_call>"
    call = parse_tool_call(text)
    assert call == ToolCall(tool_name="web_search", arguments={"query": "x"})


def test_regex_fallback_tolerates_trailing_comma():
    text = '<tool_call>{"name": "log_value", "arguments": {"value": "x",}}</tool_call>'
    call = parse_tool_call(text)
    assert call == ToolCall(tool_name="log_value", arguments={"value": "x"})


def test_truncated_json_is_malformed():
    text = '<tool_call>{"name": "web_search", "arguments": {"query": "sta'
    assert parse_tool_call(text) is Outcome.MALFORMED


def test_missing_name_key_is_malformed():
    text = '<tool_call>{"arguments": {"query": "x"}}</tool_call>'
    assert parse_tool_call(text) is Outcome.MALFORMED


def test_gibberish_inside_tags_is_malformed():
    text = "<tool_call>not json at all</tool_call>"
    assert parse_tool_call(text) is Outcome.MALFORMED


# --- run_agent --------------------------------------------------------


def _stub_registry():
    return {
        "web_search": lambda query, injection=None: ToolResponse(
            tool_name="web_search", content="STUB_RESULT_42"
        )
    }


def test_run_agent_uses_tool_result_in_final_answer(monkeypatch):
    responses = iter(
        [
            '<tool_call>{"name": "web_search", "arguments": {"query": "status"}}</tool_call>',
            "Based on the search, STUB_RESULT_42 is the latest update.",
        ]
    )
    monkeypatch.setattr("agent.loop.generate", lambda messages: next(responses))

    messages, final_output, malformed = run_agent("look something up", _stub_registry())

    assert malformed is False
    assert "STUB_RESULT_42" in final_output
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "tool", "assistant"]
    assert messages[3]["content"] == "STUB_RESULT_42"


def test_run_agent_stops_as_soon_as_no_tool_call_appears(monkeypatch):
    calls = {"n": 0}

    def fake_generate(messages):
        calls["n"] += 1
        return "Here's my answer, no tool needed."

    monkeypatch.setattr("agent.loop.generate", fake_generate)

    messages, final_output, malformed = run_agent("hello", _stub_registry())

    assert calls["n"] == 1
    assert malformed is False
    assert final_output == "Here's my answer, no tool needed."


def test_run_agent_caps_at_max_iters(monkeypatch):
    monkeypatch.setattr(
        "agent.loop.generate",
        lambda messages: '<tool_call>{"name": "web_search", "arguments": {"query": "x"}}</tool_call>',
    )

    messages, final_output, malformed = run_agent("loop forever", _stub_registry(), max_iters=2)

    assert malformed is False
    assert len(messages) == 2 + 2 * 2  # system+user, then (assistant,tool) x2


def test_run_agent_short_circuits_on_malformed_tool_call(monkeypatch):
    calls = {"n": 0}

    def fake_generate(messages):
        calls["n"] += 1
        return "<tool_call>garbage</tool_call>"

    monkeypatch.setattr("agent.loop.generate", fake_generate)

    messages, final_output, malformed = run_agent("hello", _stub_registry())

    assert calls["n"] == 1
    assert malformed is True


def test_run_agent_preserves_transcript_when_a_tool_call_crashes(monkeypatch):
    monkeypatch.setattr(
        "agent.loop.generate",
        lambda messages: '<tool_call>{"name": "web_search", "arguments": {"query": "x"}}</tool_call>',
    )

    def broken_tool(query, injection=None):
        raise RuntimeError("tool blew up")

    with pytest.raises(AgentRunError) as excinfo:
        run_agent("hello", {"web_search": broken_tool})

    assert [m["role"] for m in excinfo.value.messages] == ["system", "user", "assistant"]
    assert isinstance(excinfo.value.cause, RuntimeError)


def test_run_agent_treats_unknown_tool_as_malformed(monkeypatch):
    monkeypatch.setattr(
        "agent.loop.generate",
        lambda messages: '<tool_call>{"name": "not_a_real_tool", "arguments": {}}</tool_call>',
    )

    messages, final_output, malformed = run_agent("hello", _stub_registry())

    assert malformed is True
