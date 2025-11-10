#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Tests for features.py.

import pytest
from importlib import reload

# ------------------------- Test utilities & fixtures --------------------------

def mock_feature_info(f):
    return {
        "modelId": f.model_id, "layer": f.layer, "index": f.index,
        "model": {"layers": 48},
        "maxActApprox": 0.5,
        "activations": [
            {"tokens": ["hello", "world"], "values": [0.1, 0.2]},
            {"tokens": ["foo"], "values": [0.9]},
        ],
        "source": {
            "saelensConfig": {"d_sae": 4096}
        },
        "explanations": [
            {"explanationModelName": "modelA", "typeName": "method1", "description": "A1"},
            {"explanationModelName": "modelB", "typeName": "method2", "description": "B2"},
            {"explanationModelName": "modelC", "typeName": "method3", "description": "C31"},
            {"explanationModelName": "modelC", "typeName": "method3", "description": "C32"},
        ],
        "pos_str": ["good", "great"],
        "pos_values": [0.5, 0.8],
    }

class MockResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload
        self.error = payload.get("error") if payload else None

    def json(self):
        return self._payload


@pytest.fixture
def features_module(monkeypatch):
    """
    Import the module under test and hand it back so tests can reference
    its functions and types directly.
    """
    import features as mod
    reload(mod)
    return mod

# --------------------------------- Feature -----------------------------------

def test_feature_str_format(features_module):
    Feature = features_module.Feature
    f = Feature(model_id="gpt-foo", layer="layer-12", index=7)
    assert str(f) == "gpt-foo_layer-12_7"


def test_feature_to_dict(features_module):
    Feature = features_module.Feature
    f = Feature(model_id="gpt-foo", layer="layer-12", index=7)
    d = f.to_dict()
    assert d == {"model_id": "gpt-foo", "layer": "layer-12", "index": 7}

# ----------------------------- get_feature_info -------------------------------

def test_get_feature_info_success(features_module, monkeypatch):
    f = features_module.Feature("gpt-foo", "L12", 3)
    payload = mock_feature_info(f)

    def fake_get(url):
        assert url.endswith("/api/feature/gpt-foo/L12/3")
        return MockResponse(200, payload)

    monkeypatch.setattr("features.requests.get", fake_get)

    out = f.get_feature_info()
    assert out is payload


def test_get_feature_info_caches_and_returns(features_module, monkeypatch):
    f = features_module.Feature("gpt-foo", "L12", 3)
    payload = mock_feature_info(f)
    calls = {"count": 0}

    def fake_get(url):
        calls["count"] += 1
        assert url.endswith("/api/feature/gpt-foo/L12/3")
        return MockResponse(status_code=200, payload=payload)

    monkeypatch.setattr("features.requests.get", fake_get)

    # First call -> hits network
    resp1 = f.get_feature_info()
    assert calls["count"] == 1

    # Second call -> served from cache, no new network call
    resp2 = f.get_feature_info()
    assert resp2 is resp1
    assert calls["count"] == 1  # still one call


def test_get_feature_info_non_200_raises(features_module, monkeypatch):
    f = features_module.Feature("gpt-foo", "L12", 3)

    def fake_get(url):
        return MockResponse(503, {"error": "unavailable"})

    monkeypatch.setattr("features.requests.get", fake_get)

    with pytest.raises(Exception) as ei:
        f.get_feature_info()
    assert "Failed to get feature info for feature gpt-foo_L12_3" in str(ei.value)


def test_get_feature_info_none_json_raises(features_module, monkeypatch):
    f = features_module.Feature("gpt-foo", "L12", 3)

    def fake_get(url):
        return MockResponse(status_code=200, payload=None)

    monkeypatch.setattr("features.requests.get", fake_get)

    with pytest.raises(Exception) as ei:
        f.get_feature_info()
    # the code checks `response.json() is None or ... == 0`
    assert f"No activating data for feature {str(f)}" in str(ei.value)

