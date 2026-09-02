"""Day 10 tests: attackers/build_index.py's FAISS IndexFlatIP over the
train-family corpus. Builds a real index once per test session (loading
sentence-transformers/all-MiniLM-L6-v2 isn't free, ~a few seconds) rather
than mocking the encoder -- the whole point of day 10's checkpoint is that
normalisation is actually correct, which a mock can't demonstrate."""

from __future__ import annotations

import pytest
from sentence_transformers import SentenceTransformer

import config
from attackers.build_index import MODEL_NAME, build_index, load_index, retrieve
from data_split import load_train


@pytest.fixture(scope="module")
def index_and_ids(tmp_path_factory):
    # Redirect the index/ids paths for the whole module so this never
    # touches (or depends on) whatever's already built at attackers/index.faiss.
    tmp_dir = tmp_path_factory.mktemp("faiss")
    orig_index_path, orig_ids_path = config.FAISS_INDEX_PATH, config.IDS_PATH
    config.FAISS_INDEX_PATH = tmp_dir / "index.faiss"
    config.IDS_PATH = tmp_dir / "ids.json"
    try:
        yield build_index()
    finally:
        config.FAISS_INDEX_PATH, config.IDS_PATH = orig_index_path, orig_ids_path


@pytest.fixture(scope="module")
def encoder():
    return SentenceTransformer(MODEL_NAME)


def _family_of(name: str, train_by_name: dict) -> str:
    return train_by_name[name].family


def test_index_covers_every_train_pattern_and_nothing_else(index_and_ids):
    index, ids = index_and_ids
    train = load_train()
    assert index.ntotal == len(train) == 40
    assert index.d == 384
    assert set(ids) == {p.name for p in train}


def test_index_never_leaks_a_test_family_id(index_and_ids):
    """The whole point of indexing load_train() instead of load_corpus():
    a test-family pattern id must never end up retrievable."""
    _, ids = index_and_ids
    test_family_prefixes = ("F5-", "F6-")  # obfuscated_encoding, structural_smuggling
    assert not any(i.startswith(test_family_prefixes) for i in ids)


def test_direct_override_query_returns_direct_override_in_top_3(index_and_ids, encoder):
    index, ids = index_and_ids
    train_by_name = {p.name: p for p in load_train()}

    hits = retrieve(
        "make the model ignore its previous instructions", index, ids, encoder, k=3
    )

    assert len(hits) == 3
    families = [_family_of(name, train_by_name) for name, _score in hits]
    assert "direct_override" in families


def test_scores_are_normalised_not_all_near_one(index_and_ids, encoder):
    """Scores near 1.0 across the board means normalisation was skipped --
    the day-10 checkpoint's own diagnostic for that bug."""
    index, ids = index_and_ids

    hits = retrieve(
        "make the model ignore its previous instructions", index, ids, encoder, k=3
    )

    scores = [score for _name, score in hits]
    assert all(-1.0 <= s <= 1.0 for s in scores)
    assert not all(s > 0.95 for s in scores)


def test_saved_index_round_trips_through_load_index(index_and_ids):
    index, ids = load_index()
    assert index.ntotal == 40
    assert len(ids) == 40
