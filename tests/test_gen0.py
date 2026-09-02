"""Day 9 tests: gen0.py's planned-run list and, most importantly, the
resume path -- kill a sweep partway through, restart, and confirm it skips
completed run_ids and appends rather than duplicating or truncating. No
GPU and no real Gemini calls here: agent.loop.generate and
VanillaAttacker.generate are both monkeypatched, the same approach as
tests/test_loop.py and tests/test_vanilla.py."""

from __future__ import annotations

import json

import gen0
from attackers.vanilla import VanillaAttacker
from schemas import AttackCase, RunRecord

_FAKE_GOALS = [
    {
        "id": "T001",
        "tool_name": "web_search",
        "position": "top",
        "benign_task": "search for something",
        "goal": "goal text one",
    },
    {
        "id": "T002",
        "tool_name": "read_file",
        "position": "middle",
        "benign_task": "read something",
        "goal": "goal text two",
    },
]


def _fake_generate(self, goal, tool_name, seed):
    return AttackCase(
        name=f"fake-{tool_name}-{seed}",
        family="vanilla",
        technique="fake",
        injected_text=f"PAYLOAD for {goal} seed={seed}",
    )


def _patch_common(monkeypatch):
    monkeypatch.setattr(gen0, "GOALS", _FAKE_GOALS)
    monkeypatch.setattr(VanillaAttacker, "generate", _fake_generate)
    monkeypatch.setattr("agent.loop.generate", lambda messages: "no canary in this reply.")


# --- build_plan() ---------------------------------------------------------


def test_real_plan_has_120_runs_with_unique_sequential_ids():
    plan = gen0.build_plan()
    assert len(plan) == 120
    ids = [item["run_id"] for item in plan]
    assert len(set(ids)) == 120
    assert ids[0] == "g0-van-0001"
    assert ids[-1] == "g0-van-0120"


def test_plan_sweeps_all_three_positions_per_goal():
    plan = gen0.build_plan()
    from collections import Counter

    counts = Counter(item["goal"]["id"] for item in plan)
    assert set(counts.values()) == {3}  # every goal appears exactly 3 times (one per position)


# --- run_sweep(): shape and validation ------------------------------------


def test_sweep_writes_valid_run_records(tmp_path, monkeypatch):
    _patch_common(monkeypatch)
    log_path = tmp_path / "gen0.jsonl"

    records = gen0.run_sweep(log_path=log_path)

    assert len(records) == 6  # 2 fake goals x 3 positions
    for r in records:
        assert isinstance(r, RunRecord)
        assert r.attacker == "vanilla"
        assert r.generation == 0
        assert r.defender == "base"
        assert r.git_sha
        assert r.agent_model
        assert r.latency_s >= 0


def test_same_goal_across_positions_shares_one_generated_payload(tmp_path, monkeypatch):
    """One Gemini call per goal, not per (goal, position) -- the seed ties
    all 3 position variants of a goal back to the same payload."""
    calls = {"n": 0}
    orig = _fake_generate

    def counting_generate(self, goal, tool_name, seed):
        calls["n"] += 1
        return orig(self, goal, tool_name, seed)

    monkeypatch.setattr(gen0, "GOALS", _FAKE_GOALS)
    monkeypatch.setattr(VanillaAttacker, "generate", counting_generate)
    monkeypatch.setattr("agent.loop.generate", lambda messages: "no canary in this reply.")

    records = gen0.run_sweep(log_path=tmp_path / "gen0.jsonl")

    assert calls["n"] == 2  # once per goal, not once per (goal, position) = 6
    payloads_by_goal = {}
    for item, r in zip(gen0.build_plan(), records):
        payloads_by_goal.setdefault(item["goal"]["id"], set()).add(r.injected_text)
    assert all(len(v) == 1 for v in payloads_by_goal.values())


# --- the resume path -------------------------------------------------------


def test_resume_skips_completed_and_appends_without_duplicates(tmp_path, monkeypatch):
    _patch_common(monkeypatch)
    log_path = tmp_path / "gen0.jsonl"
    plan = gen0.build_plan()
    assert len(plan) == 6

    # a full, uninterrupted run
    gen0.run_sweep(log_path=log_path)
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 6

    # simulate a kill right after the 2nd record was flushed: truncate the
    # log to just what would have hit disk before the process died.
    log_path.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")

    new_records = gen0.run_sweep(log_path=log_path)
    assert len(new_records) == 4  # only the 4 not-yet-done runs happen again

    final_lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(final_lines) == 6  # no gaps
    run_ids = [json.loads(line)["run_id"] for line in final_lines]
    assert len(set(run_ids)) == 6  # no duplicates
    assert run_ids == [item["run_id"] for item in plan]  # same order as the plan


def test_resume_with_a_fully_completed_log_reruns_nothing(tmp_path, monkeypatch):
    _patch_common(monkeypatch)
    log_path = tmp_path / "gen0.jsonl"

    gen0.run_sweep(log_path=log_path)
    second_call_records = gen0.run_sweep(log_path=log_path)

    assert second_call_records == []
    assert len(log_path.read_text(encoding="utf-8").splitlines()) == 6


# --- report() --------------------------------------------------------------


def test_report_runs_without_error_on_a_real_sweep(tmp_path, monkeypatch, capsys):
    _patch_common(monkeypatch)
    log_path = tmp_path / "gen0.jsonl"
    records = gen0.run_sweep(log_path=log_path)

    gen0.report(records)

    out = capsys.readouterr().out
    assert "Gen-0 baseline ASR" in out
    assert "n=6" in out