def test_get_feature_info_zero_max_act_raises(features_module, monkeypatch):
    f = features_module.Feature("gpt-foo", "L12", 3)

    def fake_get(url):
        return MockResponse(status_code=200, payload={"maxActApprox": 0})

    monkeypatch.setattr("features.requests.get", fake_get)

    with pytest.raises(Exception) as ei:
        f.get_feature_info()
    assert f"No activating data for feature {str(f)}" in str(ei.value)

def test_cache_key_is_per_feature(features_module, monkeypatch):
    feature_a = features_module.Feature("gpt-foo", "L12", 0)
    feature_b = features_module.Feature("gpt-foo", "L12", 100)  # different index

    payload = mock_feature_info(feature_a)
    calls = {"count": 0}

    def fake_get(url):
        calls["count"] += 1
        return MockResponse(status_code=200, payload=payload)

    monkeypatch.setattr("features.requests.get", fake_get)

    feature_a.get_feature_info()
    feature_b.get_feature_info()  # should trigger second HTTP call due to diff key
    assert calls["count"] == 2


# -------------------------------- get_sae_size --------------------------------

def test_get_sae_size_happy_path(features_module, monkeypatch):
    f = features_module.Feature("m", "L1", 0)
    payload = mock_feature_info(f)

    def fake_get(url):
        return MockResponse(200, payload)

    monkeypatch.setattr("features.requests.get", fake_get)
    assert f.get_sae_size() == 4096


def test_get_sae_size_missing_or_zero_raises(features_module, monkeypatch):
    f = features_module.Feature("m", "L1", 0)

    # Case 1: missing keys
    def fake_get_missing(url):
        return MockResponse(200, {'maxActApprox': 1})  # no 'source' key
    monkeypatch.setattr("features.requests.get", fake_get_missing)
    with pytest.raises(ValueError) as ei:
        f.get_sae_size()
    assert "SAE size not found for feature m_L1_0" in str(ei.value)

    # Case 2: explicit zero
    def fake_get_zero(url):
        return MockResponse(200, {'maxActApprox': 1, "source": {"saelensConfig": {"d_sae": 0}}})
    monkeypatch.setattr("features.requests.get", fake_get_zero)
    with pytest.raises(ValueError):
        f.get_sae_size()


# --------------------------- get_model_num_layers -----------------------------

def test_get_model_num_layers_happy_path(features_module, monkeypatch):
    f = features_module.Feature("m", "L1", 0)
    payload = mock_feature_info(f)

    def fake_get(url):
        return MockResponse(200, payload)

    monkeypatch.setattr("features.requests.get", fake_get)
    assert f.get_model_num_layers() == 48


def test_get_model_num_layers_missing_or_zero_raises(features_module, monkeypatch):
    f = features_module.Feature("m", "L1", 0)

    def fake_get_missing(url):
        return MockResponse(200, {'maxActApprox': 1})
    monkeypatch.setattr("features.requests.get", fake_get_missing)
    with pytest.raises(ValueError) as ei:
        f.get_model_num_layers()
    assert "Model num layers not found for feature m_L1_0" in str(ei.value)

    def fake_get_zero(url):
        return MockResponse(200, {'maxActApprox': 1, "model": {"layers": 0}})
    monkeypatch.setattr("features.requests.get", fake_get_zero)
    with pytest.raises(ValueError):
        f.get_model_num_layers()


# --------------------- get_activating_examples() ---------------------------

def test_get_activating_examples_parses_tokens_and_values(features_module, monkeypatch):
    f = features_module.Feature("m", "L1", 0)
    payload = mock_feature_info(f)

    def fake_get(url):
        return MockResponse(200, payload)

    monkeypatch.setattr("features.requests.get", fake_get)

    tokens, activations = f.get_activating_examples()
    assert tokens == [["hello", "world"], ["foo"]]
    assert activations == [[0.1, 0.2], [0.9]]

