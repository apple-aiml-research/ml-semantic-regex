#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Responsiveness and Purity metrics from "FADE: Why Bad Descriptions Happen to Good Features"
# Paper: https://arxiv.org/pdf/2502.16994
# Code: https://github.com/brunibrun/FADE/

import math
from typing import List
from sklearn.metrics import roc_auc_score, average_precision_score

import util
from features import Feature
from metrics import FADEMetric

class FADENaturalExampleMetric(FADEMetric):
    """Base class for FADE metrics using natural examples: Responsiveness and Purity."""

    def __init__(self, eval_model_name, data_model_name, is_semantic_regex, ignore_first_token, show_breaks, subject_model):
        super().__init__(eval_model_name, data_model_name, is_semantic_regex, ignore_first_token, show_breaks, subject_model)

    def get_matches_and_activations(self, description: str, feature: Feature, logging: bool):
        """Compute the responsiveness metric from FADE."""
        result = {
            "value": 0,
            "parameters": self.parameters,
            "data": {
                "positive": [],
                "negative": [],
            },
        }

        print(f"{self.name.upper()} - computing for feature {str(feature)} with {'semantic regex' if self.is_semantic_regex else 'baseline'} description: {description}")

        # Get activating and non-activating samples from the dataset
        # To reduce the number of model calls, we sample using the FADE method on the known activating data and then sample an equal number of negative data from other features.
        if not self.is_in_fade_data_cache(feature, 'positive'):
            if logging:
                print(f"{self.name.upper()} - {str(feature)} positives not in data cache, sampling data")
            data_positive_tokens, data_positive_activations = self.fade_sample_positives(feature)
            self.add_to_fade_data_cache(feature, 'positive', data_positive_tokens, data_positive_activations)
        data_positive_tokens, data_positive_activations = self.get_data_from_fade_cache(feature, 'positive')
        data_positive_tokens, data_positive_activations = data_positive_tokens[:self.n_samples], data_positive_activations[:self.n_samples]

        num_positives = len(data_positive_tokens)
        if not self.is_in_fade_data_cache(feature, 'negative'):
            if logging:
                print(f"{self.name.upper()} - {str(feature)} negatives not in data cache, sampling data")
            data_negative_tokens, data_negative_activations = self.fade_sample_negatives(feature, self.n_samples)
            self.add_to_fade_data_cache(feature, 'negative', data_negative_tokens, data_negative_activations)
        data_negative_tokens, data_negative_activations = self.get_data_from_fade_cache(feature, 'negative')
        data_negative_tokens, data_negative_activations = data_negative_tokens[:num_positives], data_negative_activations[:num_positives]
        assert len(data_negative_tokens) == len(data_positive_tokens), f"Expected equal number of negative and positive samples, got {len(data_negative_tokens)} negatives and {len(data_positive_tokens)} positives"

        if logging:
            print(f"{self.name.upper()} - {len(data_positive_tokens)} data positive examples with ~{len(data_positive_tokens[0])} tokens each")
            print(f"{self.name.upper()} - {len(data_negative_tokens)} data negative examples with ~{len(data_negative_tokens[0])} tokens each")

        # Ask an LLM to classify each example using FADE's match method
        if not self.is_in_ratings_cache(feature, description):
            if logging:
                print(f"{self.name.upper()} - {str(feature)} and {description} not in match cache, matching data")
            data_positive_examples = util.format_data_strings(data_positive_tokens, self.show_breaks)
            data_negative_examples = util.format_data_strings(data_negative_tokens, self.show_breaks)
            data_positive_ratings, data_negative_ratings = self.batch_rate(description, data_positive_examples, data_negative_examples, logging)
            self.add_to_ratings_cache(feature, description, data_positive_ratings, data_negative_ratings)
        data_positive_ratings, data_negative_ratings = self.get_ratings_from_cache(feature, description)
        if logging:
            print(f"{self.name.upper()} - {len(data_positive_ratings)} data positive ratings: {data_positive_ratings}")
            print(f"{self.name.upper()} - {len(data_negative_ratings)} data negative ratings: {data_negative_ratings}")

        # Filter out indeterminately rated examples (1s)
        keep_positive_indices, data_positive_matches = self.filter_ratings(data_positive_ratings)
        data_positive_tokens = [data_positive_tokens[i] for i in keep_positive_indices]
        data_positive_activations = [data_positive_activations[i] for i in keep_positive_indices]
        data_positive_examples = util.format_data_strings(data_positive_tokens, self.show_breaks)

        keep_negative_indices, data_negative_matches = self.filter_ratings(data_negative_ratings)
        data_negative_tokens = [data_negative_tokens[i] for i in keep_negative_indices]
        data_negative_activations = [data_negative_activations[i] for i in keep_negative_indices]
        data_negative_examples = util.format_data_strings(data_negative_tokens, self.show_breaks)

        result["data"]["positive"] = [
            {'tokens': data_positive_tokens[i], 'activations': data_positive_activations[i], 'match': data_positive_matches[i]}
            for i in range(len(data_positive_tokens))
        ]
        result["data"]["negative"] = [
            {'tokens': data_negative_tokens[i], 'activations': data_negative_activations[i], 'match': data_negative_matches[i]}
            for i in range(len(data_negative_examples))
        ]

        print(f"{self.name.upper()} - {len(data_positive_examples)} data positive after matching and filtering: {list(zip(data_positive_matches, data_positive_examples))}")
        print(f"{self.name.upper()} - {len(data_negative_examples)} data negative after matching and filtering: {list(zip(data_negative_matches, data_negative_examples))}")

        matches = data_positive_matches + data_negative_matches
        activations = data_positive_activations + data_negative_activations
        return result, matches, activations


