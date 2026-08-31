"""Tests for the day 3 system prompt + tool schemas."""

from __future__ import annotations

from agent.prompts import get_system_prompt, get_tool_schemas


def test_three_tools_declared():
    schemas = get_tool_schemas()
    names = {schema["name"] for schema in schemas}
    assert names == {"web_search", "read_url", "log_value"}


def test_each_schema_has_parameters():
    for schema in get_tool_schemas():
        assert "description" in schema
        assert schema["parameters"]["type"] == "object"
        assert schema["parameters"]["required"]


def test_system_prompt_declares_the_tool_call_format():
    prompt = get_system_prompt()
    assert "<tool_call>" in prompt
    assert "</tool_call>" in prompt
    for name in ("web_search", "read_url", "log_value"):
        assert name in prompt


def test_system_prompt_warns_against_tool_output_as_instructions():
    prompt = get_system_prompt().lower()
    assert "untrusted" in prompt