def test_get_activating_examples_handles_missing_activations(features_module, monkeypatch):
    f = features_module.Feature("m", "L1", 0)
    payload = {
        "maxActApprox": 1,
        # activations omitted
        "explanations": [],
    }

    def fake_get(url):
        return MockResponse(200, payload)

    monkeypatch.setattr("features.requests.get", fake_get)

    with pytest.raises(Exception) as ei:
        f.get_activating_examples()


def test_get_activating_examples_per_quantile_even_sampling(features_module, monkeypatch):
    f = features_module.Feature("m", "L1", 0)
    payload = mock_feature_info(f)

    # Extend activations to 100 examples with increasing activation values
    payload["activations"] = [{"tokens": [f"token{i}"], "values": [i * 0.01]} for i in range(100)]

    def fake_get(url):
        return MockResponse(200, payload)

    monkeypatch.setattr("features.requests.get", fake_get)

    tokens, activations = f.get_activating_examples_per_quantile(n_quantiles=5, n_examples_per_quantile=3)
    assert len(tokens) == 15  # 5 quantiles * 3 examples each
    assert len(activations) == 15

    # Check that activations are roughly evenly distributed across quantiles
    quantile_bounds = [i * 20 for i in range(6)]  # 0-19, 20-39, ..., 80-99
    quantile_counts = [0] * 5
    for act in activations:
        act_value = act[0] * 100  # scale back to original index range
        for q in range(5):
            if quantile_bounds[q] <= act_value < quantile_bounds[q + 1]:
                quantile_counts[q] += 1
                break
    assert all(count > 0 for count in quantile_counts), "Each quantile should have at least one sampled example"


def test_get_positive_logits(features_module, monkeypatch):
    f = features_module.Feature("m", "L1", 0)
    payload = mock_feature_info(f)

    def fake_get(url):
        return MockResponse(200, payload)

    monkeypatch.setattr("features.requests.get", fake_get)

    tokens, logits = f.get_positive_logits()
    assert tokens == ["good", "great"]
    assert logits == [0.5, 0.8]

# --- Tests: .get_explanations() & .get_explanation() --------------------------

def test_get_explanations_returns_list(features_module, monkeypatch):
    f = features_module.Feature("m", "L1", 0)
    payload = mock_feature_info(f)

    def fake_get(url):
        return MockResponse(200, payload)

    monkeypatch.setattr("features.requests.get", fake_get)
    explanations = f.get_explanations()
    assert isinstance(explanations, list)
    assert len(explanations) == 4
    assert explanations[0]["explanationModelName"] == "modelA"

def test_get_explanation_selects_unique_match(features_module, monkeypatch):
    f = features_module.Feature("m", "L1", 0)
    payload = mock_feature_info(f)

    def fake_get(url):
        return MockResponse(200, payload)

    monkeypatch.setattr("features.requests.get", fake_get)
    result = f.get_explanation(model="modelA", method="method1")
    assert result["description"] == 'A1'

def test_get_explanation_raises_when_no_match(features_module, monkeypatch):
    f = features_module.Feature("m", "L1", 0)
    payload = mock_feature_info(f)

    def fake_get(url):
        return MockResponse(200, payload)

    monkeypatch.setattr("features.requests.get", fake_get)
    with pytest.raises(Exception) as ei:
        f.get_explanation(model="modelA", method="method2") # no such combo

    msg = str(ei.value)
    # The error should list available models and methods
    assert "No explanations found for model modelA and method method2" in msg
    assert "Available: [('modelA', 'method1'), ('modelB', 'method2'), ('modelC', 'method3'), ('modelC', 'method3')]." in msg

def test_get_explanation_multiple_matches_warns_and_returns_first(features_module, monkeypatch, capsys):
    f = features_module.Feature("m", "L1", 0)
    payload = mock_feature_info(f)

    def fake_get(url):
        return MockResponse(200, payload)

    monkeypatch.setattr("features.requests.get", fake_get)
    result = f.get_explanation(model="modelC", method="method3")
    captured = capsys.readouterr()
    assert "Warning: Multiple explanations found for model modelC and method method3" in captured.out
    assert result["description"] == 'C31'  # first in order


