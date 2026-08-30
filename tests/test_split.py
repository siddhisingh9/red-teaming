"""Enforces the train/test split discipline described in NOTES.md:
data/attacks/test.jsonl (families 5-6) must not be read before day 18 unless
the RT_ALLOW_TEST_SPLIT env var explicitly opts in.
"""

from __future__ import annotations

import importlib

import config


def test_test_split_is_gated_by_default(monkeypatch):
    monkeypatch.delenv("RT_ALLOW_TEST_SPLIT", raising=False)
    importlib.reload(config)
    assert config.ALLOW_TEST_SPLIT is False


def test_test_split_path_points_at_the_held_out_file():
    assert config.ATTACKS_TEST_PATH.name == "test.jsonl"
    assert config.ATTACKS_TRAIN_PATH.name == "train.jsonl"
    assert config.ATTACKS_TEST_PATH != config.ATTACKS_TRAIN_PATH
