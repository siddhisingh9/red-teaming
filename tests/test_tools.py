"""Tests for tools/sim.py. Skipped until day 4 implements it."""

from __future__ import annotations

import pytest


def test_sim_tools_not_yet_implemented():
    from tools.sim import call_tool

    with pytest.raises(NotImplementedError):
        call_tool("noop", {})