# ------------------------------- query_feature --------------------------------

def test_query_feature_posts_correct_payload_and_parses(features_module, monkeypatch):
    f = features_module.Feature("gpt-foo", "L12", 7)
    text = "Hello world"

    def fake_post(url, headers, json):
        # URL and headers
        assert url == "https://www.neuronpedia.org/api/activation/new"
        assert headers == {"Content-Type": "application/json"}

        # Payload shape and values
        assert json["feature"] == {
            "modelId": "gpt-foo",
            "source": "L12",
            "index": "7",  # NOTE: string index in request
        }
        assert json["customText"] == text

        return MockResponse(200, {"tokens": ["Hi", "there"], "values": [0.2, 0.3]})

    monkeypatch.setattr("features.requests.post", fake_post)

    tokens, acts = f.query_feature(text, ignore_first_token=False)
    assert tokens == ["Hi", "there"]
    assert acts == [0.2, 0.3]


def test_query_feature_requires_nonempty_text(features_module):
    f = features_module.Feature("id", "L0", 1)
    with pytest.raises(AssertionError) as ei:
        f.query_feature("", ignore_first_token=False)
    assert "Text must not be empty" in str(ei.value)


def test_query_feature_non_200_raises(features_module, monkeypatch):
    f = features_module.Feature("id", "L0", 1)

    def fake_post(url, headers, json):
        return MockResponse(500, {"error": "boom"})

    monkeypatch.setattr("features.requests.post", fake_post)

    with pytest.raises(Exception) as ei:
        f.query_feature("text", ignore_first_token=False)
    assert "Failed to query feature id_L0_1 with text text: 500" in str(ei.value)


def test_query_feature_asserts_tokens_present(features_module, monkeypatch):
    f = features_module.Feature("id", "L0", 1)

    def fake_post(url, headers, json):
        return MockResponse(200, {"tokens": [], "values": []})

    monkeypatch.setattr("features.requests.post", fake_post)

    with pytest.raises(AssertionError) as ei:
        f.query_feature("x", ignore_first_token=False)
    assert "No tokens returned from the API" in str(ei.value)


def test_query_feature_asserts_tokens_values_same_length(features_module, monkeypatch):
    f = features_module.Feature("id", "L0", 1)

    def fake_post(url, headers, json):
        return MockResponse(200, {"tokens": ["a", "b"], "values": [0.1]})

    monkeypatch.setattr("features.requests.post", fake_post)

    with pytest.raises(AssertionError) as ei:
        f.query_feature("x", ignore_first_token=False)
    assert "Tokens and activations must have the same length" in str(ei.value)


@pytest.mark.parametrize("first_token", ["<|endoftext|>", "<bos>"])
def test_query_feature_ignore_first_token_filters_bos_variants(features_module, monkeypatch, first_token):
    f = features_module.Feature("id", "L0", 1)

    def fake_post(url, headers, json):
        return MockResponse(200, {"tokens": [first_token, "real", "tokens"], "values": [0.0, 1.0, 2.0]})

    monkeypatch.setattr("features.requests.post", fake_post)

    tokens, acts = f.query_feature("x", ignore_first_token=True)
    assert tokens == ["real", "tokens"]
    assert acts == [1.0, 2.0]


def test_query_feature_no_ignore_keeps_all_tokens(features_module, monkeypatch):
    f = features_module.Feature("id", "L0", 1)

    def fake_post(url, headers, json):
        return MockResponse(200, {"tokens": ["<bos>", "kept"], "values": [0.4, 0.5]})

    monkeypatch.setattr("features.requests.post", fake_post)

    tokens, acts = f.query_feature("x", ignore_first_token=False)
    assert tokens == ["<bos>", "kept"]
    assert acts == [0.4, 0.5]


# ---------------------------- batch_query_feature -----------------------------

