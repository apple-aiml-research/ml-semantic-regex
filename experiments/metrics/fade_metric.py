#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Base class for the metrics from "FADE: Why Bad Descriptions Happen to Good Features"
# Paper: https://arxiv.org/pdf/2502.16994
# Code: https://github.com/brunibrun/FADE/blob/f929405e2350bd9a8098fd29a828bb497f085e09/fade/default_config.yaml#L48

import re
import json
import random
import numpy as np
from typing import List, Tuple

import util
from metrics import Metric
from features import Feature
from prompts.metrics.metrics_fade_prompt import RATING_NATURAL_LANGUAGE_SYSTEM, RATING_SEMANTIC_REGEX_SYSTEM


class FADEMetric(Metric):
    """Base class for FADE metrics"""

    fade_data_cache = {}
    fade_generation_cache = {}
    fade_ratings_cache = {}

    def __init__(self, eval_model_name, data_model_name, is_semantic_regex, ignore_first_token, show_breaks, subject_model):
        super().__init__(eval_model_name, data_model_name, is_semantic_regex, ignore_first_token, show_breaks, subject_model)

        self.n_examples_per_call = 15 # From FADE implementation
        self.top_sampling_percentage = 0.2
        self.percentiles = [0, 50, 75, 95, 100]

        new_parameters = {
            "n_examples_per_call": self.n_examples_per_call,
            "n_samples": self.n_samples,
            "top_sampling_percentage": self.top_sampling_percentage,
            "percentiles": self.percentiles,
            "n_tokens_per_sample": self.n_tokens_per_sample,
        }
        self.parameters.update(new_parameters)

    def fade_sample_positives(self, feature: Feature) -> Tuple[List[List[str]], List[List[float]]]:
        """Sample data from the positive activating data according to FADE's sampling strategy."""
        activating_data = feature.get_activating_examples()
        tokens, activations = util.remove_duplicate_snippets(
            *util.batch_snip_activations(*activating_data, length_in_tokens=self.n_tokens_per_sample)
        )
        percentiles = sorted(self.percentiles, reverse=True) # Reverse percentiles because activation is sorted max to min
        indices = list(range(len(tokens)))
        percentile_indices = {}
        for i in range(len(percentiles) - 1):
            start_index = int(percentiles[i] / 100 * len(indices))
            end_index = int(percentiles[i + 1] / 100 * len(indices))
            percentile_indices[percentiles[i]] = indices[start_index:end_index]

        # Sample evenly from each percentile bin
        samples_per_percentile = int(self.n_samples * (1 - self.top_sampling_percentage) // (len(percentiles) - 1))
        sampled_indices = []
        for samples in percentile_indices.values():
            if len(samples) > samples_per_percentile:
                sampled_indices.extend(np.random.choice(samples, samples_per_percentile, replace=False).tolist())
            else:
                sampled_indices.extend(samples)

        # Sample the top activations
        remaining_samples = self.n_samples - len(sampled_indices)
        sampled_indices.extend(indices[:remaining_samples])
        unique_sampled_indices = list(set(sampled_indices))
        unique_sampled_indices.sort()

        return [tokens[i] for i in unique_sampled_indices], [activations[i] for i in unique_sampled_indices]

    def fade_sample_negatives(self, feature: Feature, n_samples: int) -> Tuple[List[List[str]], List[List[float]]]:
        data_negative = self.sample_dataset(feature, n_samples)
        data_negative_tokens, _ = util.remove_duplicate_snippets(
            *util.batch_snip_activations(*data_negative, length_in_tokens=self.n_tokens_per_sample)
        )
        data_negative_examples = util.format_data_strings(data_negative_tokens, self.show_breaks)
        if self.subject_model is not None:
            data_negative_tokens, data_negative_activations = feature.batch_query_feature_on_device(data_negative_examples, self.subject_model, self.device)
        else:
            data_negative_tokens, data_negative_activations = feature.batch_query_feature(data_negative_examples, self.ignore_first_token)
        return data_negative_tokens, data_negative_activations


    # ------- DATA AND CONCEPT MATCH SCORING -------

    def parse_ratings(self, response: str) -> dict:
        """Parse the ratings from the LLM response into a dict of {example_id: rating}."""
        pattern = r"\{.*?\}"
        match = re.search(pattern, response)
        if match is None:
            raise ValueError("No match found in string")
        ratings = json.loads(match.group(0))
        assert all(isinstance(rating, int) and 0 <= rating <= 2 for rating in ratings.values()), "Ratings must be integers between 0 and 2"
        return ratings

    def rate(self, description: str, examples: List[str], logging: bool) -> dict:
        """Rate a batch of examples using the LLM."""
        system_message = RATING_NATURAL_LANGUAGE_SYSTEM if not self.is_semantic_regex else RATING_SEMANTIC_REGEX_SYSTEM
        messages = [{"role": "system", "content": system_message}]

        batch_prompt = f"Concept: {description}\n" + "\n".join(examples)
        messages.append({"role": "user", "content": batch_prompt})
        if logging:
            print(f"{self.name.upper()} RATE PROMPT:")
            for message in messages:
                print(f"{message['role'].upper()}: {message['content']}\n")

        response = self.client.chat.completions.create(
                model=self.eval_model_name,
                messages=messages,
        )
        assert len(response.choices) == 1, "Expected exactly one completion from the model."
        ratings = self.parse_ratings(response.choices[0].message.content)
        return ratings

    def batch_rate(self, description: str, positive_examples: List[str], negative_examples: List[str], logging: bool) -> Tuple[List[int], List[int]]:
        """Batch the ratings into calls of n_examples_shown and merge the responses."""
        examples = positive_examples + negative_examples
        num_examples = len(examples)
        if logging:
            num_batches = (num_examples + self.n_examples_per_call - 1) // self.n_examples_per_call
            print(f"{self.name.upper()} - rating {num_examples} examples in {num_batches} batches of {self.n_examples_per_call}")
        prompts = [f"Sequence ID {key}: '{example}'" for key, example in enumerate(examples)]
        ratings = np.array([None] * num_examples)
        shuffled_indices = np.array((range(num_examples))) # Shuffle to avoid any ordering effects
        random.shuffle(shuffled_indices)

        for batch_i, batch_start in enumerate(range(0, num_examples, self.n_examples_per_call)):
            batch_indices = shuffled_indices[batch_start:batch_start + self.n_examples_per_call]
            batch_prompts = [prompts[i] for i in batch_indices]
            batch_ratings = self.rate(description, batch_prompts, logging)
            if logging:
                print(f"{self.name.upper()} - batch {batch_i} ratings: {batch_ratings}")
            for example_id, rating in batch_ratings.items():
                ratings[int(example_id)] = rating
        assert None not in ratings, "Some examples were not rated"

        positive_ratings = ratings[:len(positive_examples)].tolist()
        negative_ratings = ratings[len(positive_examples):].tolist()
        return positive_ratings, negative_ratings

    def filter_ratings(self, ratings: List[int]) -> List[int]:
        """Filter out indeterminately rated examples (1s) and convert to binary match (2 -> 1, 0 -> 0)."""
        keep_indices = [i for i, rating in enumerate(ratings) if rating == 0 or rating == 2]
        filtered_ratings = [1 if ratings[i] == 2 else 0 for i in keep_indices]
        return keep_indices, filtered_ratings

    # ------- DATA AND MATCH CACHING -------

    def is_in_fade_data_cache(self, feature: Feature, parity: str):
        """Check if a feature's data is in the data cache."""
        feature_str = str(feature)
        return feature_str in self.fade_data_cache and len(self.fade_data_cache[feature_str][parity]['tokens']) > 0

    def add_to_fade_data_cache(self, feature: Feature, parity: str, tokens: List[List[str]], activations: List[List[float]]):
        """Add a feature's data to the data cache."""
        assert len(tokens) == len(activations), "Expected equal number of tokens and activations"
        assert len(tokens[0]) == len(activations[0]), "Expected equal length of tokens and activations in each example"
        feature_str = str(feature)
        if feature_str not in self.fade_data_cache:
            self.fade_data_cache[feature_str] = {
                'positive': {
                    'tokens': [],
                    'activations': [],
                },
                'negative': {
                    'tokens': [],
                    'activations': [],
                },
            }
        self.fade_data_cache[feature_str][parity]['tokens'] = tokens
        self.fade_data_cache[feature_str][parity]['activations'] = activations

    def get_data_from_fade_cache(self, feature: Feature, partity: str):
        """Get a feature's data from the data cache."""
        feature_str = str(feature)
        assert feature_str in self.fade_data_cache, f"Feature not in data cache: {feature_str}"
        return (self.fade_data_cache[feature_str][partity]['tokens'],
                self.fade_data_cache[feature_str][partity]['activations'],)

    def is_in_fade_generation_cache(self, feature: Feature, description: str):
        """Check if a feature's data is in the data cache."""
        key = str(feature) + str(description)
        return key in self.fade_generation_cache

    def add_to_fade_generation_cache(self, feature: Feature, description: str, positive_tokens: List[List[str]], positive_activations: List[List[float]]):
        """Add a feature's data to the data cache."""
        key = str(feature) + str(description)
        if key not in self.fade_generation_cache:
            self.fade_generation_cache[key] = {
                'positive': {
                    'tokens': [],
                    'activations': [],
                },
            }
        self.fade_generation_cache[key]['positive']['tokens'] = positive_tokens
        self.fade_generation_cache[key]['positive']['activations'] = positive_activations

    def get_generations_from_fade_cache(self, feature: Feature, description: str):
        """Get a feature's data from the data cache."""
        key = str(feature) + str(description)
        assert key in self.fade_generation_cache, f"Feature not in data cache: {key}"
        return (self.fade_generation_cache[key]['positive']['tokens'],
                self.fade_generation_cache[key]['positive']['activations'])

    def is_in_ratings_cache(self, feature: Feature, description: str):
        """Check if a description is in the ratings cache for a feature."""
        feature_str = str(feature)
        return feature_str in self.fade_ratings_cache and description in self.fade_ratings_cache[feature_str]

    def add_to_ratings_cache(self, feature: Feature, description: str, positive_ratings: List[int], negative_ratings: List[int]):
        """Add a description to the ratings cache for a feature."""
        feature_str = str(feature)
        if feature_str not in self.fade_ratings_cache:
            self.fade_ratings_cache[feature_str] = {}
        if description not in self.fade_ratings_cache[feature_str]:
            self.fade_ratings_cache[feature_str][description] = {}
        self.fade_ratings_cache[feature_str][description]['positive'] = positive_ratings
        self.fade_ratings_cache[feature_str][description]['negative'] = negative_ratings

    def get_ratings_from_cache(self, feature: Feature, description: str):
        """Get ratings from the rating cache for a feature and description."""
        feature_str = str(feature)
        assert feature_str in self.fade_ratings_cache, f"Feature not in rating cache: {feature_str}"
        assert description in self.fade_ratings_cache[feature_str], f"Description not in rating cache for feature: {description}"
        return (self.fade_ratings_cache[feature_str][description]['positive'],
                self.fade_ratings_cache[feature_str][description]['negative'])
