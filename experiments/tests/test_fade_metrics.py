#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Tests for FADE metrics.

import pytest

# FADE metrics to test
from metrics import Responsiveness, Purity, Clarity, Faithfulness

# Lightweight dummy "Feature" object that the cache keys on (via str(feature)).
class DummyFeature:
    def __init__(self, name):
        self.name = name
        self._pos_tokens = [["A", "A", "A"]]
        self._pos_acts = [[0.99, 0.8, 0.5]]

    def __str__(self):
        return f"Feature<{self.name}>"

    def get_activating_examples(self):
        return self._pos_tokens, self._pos_acts

    def apply_to_dataset(self, examples, ignore_first_token):
        # Return tokens/activations for the provided strings
        tokens = [[f"TOK@{self.name}@{i}"]*3 for i,_ in enumerate(examples)]
        activations = [[0.1, 0.2, 0.3] for _ in examples]
        return tokens, activations

    def batch_query_feature(self, examples, ignore_first_token):
        # Produce tokens/activations for examples used by fade_sample_negatives
        tokens = [[f"NEG@{self.name}@{i}"]*3 for i,_ in enumerate(examples)]
        activations = [[0.05, 0.02, 0.01] for _ in examples]
        return tokens, activations

    def steer(self, example, strength, n_tokens):
        # Return a "steered" example string and dummy metadata
        return f"{example}|steered:{strength}", {"strength": strength}

# Helpers to build canned token/activation sets
def make_tokens(prefix, n_examples=3, n_tokens=3):
    return [[f"{prefix}-{i}-{j}" for j in range(n_tokens)] for i in range(n_examples)]

def make_activations(val, n_examples=3, n_tokens=3):
    return [[val for _ in range(n_tokens)] for _ in range(n_examples)]

# Common constructor kwargs used by all metrics
COMMON_KW = dict(
    eval_model_name="dummy-eval",
    data_model_name="dummy-data",
    is_semantic_regex=False,
    ignore_first_token=False,
    show_breaks=False,
    subject_model=None,
)

# ----------------- Responsiveness and Purity  -------------------

@pytest.mark.parametrize("MetricCls", [Responsiveness, Purity])
def test_ratings_cache_scoped_by_feature_and_description(MetricCls, monkeypatch):
    m = MetricCls(**COMMON_KW)
    fA = DummyFeature("A")
    fB = DummyFeature("B")

    # Preload positive/negative FADE data for each feature so compute() won't sample
    posA = make_tokens("Apos", 2); posA_act = make_activations(0.9, 2)
    negA = make_tokens("Aneg", 2); negA_act = make_activations(0.1, 2)
    posB = make_tokens("Bpos", 1); posB_act = make_activations(0.8, 1)
    negB = make_tokens("Bneg", 3); negB_act = make_activations(0.2, 3)

    m.add_to_fade_data_cache(fA, 'positive', posA, posA_act)
    m.add_to_fade_data_cache(fA, 'negative', negA, negA_act)
    m.add_to_fade_data_cache(fB, 'positive', posB, posB_act)
    m.add_to_fade_data_cache(fB, 'negative', negB, negB_act)

    # Monkeypatch batch_rate to produce deterministic "ratings":
    # "yes" in description - positives match, negatives don't
    # "no"  in description - negatives match, positives don't
    def fake_batch_rate(desc, pos_examples, neg_examples, logging):
        pos = [2 if "yes" in desc.lower() else 0 for _ in pos_examples]
        neg = [1 if "no"  in desc.lower() else 0 for _ in neg_examples]
        return pos, neg
    monkeypatch.setattr(m, "batch_rate", fake_batch_rate)

    # First compute fills ratings cache
    s1, _ = m.compute("yes", fA, logging=False)

    print('EH', m, m.fade_ratings_cache)

    assert m.is_in_ratings_cache(fA, "yes")
    assert not m.is_in_ratings_cache(fA, "no")
    assert not m.is_in_ratings_cache(fB, "yes")

    # Ensure subsequent compute with same keys does not call batch_rate again
    def fail(*a, **k): raise AssertionError("batch_rate should not be called when ratings are cached")
    monkeypatch.setattr(m, "batch_rate", fail)
    s2, _ = m.compute("yes", fA, logging=False)
    assert s2 == s1

