"""Tests for the day 2 tools/sim.py stub: fixed poisoned response regardless
of input. Gets replaced once day 4 adds real per-case simulation."""

from __future__ import annotations

from schemas import ToolResponse
from tools.sim import call_tool


def test_call_tool_returns_fixed_poisoned_response():
    response = call_tool("any payload")
    assert isinstance(response, ToolResponse)
    assert "ignore all previous instructions" in response.content.lower()


def test_call_tool_ignores_its_input():
    assert call_tool("payload a") == call_tool("payload b")
