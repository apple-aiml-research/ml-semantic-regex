#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Detection metric from Eleuther's "Automatically Interpreting Millions of Features in Large Language Models"
# Paper: https://arxiv.org/pdf/2410.13928
# Code: https://github.com/EleutherAI/delphi
# This implementation is adapted from the Neuronpedia's implementation called eluether_recall: https://github.com/hijohnnylin/automated-interpretability and https://github.com/hijohnnylin/neuronpedia/

import util
from metrics import EleutherMetric
from prompts.metrics import metrics_eleuther_prompt


class Detection(EleutherMetric):
    """Detection metric."""

    def __init__(self, eval_model_name, data_model_name, is_semantic_regex, ignore_first_token, show_breaks, subject_model):
        super().__init__(eval_model_name, data_model_name, is_semantic_regex, ignore_first_token, show_breaks, subject_model=None)
        self.name = 'detection'

        self.match_prompt_fn = metrics_eleuther_prompt.detection_prompt
        self.match_cache = {}


    def compute(self, description, feature, logging):
        """Compute the detection metric from eleuther. Compares matches on positive and negative examples from the dataset."""
        result = {
            "value": 0,
            "parameters": self.parameters,
            "data": {
                "positive": [],
                "negative": [],
            },
        }

        if not self.is_in_match_cache(feature, description):
            if not self.is_in_data_cache(feature):
                # Pull activating and random examples from the dataset
                data_positive_tokens, data_positive_activations = feature.get_activating_examples_per_quantile(n_quantiles=self.n_quantiles, n_examples_per_quantile=self.n_samples // self.n_quantiles)
                n_negative_examples = len(data_positive_tokens) # Ensure equal number of positive and negative examples when there were not enough activating data
                data_negative_tokens, data_negative_activations = self.sample_dataset(feature, n_negative_examples)
                assert len(data_positive_tokens) == len(data_negative_tokens), f"Expected equal number of positive and negative examples, got {len(data_positive_tokens)} positive and {len(data_negative_tokens)} negative"
                if logging:
                    print(f"{self.name.upper()} - sampled {len(data_positive_tokens)} positive and {len(data_negative_tokens)} negative examples")
                data_positive_tokens, data_positive_activations = util.batch_snip_activations(data_positive_tokens, data_positive_activations, self.n_tokens_per_sample)
                data_negative_tokens, data_negative_activations = util.batch_snip_activations(data_negative_tokens, data_negative_activations, self.n_tokens_per_sample)
                self.add_to_data_cache(feature, data_positive_tokens, data_positive_activations, data_negative_tokens, data_negative_activations)

            # Format tokens back to text that will get fed to the match LLM
            data_positive_tokens, data_positive_activations, data_negative_tokens, data_negative_activations = self.get_data_from_cache(feature)
            data_positive_examples = util.format_data_strings(data_positive_tokens, self.show_breaks)
            data_negative_examples = util.format_data_strings(data_negative_tokens, self.show_breaks)
            assert len(data_positive_examples) == len(data_negative_examples) == len(data_positive_tokens), f"Expected {len(data_positive_tokens)} positive examples, got {len(data_positive_examples)} positive and {len(data_negative_examples)} negative"

            # Batch the matches into calls of n_examples_shown and get the responses at once
            data_positive_matches, data_negative_matches = self.batch_match(description, data_positive_examples, data_negative_examples, logging)
            assert len(data_positive_matches) == len(data_positive_tokens), f"Expected {len(data_positive_tokens)} positive matches, got {len(data_positive_matches)}"
            assert len(data_negative_matches) == len(data_negative_tokens), f"Expected {len(data_negative_tokens)} negative matches, got {len(data_negative_matches)}"
            self.add_to_match_cache(feature, description, data_positive_matches, data_negative_matches)

        # Pull results from the cache
        data_positive_tokens, data_positive_activations, data_negative_tokens, data_negative_activations = self.get_data_from_cache(feature)
        result["data"]["positive"] = [
            {'tokens': data_positive_tokens[i], 'activations': data_positive_activations[i], 'match': data_positive_matches[i]}
            for i in range(len(data_positive_examples))
        ]
        result["data"]["negative"] = [
            {'tokens': data_negative_tokens[i], 'activations': data_negative_activations[i], 'match': data_negative_matches[i]}
            for i in range(len(data_negative_examples))
        ]

        data_positive_matches, data_negative_matches = self.get_matches_from_cache(feature, description)
        assert len(data_positive_matches) == len(data_positive_tokens), f"Expected {len(data_positive_tokens)} positive matches, got {len(data_positive_matches)}"
        assert len(data_negative_matches) == len(data_negative_tokens), f"Expected {len(data_negative_tokens)} negative matches, got {len(data_negative_matches)}"

        print(f"{self.name.upper()} - {len(data_positive_examples)} data positive: {list(zip(data_positive_matches, data_positive_examples))}")
        print(f"{self.name.upper()} - {len(data_negative_examples)} data negative: {list(zip(data_negative_matches, data_negative_examples))}")

        # Compute the detection score
        detection_score = self.compute_score(data_positive_matches, data_negative_matches)
        result["value"] = detection_score
        print(f"{self.name.upper()}: {detection_score}\n")
        return detection_score, result