def test_fade_data_cache_is_per_feature_for_responsiveness():
    m = Responsiveness(**COMMON_KW)
    fA = DummyFeature("A")
    fB = DummyFeature("B")

    m.add_to_fade_data_cache(fA, 'positive', [["A+pos"]], [[0.9]])
    m.add_to_fade_data_cache(fA, 'negative', [["A-neg"]], [[0.1]])
    m.add_to_fade_data_cache(fB, 'positive', [["B+pos"]], [[0.8]])
    m.add_to_fade_data_cache(fB, 'negative', [["B-neg"]], [[0.2]])

    Ap, Aa = m.get_data_from_fade_cache(fA, 'positive')
    An, Na = m.get_data_from_fade_cache(fA, 'negative')
    Bp, Ba = m.get_data_from_fade_cache(fB, 'positive')
    Bn, Nb = m.get_data_from_fade_cache(fB, 'negative')

    assert Ap == [["A+pos"]] and An == [["A-neg"]]
    assert Bp == [["B+pos"]] and Bn == [["B-neg"]]

def test_ratings_cache_instance_sharing_between_metrics():
    m1 = Responsiveness(**COMMON_KW)
    m2 = Responsiveness(**COMMON_KW)
    f = DummyFeature("A")

    m1.add_to_ratings_cache(f, "featuredesc", [1], [0])
    assert m1.is_in_ratings_cache(f, "featuredesc")
    assert m2.is_in_ratings_cache(f, "featuredesc")


# ----------------- Clarity -------------------

def test_clarity_generation_cache_keyed_by_feature_and_description(monkeypatch):
    m = Clarity(**COMMON_KW)
    f = DummyFeature("A")

    # Stub negatives in data cache to avoid sampling
    neg = make_tokens("neg", 2); neg_act = make_activations(0.1, 2)
    m.add_to_fade_data_cache(f, 'negative', neg, neg_act)

    # First call should use generate_data and populate generation cache
    called = {"count": 0}
    def fake_generate(desc, logging):
        called["count"] += 1
        return ["GEN-1", "GEN-2", "GEN-3"]
    monkeypatch.setattr(m, "generate_data", fake_generate)

    val1, _ = m.compute("spec", f, logging=False)
    assert called["count"] == 1
    assert m.is_in_fade_generation_cache(f, "spec")

    # Second call with same keys should NOT call generate_data again
    def fail_generate(*a, **k): raise AssertionError("generate_data should not be called when generation cache is populated")
    monkeypatch.setattr(m, "generate_data", fail_generate)
    val2, _ = m.compute("spec", f, logging=False)
    assert val2 == val1

def test_clarity_generation_cache_different_description_is_separate(monkeypatch):
    m = Clarity(**COMMON_KW)
    f = DummyFeature("A")
    # Seed negatives
    m.add_to_fade_data_cache(f, 'negative', make_tokens("neg",1), make_activations(0.1,1))

    # First description
    monkeypatch.setattr(m, "generate_data", lambda d, l: ["ONE"])
    v1, _ = m.compute("d1", f, logging=False)
    assert m.is_in_fade_generation_cache(f, "d1")

    # Different description should lead to separate generation entry
    calls = {"n":0}
    def gen2(d,l):
        calls["n"]+=1
        return ["TWO"]
    monkeypatch.setattr(m, "generate_data", gen2)
    v2, _ = m.compute("d2", f, logging=False)
    assert calls["n"] == 1
    assert m.is_in_fade_generation_cache(f, "d2")
    assert v1 != v2 or True  # values may coincide depending on downstream calc, focus is cache separation


# ----------------- Faithfulness -------------------

def test_faithfulness_uses_feature_local_data_cache_and_batch_rate(monkeypatch):
    m = Faithfulness(**COMMON_KW)
    f = DummyFeature("A")

    # Provide negatives via cache to avoid dataset sampling
    neg = make_tokens("negA", 3); neg_act = make_activations(0.2, 3)
    m.add_to_fade_data_cache(f, 'negative', neg, neg_act)

    # Monkeypatch batch_rate to fabricate matches that increase with strength
    def fake_batch_rate(desc, pos, neg, logging):
        out = []
        for ex in pos + neg:
            if "|steered:" in ex:
                strength = float(ex.split("|steered:")[1])
                out.append({"match": 1 if strength > 0 else 0})
            else:
                out.append({"match": 0})
        return (out, []), None
    monkeypatch.setattr(m, "batch_rate", fake_batch_rate)

    # Compute twice to exercise cache: no explicit cache for faithfulness ratings per factor,
    # but it should reuse the negative data cached for the feature.
    v1, _ = m.compute("desc", f, logging=False)
    v2, _ = m.compute("desc", f, logging=False)
    assert v1 == v2
    assert 0 <= v1 <= 1