def test_batch_query_feature_calls_query_for_each_and_aggregates(features_module, monkeypatch):
    f = features_module.Feature("id", "L0", 1)
    texts = ["first", "second", "third"]
    calls = {"seen": []}

    def fake_query(self, text, ignore_first_token):
        calls["seen"].append((str(self), text, ignore_first_token))
        # Return different shapes to ensure aggregation preserves order
        return [text, "!"], [0.1, 0.2]

    monkeypatch.setattr(features_module.Feature, "query_feature", fake_query)

    tokens, acts = f.batch_query_feature(texts, ignore_first_token=True)
    assert tokens == [["first", "!"], ["second", "!"], ["third", "!"]]
    assert acts == [[0.1, 0.2], [0.1, 0.2], [0.1, 0.2]]

    # Ensure each text was passed through with the ignore flag
    assert calls["seen"] == [
        ("id_L0_1", "first", True),
        ("id_L0_1", "second", True),
        ("id_L0_1", "third", True),
    ]


def test_batch_query_feature_propagates_exceptions(features_module, monkeypatch):
    f = features_module.Feature("id", "L0", 1)
    texts = ["ok", ""]  # second will fail due to query_feature's assertion

    def fake_query(self, text, ignore_first_token):
        if not text:
            raise AssertionError("Text must not be empty")
        return ["ok"], [0.9]

    monkeypatch.setattr(features_module.Feature, "query_feature", fake_query)

    with pytest.raises(AssertionError):
        f.batch_query_feature(texts, ignore_first_token=False)


# ----------------------------------- steer -----------------------------------

def test_steer_posts_correct_payload_and_returns_outputs(features_module, monkeypatch):
    f = features_module.Feature("gpt-foo", "L12", 7)

    def fake_post(url, headers, json):
        assert url == "https://www.neuronpedia.org/api/steer"
        assert headers == {"Content-Type": "application/json"}

        # Validate key parts of the payload
        assert json["prompt"] == "compose a poem"
        assert json["modelId"] == "gpt-foo"
        assert isinstance(json["features"], list) and len(json["features"]) == 1
        feat = json["features"][0]
        assert feat == {
            "modelId": "gpt-foo",
            "layer": "L12",
            "index": 7,
            "strength": 1.25,
        }
        # Other fixed knobs present
        for k in ["temperature", "n_tokens", "freq_penalty", "seed", "strength_multiplier"]:
            assert k in json

        return MockResponse(200, {"STEERED": "compose a poem steered text", "DEFAULT": "baseline text"})

    monkeypatch.setattr("features.requests.post", fake_post)

    steered = f.steer(
        text="compose a poem", strength=1.25, num_tokens=20
    )
    assert steered == " steered text"


def test_steer_non_200_raises(features_module, monkeypatch):
    f = features_module.Feature("gpt-foo", "L12", 7)

    def fake_post(url, headers, json):
        return MockResponse(429, {"error": "rate limited"})

    monkeypatch.setattr("features.requests.post", fake_post)

    with pytest.raises(Exception) as ei:
        f.steer(text="x", strength=0.5, num_tokens=5)
    assert "Failed to steer feature gpt-foo_L12_7 with text x: 429" in str(ei.value)


# ----------------------------------- cache -----------------------------------

def test_get_activating_examples_uses_cached_response(features_module, monkeypatch):
    f = features_module.Feature("gpt-foo", "L12", 7)
    payload = mock_feature_info(f)

    calls = {"count": 0}
    def fake_get(url):
        calls["count"] += 1
        return MockResponse(200, payload)

    monkeypatch.setattr("features.requests.get", fake_get)

    # First call populates cache via get_activating_examples()
    tokens1, _ = f.get_activating_examples()
    assert calls["count"] == 1
    assert tokens1 == [["hello", "world"], ["foo"]]

    # Second call to get_explanations() should use cached response (no new HTTP)
    exp = f.get_explanations()
    assert calls["count"] == 1
    assert len(exp) == 4
