#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Evaluator class to compute various metrics on feature descriptions.

from typing import List

from features import Feature
from metrics import Clarity, Responsiveness, Detection, Fuzzing, Purity, Faithfulness

class Evaluator():
    """Evaluator for computing metrics on feature descriptions."""

    def __init__(
            self,
            metric_names: List[str],
            eval_model_name: str,
            data_model_name: str,
            ignore_first_token: bool,
            show_breaks: bool,
            is_semantic_regex: bool,
            logging: bool,
            subject_model = None,
            **_
        ):
        """Initialize the evaluator with specified metrics and parameters.
        Args:
            metric_names: List of metric names to compute.
            eval_model_name: Name of the model used for evaluation.
            data_model_name: Name of the model used for generating data examples.
            ignore_first_token: Whether to ignore the activation of the first token if its a special token in the examples.
            show_breaks: Whether to include line breaks in the examples.
            is_semantic_regex: Whether the descriptions are semantic regexes or free-form text.
            logging: Whether to print out metric computation details.
            subject_model: Optional model name for on-device evaluations.
        """
        self.logging = logging
        available_metrics = {
            'clarity': Clarity,
            'responsiveness': Responsiveness,
            'purity': Purity,
            'detection': Detection,
            'fuzzing': Fuzzing,
            'faithfulness': Faithfulness,
        }

        assert all(name in available_metrics for name in metric_names), f"Unknown metric names: {[name for name in metric_names if name not in available_metrics]}. Available metrics: {list(available_metrics.keys())}"

        if len(metric_names) == 0:
            metric_names = list(available_metrics.keys())

        self.metrics = [
            available_metrics[name](
                eval_model_name,
                data_model_name,
                is_semantic_regex,
                ignore_first_token,
                show_breaks,
                subject_model=subject_model
            )
            for name in metric_names if name in available_metrics]


    def evaluate(self, description: str, feature: Feature) -> dict:
        """Compute all specified metrics on the given description and feature.
        Args:
            description: The feature description to evaluate.
            feature: The feature object associated with the description.
        Returns:
            A dictionary mapping metric names to their computed results.
        """
        metric_results = {}
        for metric in self.metrics:
            try:
                _, result = metric.compute(description, feature, logging=self.logging)
                metric_results[metric.name] = result
            except Exception as e:
                print(f"Error computing {metric.name} for feature {str(feature)}: {e}")
                continue
        return metric_results
