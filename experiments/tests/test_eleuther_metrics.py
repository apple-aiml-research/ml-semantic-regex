#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Tests for Eleuther metrics.

import pytest
from metrics.eleuther_metric import EleutherMetric

# Lightweight dummy "Feature" object that the cache keys on (via str(feature)).
class DummyFeature:
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return f"Feature<{self.name}>"

# Lightweight dummy metric subclass that uses EleutherMetric's cache utilities
class DummyMetric(EleutherMetric):
    def __init__(self):
        # Pass benign placeholders for the parent constructor
        super().__init__(
            eval_model_name="dummy-eval-model",
            data_model_name="dummy-data-model",
            is_semantic_regex=False,
            ignore_first_token=False,
            show_breaks=False,
            subject_model=None,
        )
        self.name = "dummy"
        self.match_cache = {}

    # A super-light "compute" that mirrors the cache flow:
    def compute(self, description, feature, logging=False):
        if self.is_in_match_cache(feature, description):
            pos_matches, neg_matches = self.get_matches_from_cache(feature, description)
        else:
            # Pull tokens from data cache, or fabricate simple data if missing
            if self.is_in_data_cache(feature):
                pos_tokens, _pos_act, neg_tokens, _neg_act = self.get_data_from_cache(feature)
            else:
                # Create deterministic "data" tied to the feature key
                key = str(feature)
                pos_tokens = [f"{key}-pos-0", f"{key}-pos-1", f"{key}-pos-2"]
                neg_tokens = [f"{key}-neg-0", f"{key}-neg-1", f"{key}-neg-2"]
                # Activations are irrelevant for the tests; keep same length
                self.add_to_data_cache(feature, pos_tokens, [1.0]*len(pos_tokens),
                                       neg_tokens, [0.0]*len(neg_tokens))

            # Deterministic "matcher": match positive tokens if description contains "yes"
            # and match negative tokens if description contains "no".
            pos_matches = [1 if "yes" in description.lower() else 0 for _ in pos_tokens]
            neg_matches = [1 if "no"  in description.lower() else 0 for _ in neg_tokens]

            self.add_to_match_cache(feature, description, pos_matches, neg_matches)

        return self.compute_score(pos_matches, neg_matches)


# ----------------- Eleuther metrics  -------------------

def test_compute_score_balanced():
    m = DummyMetric()
    # TPR = 3/4, TNR = 2/3 -> avg = (0.75 + 0.666...) / 2 = ~0.7083
    pos = [1, 0, 1, 1]
    neg = [0, 0, 1]
    score = m.compute_score(pos, neg)
    assert pytest.approx(score, rel=1e-6) == (0.75 + (2/3)) / 2

def test_match_cache_keyed_by_feature_and_description():
    m = DummyMetric()
    f = DummyFeature("A")
    # Preload the cache for description "foo"
    m.add_to_match_cache(f, "foo", [1, 1, 0], [0, 0, 1])

    # Should be present for (A, "foo"), but not for (A, "bar")
    assert m.is_in_match_cache(f, "foo") is True
    assert m.is_in_match_cache(f, "bar") is False

    # Cached retrieval returns what we inserted
    pos, neg = m.get_matches_from_cache(f, "foo")
    assert pos == [1, 1, 0]
    assert neg == [0, 0, 1]

def test_data_cache_isolated_per_feature():
    m = DummyMetric()
    fA = DummyFeature("A")
    fB = DummyFeature("B")

    # Add distinct data for A and B
    m.add_to_data_cache(fA,
                        positive_tokens=["A+1", "A+2"], positive_activations=[0.9, 0.8],
                        negative_tokens=["A-1"],         negative_activations=[0.1])
    m.add_to_data_cache(fB,
                        positive_tokens=["B+1"],         positive_activations=[0.7],
                        negative_tokens=["B-1", "B-2"],  negative_activations=[0.2, 0.1])

    # Ensure data retrieval is separated by feature key
    A_pos_toks, A_pos_act, A_neg_toks, A_neg_act = m.get_data_from_cache(fA)
    B_pos_toks, B_pos_act, B_neg_toks, B_neg_act = m.get_data_from_cache(fB)

    assert A_pos_toks == ["A+1", "A+2"]
    assert A_neg_toks == ["A-1"]
    assert B_pos_toks == ["B+1"]
    assert B_neg_toks == ["B-1", "B-2"]

def test_compute_uses_cached_matches_not_recomputing(monkeypatch):
    m = DummyMetric()
    f = DummyFeature("A")
    # Put some data in the data cache (so "compute" wouldn't fabricate it)
    m.add_to_data_cache(f,
                        positive_tokens=["p1", "p2", "p3"], positive_activations=[1,1,1],
                        negative_tokens=["n1", "n2", "n3"], negative_activations=[0,0,0])

    # First run with description "yes" populates the match cache
    score1 = m.compute("YES please", f)
    assert pytest.approx(score1, rel=1e-12) == 1.0

    # Now force a failure if "compute" tries to recompute matches
    def fail_if_called(*args, **kwargs):
        raise AssertionError("batch/match recomputation should NOT occur when matches are cached")
    monkeypatch.setattr(m, "add_to_match_cache", fail_if_called)

    # Second run with the SAME (feature, description) must hit cache and not attempt recomputation
    score2 = m.compute("YES please", f)
    assert pytest.approx(score2, rel=1e-12) == score1

def test_match_cache_is_per_instance_not_shared():
    # Two separate metric instances should not share match_cache
    m1 = DummyMetric()
    m2 = DummyMetric()
    f = DummyFeature("A")

    # Populate m1's cache only
    m1.add_to_match_cache(f, "q", [1,0,1], [0,1,0])
    assert m1.is_in_match_cache(f, "q") is True
    assert m2.is_in_match_cache(f, "q") is False

def test_same_feature_different_descriptions_have_separate_entries():
    m = DummyMetric()
    f = DummyFeature("A")
    # Populate data (so compute is deterministic)
    m.add_to_data_cache(f,
                        positive_tokens=["p1", "p2"], positive_activations=[1,1],
                        negative_tokens=["n1", "n2"], negative_activations=[0,0])

    # First description: matches "yes" - positives match
    s1 = m.compute("yes", f)
    # Second description: matches "no" - negatives match
    s2 = m.compute("no", f)

    # Ensure we created two different cached entries
    assert m.is_in_match_cache(f, "yes")
    assert m.is_in_match_cache(f, "no")
    pos_yes, neg_yes = m.get_matches_from_cache(f, "yes")
    pos_no,  neg_no  = m.get_matches_from_cache(f, "no")

    # For "yes", only positives match (1s), for "no", only negatives match (1s)
    assert pos_yes == [1, 1] and neg_yes == [0, 0]
    assert pos_no  == [0, 0] and neg_no  == [1, 1]

    # Scores should differ due to different predicted labels
    assert s1 != s2
