#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Faithfulness metrics from "FADE: Why Bad Descriptions Happen to Good Features"
# Paper: https://arxiv.org/pdf/2502.16994
# Code: https://github.com/brunibrun/FADE/

import time
import util
from metrics import FADEMetric

class Faithfulness(FADEMetric):
    """Faithfulness metric from FADE."""

    def __init__(self, eval_model_name, data_model_name, is_semantic_regex, ignore_first_token, show_breaks, subject_model):
        super().__init__(eval_model_name, data_model_name, is_semantic_regex, ignore_first_token, show_breaks, subject_model=subject_model)
        self.name = 'faithfulness'
        self.modification_factors = [0, 1, 10, 50]
        self.n_steered_generation_tokens = 30 # From FADE paper
        self.n_samples = 10 # Using fewer samples to reduce time and cost
        self.parameters.update({
            "modification_factors": self.modification_factors,
            "n_steered_generation_tokens": self.n_steered_generation_tokens,
            "n_samples": self.n_samples,
        })

    def compute(self, description, feature, logging):
        """Compute the faithfulness metric from FADE. Measures how the match rate changes as random examples are steered towards higher activation for the feature."""
        result = {
            "value": 0,
            "parameters": self.parameters,
            "data": {}, # map from steering factor to list of text and match
        }

        print(f"{self.name.upper()} - computing for feature {str(feature)} with {'semantic regex' if self.is_semantic_regex else 'baseline'} description: {description}")

        # Get the feature's max activation to determine steering strengths
        _, data_positive_activations = feature.get_activating_examples()
        max_activation = max(data_positive_activations[0]) # The first positive example should have the highest activation
        if logging:
            print(f"{self.name.upper()} - max activation for feature {str(feature)}: {max_activation}")

        # Get random examples from the dataset to steer
        if not self.is_in_fade_data_cache(feature, 'negative'):
            if logging:
                print(f"{self.name.upper()} - {str(feature)} not in data cache, sampling data")
            data_negative = self.sample_dataset(feature, self.n_samples)
            self.add_to_fade_data_cache(feature, 'negative', *data_negative)
        data_negative_tokens, _ = self.get_data_from_fade_cache(feature, 'negative')
        data_negative_examples = util.format_data_strings(data_negative_tokens, self.show_breaks)
        if logging:
            print(f"{self.name.upper()} - {len(data_negative_examples)} data negative examples: {data_negative_examples}")

        # Load the SAE once
        if self.subject_model is not None:
            sae, hook_name = feature.load_sae(self.device)

        # Steer each example and get the new results
        steered_texts_per_strength = []
        steered_matches_per_strength = []
        for modification_factor in self.modification_factors:
            strength = max_activation * modification_factor
            # Steer random examples (from dataset negative set)
            if self.subject_model is not None:
                steered_examples = feature.steer_on_device(data_negative_examples, strength, self.n_steered_generation_tokens, self.subject_model, self.device, sae, hook_name)
            else:
                steered_examples = []
                for data_negative_example in data_negative_examples:
                    try:
                        steered_example = feature.steer(data_negative_example, strength, self.n_steered_generation_tokens)
                    except Exception as e:
                        if str(e).endswith("429"): # Rate limit error
                            print("Steering rate limited, waiting 60 seconds...")
                            time.sleep(60)
                            steered_example = feature.steer(data_negative_example, strength, self.n_steered_generation_tokens)
                    steered_examples.append(steered_example)

            if logging:
                print(f"{self.name.upper()} - steered examples for factor {modification_factor} (strength {strength}): {steered_examples}")

            # Get the matches for the steered examples
            steered_ratings = self.batch_rate(description, steered_examples, [], logging)[0]
            keep_steered_indices, steered_matches = self.filter_ratings(steered_ratings)
            steered_examples = [steered_examples[i] for i in keep_steered_indices]
            if logging:
                print(f"{self.name.upper()} - steered examples after match filtering {modification_factor}: {list(zip(steered_matches, steered_examples))}")

            steered_texts_per_strength.append(steered_examples)
            steered_matches_per_strength.append(steered_matches)
            result['data'][modification_factor] = [
                {"text": steered_examples[i], "match": int(steered_matches[i])}
                for i in range(len(steered_examples))
            ]

        # Compute the faithfulness score
        if len(result['data'][0]) == 0:
            print(f"{self.name.upper()} - no data for modification factor 0, returning faithfulness of 0")
            result["value"] = 0
            return 0, result

        r0 = sum([r['match'] for r in result['data'][0]]) / len(result['data'][0])  # Proportion matched at strength 0
        r = [sum([r['match'] for r in result['data'][factor]]) / len(result['data'][factor]) if len(result['data'][factor]) > 0 else 0 for factor in self.modification_factors if factor != 0]  # Proportion matched at other strengths

        for i, factor in enumerate(self.modification_factors):
            print(f"{self.name.upper()} - factor {factor}: {list(zip([r['match'] for r in result['data'][factor]], [r['text'] for r in result['data'][factor]]))}")

        faithfulness = max(max(r) - r0, 0) / (1 - r0)
        result["value"] = faithfulness
        print(f"{self.name.upper()}: {faithfulness}\n")
        return faithfulness, result
