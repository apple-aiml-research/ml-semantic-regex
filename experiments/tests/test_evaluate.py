#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Tests for evaluate.py.

import sys
from types import SimpleNamespace
from dataclasses import dataclass
import pytest

# --- Stub metrics module ------------------------------------------------------

class _DummyMetricBase:
    def __init__(
        self,
        eval_model_name,
        data_model_name,
        is_semantic_regex,
        ignore_first_token,
        show_breaks,
        subject_model,
    ):
        # capture constructor args for assertions
        self.config = {
            "eval_model_name": eval_model_name,
            "data_model_name": data_model_name,
            "is_semantic_regex": is_semantic_regex,
            "ignore_first_token": ignore_first_token,
            "show_breaks": show_breaks,
            "subject_model": None,
        }
        # evaluator expects an attribute `name` used as result key
        self.name = self.__class__.__name__.lower()
        self._last_compute_args = None
        self._last_compute_kwargs = None

    def compute(self, description, feature, **kwargs):
        # record invocation to validate that logging is passed through
        self._last_compute_args = (description, feature)
        self._last_compute_kwargs = kwargs
        # return shape: (ignored, result)
        return ("ignored", f"{self.name}:{description}")


# Create concrete metric classes expected by evaluate.py
def _make_metric_cls(name):
    return type(name, (_DummyMetricBase,), {})

Clarity = _make_metric_cls("Clarity")
Responsiveness = _make_metric_cls("Responsiveness")
Detection = _make_metric_cls("Detection")
Fuzzing = _make_metric_cls("Fuzzing")
Purity = _make_metric_cls("Purity")
Faithfulness = _make_metric_cls("Faithfulness")


@pytest.fixture(autouse=True)
def stub_metrics_module(monkeypatch):
    """
    The code under test imports `from metrics import Clarity, Responsiveness, Detection, Fuzzing, Purity, Faithfulness`.
    Provide a stub `metrics` module exporting those symbols.
    """
    module_name = "metrics"
    stub = SimpleNamespace(
        Clarity=Clarity,
        Responsiveness=Responsiveness,
        Detection=Detection,
        Fuzzing=Fuzzing,
        Purity=Purity,
        Faithfulness=Faithfulness,
    )
    monkeypatch.setitem(sys.modules, module_name, stub)
    yield


# ----------------- Fixtures -------------------------------

@pytest.fixture
def evaluator_module():
    # Import evaluate.py after metrics has been stubbed
    from importlib import reload
    import evaluate as mod
    reload(mod)
    return mod


@pytest.fixture
def mk_evaluator(evaluator_module):
    def factory(
        metric_names,
        eval_model_name="eval-model",
        data_model_name="data-model",
        ignore_first_token=True,
        show_breaks=False,
        is_semantic_regex=False,
        logging={"sink": "stderr"},
    ):
        return evaluator_module.Evaluator(
            metric_names=metric_names,
            eval_model_name=eval_model_name,
            data_model_name=data_model_name,
            ignore_first_token=ignore_first_token,
            show_breaks=show_breaks,
            is_semantic_regex=is_semantic_regex,
            logging=logging,
        )
    return factory


# ----------------- metric construction --------------------------------

def test_unknown_metric_names_asserts(mk_evaluator):
    with pytest.raises(AssertionError) as ei:
        mk_evaluator(["clarity", "unknown_metric"])
    msg = str(ei.value)
    assert "Unknown metric names:" in msg
    assert "unknown_metric" in msg
    # Should also list available metrics
    assert "Available metrics:" in msg
    for expected in ["clarity", "responsiveness", "purity", "detection", "fuzzing", "faithfulness"]:
        assert expected in msg


def test_empty_metric_names_defaults_to_all_in_declared_order(mk_evaluator):
    ev = mk_evaluator([])
    # The order should follow the literal insertion order in available_metrics
    assert [m.name for m in ev.metrics] == [
        "clarity",
        "responsiveness",
        "purity",
        "detection",
        "fuzzing",
        "faithfulness",
    ]

    # Every metric instance should have been configured with the provided args
    for m in ev.metrics:
        assert m.config == {
            "eval_model_name": "eval-model",
            "data_model_name": "data-model",
            "is_semantic_regex": False,
            "ignore_first_token": True,
            "show_breaks": False,
            "subject_model": None,
        }


def test_subset_metric_names_constructs_only_requested_in_order(mk_evaluator):
    ev = mk_evaluator(["faithfulness", "clarity"])
    assert [m.name for m in ev.metrics] == ["faithfulness", "clarity"]


# ------------------------------- evaluate() ----------------------------------------

def test_evaluate_returns_results_by_metric_name_and_propagates_logging(mk_evaluator):
    custom_logging = {"sink": "file", "level": "INFO"}
    ev = mk_evaluator(["clarity", "detection"], logging=custom_logging)

    result = ev.evaluate(description="desc", feature={"id": 1})

    # Results keyed by metric.name, values are from compute()
    assert set(result.keys()) == {"clarity", "detection"}
    assert result["clarity"] == "clarity:desc"
    assert result["detection"] == "detection:desc"

    # Ensure evaluate() forwarded the logging kwarg to each metric.compute()
    for m in ev.metrics:
        assert m._last_compute_args == ("desc", {"id": 1})
        assert m._last_compute_kwargs.get("logging") is custom_logging


def test_constructor_args_wiring_all_flags_and_counts(mk_evaluator):
    ev = mk_evaluator(
        ["fuzzing"],
        eval_model_name="judge-1",
        data_model_name="dataset-X",
        ignore_first_token=False,
        show_breaks=True,
        is_semantic_regex=True,
        logging={"sink": "noop"},
    )
    (m,) = ev.metrics
    assert m.name == "fuzzing"
    assert m.config == {
        "eval_model_name": "judge-1",
        "data_model_name": "dataset-X",
        "is_semantic_regex": True,
        "ignore_first_token": False,
        "show_breaks": True,
        "subject_model": None,
    }


def test_duplicate_metric_names_last_result_wins(mk_evaluator, monkeypatch):
    ev = mk_evaluator(["clarity", "clarity"])

    # Make the two instances return different results so we can detect overwrite
    def first_compute(description, feature, **kwargs):
        return ("_", "first")
    def second_compute(description, feature, **kwargs):
        return ("_", "second")

    ev.metrics[0].compute = first_compute
    ev.metrics[1].compute = second_compute

    out = ev.evaluate("desc", feature=None)
    # Since both keys are 'clarity', the last compute() call should overwrite the first
    assert out == {"clarity": "second"}