class Responsiveness(FADENaturalExampleMetric):
    """Responsiveness metric from FADE."""

    def __init__(self, eval_model_name, data_model_name, is_semantic_regex, ignore_first_token, show_breaks, subject_model):
        super().__init__(eval_model_name, data_model_name, is_semantic_regex, ignore_first_token, show_breaks, subject_model)
        self.name = 'responsiveness'
        self.match_method = 'detection'
        self.match_tokens = False

    def compute(self, description: str, feature: Feature, logging: bool):
        """Compute the responsiveness metric from FADE."""
        result, matches, activations = self.get_matches_and_activations(description, feature, logging)
        max_activations = [max(activation) for activation in activations]
        responsiveness = self.compute_gini_index(matches, max_activations)
        result["value"] = responsiveness
        print(f"{self.name.upper()}: {responsiveness}\n")
        return responsiveness, result

    def compute_gini_index(self, matches: List[int], max_activations: List[float]) -> float:
        """Compute the Gini index as a measure of responsiveness."""
        roc_auc = roc_auc_score(matches, max_activations)
        gini_index = float(abs(2 * roc_auc - 1))
        if math.isnan(gini_index): # Handle NaN values when none (or all) of the data matches
            gini_index = None
        return gini_index


class Purity(FADENaturalExampleMetric):
    """Purity metric from FADE."""

    def __init__(self, eval_model_name, data_model_name, is_semantic_regex, ignore_first_token, show_breaks, subject_model):
        super().__init__(eval_model_name, data_model_name, is_semantic_regex, ignore_first_token, show_breaks, subject_model)
        self.name = 'purity'
        self.match_method = 'detection'
        self.match_tokens = False

    def compute(self, description: str, feature: Feature, logging: bool):
        """Compute the responsiveness metric from FADE."""
        result, matches, activations = self.get_matches_and_activations(description, feature, logging)
        max_activations = [max(activation) for activation in activations]

        # Compute purity as average precision score
        purity = average_precision_score(matches, max_activations)
        result["value"] = purity
        if math.isnan(purity): # Handle NaN values when none (or all) of the data matches
            result["value"] = None
        print(f"{self.name.upper()}: {purity}\n")
        return purity, result
