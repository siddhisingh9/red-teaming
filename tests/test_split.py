"""Enforces the train/test split discipline described in NOTES.md:
data/attacks/test.jsonl (families 5-6) must not be read before day 18 unless
allow_test=True is passed explicitly *and* RT_ALLOW_TEST_SPLIT=1 is set.

Also covers day 7's corpus itself: 60 patterns, 6 families, 10 each, zero
ID overlap in the corpus, and zero family overlap between train and test
(the split is by family, never by row -- a random row split would leak,
since payloads within a family are near-duplicates of each other).

Verifying those invariants requires this suite to read test.jsonl, which is
the one legitimate exception to "don't read it early": these tests check
the split's *shape* (families, ids), never its content, and every call
still goes through data_split.load_test()'s real guard via the
`opened_test_split` fixture below -- nothing here bypasses it.
"""

from __future__ import annotations

import importlib

import pytest

import config
import data_split
from schemas import AttackCase, CorpusPattern

TRAIN_FAMILIES = {"direct_override", "fake_system_message", "tool_call_emission", "context_hijack"}
TEST_FAMILIES = {"obfuscated_encoding", "structural_smuggling"}


@pytest.fixture
def opened_test_split(monkeypatch):
    """Opens both of load_test()'s gates for the duration of one test, then
    closes them again -- so the default-raise behavior isn't left disturbed
    for any test that runs after this one."""
    monkeypatch.setenv("RT_ALLOW_TEST_SPLIT", "1")
    importlib.reload(config)
    importlib.reload(data_split)
    yield
    monkeypatch.delenv("RT_ALLOW_TEST_SPLIT", raising=False)
    importlib.reload(config)
    importlib.reload(data_split)


def test_test_split_is_gated_by_default(monkeypatch):
    monkeypatch.delenv("RT_ALLOW_TEST_SPLIT", raising=False)
    importlib.reload(config)
    assert config.ALLOW_TEST_SPLIT is False


def test_test_split_path_points_at_the_held_out_file():
    assert config.ATTACKS_TEST_PATH.name == "test.jsonl"
    assert config.ATTACKS_TRAIN_PATH.name == "train.jsonl"
    assert config.ATTACKS_TEST_PATH != config.ATTACKS_TRAIN_PATH


def test_load_test_without_allow_test_raises():
    with pytest.raises(RuntimeError, match="allow_test=True"):
        data_split.load_test()


def test_load_test_with_allow_test_but_env_unset_still_raises(monkeypatch):
    monkeypatch.delenv("RT_ALLOW_TEST_SPLIT", raising=False)
    importlib.reload(config)
    importlib.reload(data_split)
    with pytest.raises(RuntimeError, match="RT_ALLOW_TEST_SPLIT"):
        data_split.load_test(allow_test=True)


def test_load_test_succeeds_only_with_both_gates_open(opened_test_split):
    records = data_split.load_test(allow_test=True)
    assert len(records) == 20


def test_corpus_has_60_records_6_families_10_each():
    corpus = data_split.load_corpus()
    assert len(corpus) == 60
    families: dict[str, int] = {}
    for record in corpus:
        families.setdefault(record.family, 0)
        families[record.family] += 1
    assert len(families) == 6
    assert all(count == 10 for count in families.values()), families


def test_corpus_ids_are_unique():
    corpus = data_split.load_corpus()
    ids = [record.id for record in corpus]
    assert len(ids) == len(set(ids))


def test_corpus_records_validate_against_corpus_pattern():
    corpus = data_split.load_corpus()
    assert all(isinstance(record, CorpusPattern) for record in corpus)


def test_train_and_test_have_zero_family_overlap(opened_test_split):
    train_families = {case.family for case in data_split.load_train()}
    test_families = {case.family for case in data_split.load_test(allow_test=True)}
    assert train_families & test_families == set()
    assert train_families == TRAIN_FAMILIES
    assert test_families == TEST_FAMILIES


def test_train_and_test_have_zero_id_overlap(opened_test_split):
    train_names = {case.name for case in data_split.load_train()}
    test_names = {case.name for case in data_split.load_test(allow_test=True)}
    assert train_names & test_names == set()
    assert len(train_names) == 40
    assert len(test_names) == 20


def test_train_and_test_records_validate_against_attack_case(opened_test_split):
    train = data_split.load_train()
    test = data_split.load_test(allow_test=True)
    assert all(isinstance(case, AttackCase) for case in train)
    assert all(isinstance(case, AttackCase) for case in test)
    assert len(train) + len(test) == 60


def test_split_is_a_reshape_of_the_same_corpus_ids(opened_test_split):
    """The 60 corpus IDs and the 60 train+test names must be the exact same
    set -- the split derives from the corpus, it doesn't drift from it."""
    corpus_ids = {record.id for record in data_split.load_corpus()}
    split_names = {case.name for case in data_split.load_train()} | {
        case.name for case in data_split.load_test(allow_test=True)
    }
    assert corpus_ids == split_names
