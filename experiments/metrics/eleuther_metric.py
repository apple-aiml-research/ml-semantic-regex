#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Base class for the detection and fuzzing metrics from Eleuther's "Automatically Interpreting Millions of Features in Large Language Models"
# Paper: https://arxiv.org/pdf/2410.13928
# Code: https://github.com/EleutherAI/delphi
# This implementation is adapted from the Neuronpedia's implementation of the same method: https://github.com/hijohnnylin/automated-interpretability and https://github.com/hijohnnylin/neuronpedia/

import random
import numpy as np
from typing import List

from metrics import Metric
from features import Feature


class EleutherMetric(Metric):
    """Base class for Eleuther metrics"""
    data_cache = {}

    def __init__(self, eval_model_name, data_model_name, is_semantic_regex, ignore_first_token, show_breaks, subject_model):
        super().__init__(eval_model_name, data_model_name, is_semantic_regex, ignore_first_token, show_breaks, subject_model=None)

        self.n_examples_per_call = 5 # From Eleuther implementation
        self.n_quantiles = 10 # From Neuronpedia implementation
        self.temperature = 0.7 # From Neuronpedia implementation
        self.max_completion_tokens = 500 # From Neuronpedia implementation

        new_parameters = {
            "n_examples_per_call": self.n_examples_per_call,
            "n_quantiles": self.n_quantiles,
            "temperature": self.temperature,
            "max_completion_tokens": self.max_completion_tokens,
        }
        self.parameters.update(new_parameters)

    def compute_score(self, positive_matches: List[int], negative_matches: List[int]) -> float:
        """Compute the detection or fuzzing score as the average of the true positive rate and true negative rate."""
        true_labels = [1] * len(positive_matches) + [0] * len(negative_matches)
        predicted_labels = positive_matches + negative_matches
        true_positive_rate = sum(1 for true, pred in zip(true_labels, predicted_labels) if true == 1 and pred == 1) / len(positive_matches)
        true_negative_rate = sum(1 for true, pred in zip(true_labels, predicted_labels) if true == 0 and pred == 0) / len(negative_matches)
        score = (true_positive_rate + true_negative_rate) / 2
        return score

    def is_in_match_cache(self, feature: Feature, description: str):
        """Check if a description is in the match cache for a feature."""
        feature_str = str(feature)
        return feature_str in self.match_cache and description in self.match_cache[feature_str]

    def add_to_match_cache(self, feature: Feature, description: str, positive_matches: List[int], negative_matches: List[int]):
        """Add a description to the match cache for a feature."""
        feature_str = str(feature)
        if feature_str not in self.match_cache:
            self.match_cache[feature_str] = {}
        if description not in self.match_cache[feature_str]:
            self.match_cache[feature_str][description] = {}
        self.match_cache[feature_str][description]['positive'] = positive_matches
        self.match_cache[feature_str][description]['negative'] = negative_matches

    def get_matches_from_cache(self, feature: Feature, description: str):
        """Get matches from the match cache for a feature and description."""
        feature_str = str(feature)
        assert feature_str in self.match_cache, f"Feature not in match cache: {feature_str}"
        assert description in self.match_cache[feature_str], f"Description not in match cache for feature: {description}"
        return (self.match_cache[feature_str][description]['positive'],
                self.match_cache[feature_str][description]['negative'])

    def is_in_data_cache(self, feature: Feature):
        """Check if a feature's data is in the data cache."""
        feature_str = str(feature)
        return feature_str in self.data_cache

    def add_to_data_cache(self, feature: Feature, positive_tokens: List[List[str]], positive_activations: List[List[float]], negative_tokens: List[List[str]], negative_activations: List[List[float]]):
        """Add a feature's data to the data cache."""
        feature_str = str(feature)
        if feature_str not in self.data_cache:
            self.data_cache[feature_str] = {
                'positive': {
                    'tokens': [],
                    'activations': [],
                },
                'negative': {
                    'tokens': [],
                    'activations': [],
                },
            }
        self.data_cache[feature_str]['positive']['tokens'] = positive_tokens
        self.data_cache[feature_str]['positive']['activations'] = positive_activations
        self.data_cache[feature_str]['negative']['tokens'] = negative_tokens
        self.data_cache[feature_str]['negative']['activations'] = negative_activations

    def get_data_from_cache(self, feature: Feature):
        """Get a feature's data from the data cache."""
        feature_str = str(feature)
        assert feature_str in self.data_cache, f"Feature not in data cache: {feature_str}"
        return (self.data_cache[feature_str]['positive']['tokens'],
                self.data_cache[feature_str]['positive']['activations'],
                self.data_cache[feature_str]['negative']['tokens'],
                self.data_cache[feature_str]['negative']['activations'])


    # ------- DATA AND CONCEPT MATCH SCORING -------

    def parse_matches(self, response):
        matches = self.parse_response_into_list(response)
        matches = [int(match) for match in matches]
        assert all(isinstance(match, int) and match in [0, 1] for match in matches), f"Matches must be 0 or 1 but are {matches}"
        assert len(matches) == self.n_examples_per_call
        return matches

    def match(self, description: str, examples: List[str], logging: bool) -> List[int]:
        messages = self.match_prompt_fn(examples=examples, explanation=description, is_semantic_regex=self.is_semantic_regex)
        if logging:
            print(f"{self.name.upper()} MATCH PROMPT:")
            for message in messages:
                print(f"{message['role'].upper()}: {message['content']}\n")

        response = self.client.chat.completions.create(
                model=self.eval_model_name,
                messages=messages,
        )
        assert len(response.choices) == 1, "Expected exactly one completion from the model."
        matches = self.parse_matches(response.choices[0].message.content)
        return matches

    def batch_match(self, description: str, positive_examples: List[str], negative_examples: List[str], logging: bool):
        """Batch the matches into calls of n_examples_shown and merge the responses."""
        examples = positive_examples + negative_examples
        num_examples = len(examples)
        matches = np.array([None] * num_examples)
        shuffled_indices = np.array((range(num_examples))) # Shuffle to avoid any ordering effects
        random.shuffle(shuffled_indices)

        for batch_start in range(0, num_examples, self.n_examples_per_call):
            batch_indices = shuffled_indices[batch_start:batch_start + self.n_examples_per_call]
            batch_examples = [examples[i] for i in batch_indices]
            batch_matches = np.array(self.match(description, batch_examples, logging))
            matches[batch_indices] = batch_matches
        assert None not in matches, "Some examples were not classified"

        positive_matches = matches[:len(positive_examples)].tolist()
        negative_matches = matches[len(positive_examples):].tolist()
        return positive_matches, negative_matches