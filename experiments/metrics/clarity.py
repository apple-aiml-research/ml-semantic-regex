#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Clarity metrics from "FADE: Why Bad Descriptions Happen to Good Features"
# Paper: https://arxiv.org/pdf/2502.16994
# Code: https://github.com/brunibrun/FADE/

import numpy as np
from sklearn.metrics import roc_auc_score

import math
import util
from metrics import FADEMetric
import prompts.metrics.metrics_fade_prompt as fade_prompt


class Clarity(FADEMetric):
    """Clarity metric from FADE."""

    def __init__(self, eval_model_name, data_model_name, is_semantic_regex, ignore_first_token, show_breaks, subject_model):
        super().__init__(eval_model_name, data_model_name, is_semantic_regex, ignore_first_token, show_breaks, subject_model)
        self.name = 'clarity'

        # Prompts from the FADE paper
        self.generate_system_message = fade_prompt.GENERATION_NATURAL_LANGUAGE_SYSTEM
        if self.is_semantic_regex:
            self.generate_system_message = fade_prompt.GENERATION_SEMANTIC_REGEX_SYSTEM

        self.max_generation_runs = self.n_samples // 5 # 15 in FADE paper, changing to match number of samples, assumibng generating at least 5 unique data examples per call
        self.parameters.update({
            "max_generation_runs": self.max_generation_runs,
        })

    def generate_data(self, description: str, logging: bool):
        messages = [
            {"role": "system", "content": self.generate_system_message},
            {"role": "user", "content": f"Concept: {description}"}
        ]
        if logging:
            print(f"{self.name.upper()} DATA GENERATION PROMPT:")
            for message in messages:
                print(f"{message['role'].upper()}: {message['content']}\n")

        generated_data = set([])
        runs = 0
        while len(generated_data) < self.n_samples and runs < self.max_generation_runs:
            response = self.client.chat.completions.create(
                model=self.eval_model_name,
                messages=messages,
            )
            assert len(response.choices) == 1, "Expected exactly one completion from the model."
            data = self.parse_response_into_list(response.choices[0].message.content)
            generated_data.update(data)
        generated_data = list(generated_data)[:self.n_samples] # Trim to n_samples
        if len(generated_data) == 0:
            raise ValueError("No generated data")
        if logging:
            print(f"{self.name.upper()} - generated {len(generated_data)} data examples: {generated_data}\n")
        return generated_data

    def compute(self, description, feature, logging):
        """Compute the clarity metric from FADE. Measures how well the feature separates generated positive examples from random negative examples from the dataset."""
        result = {
            "value": 0,
            "parameters": self.parameters,
            "data": {
                "positive": [],
                "negative": [],
            }
        }

        print(f"{self.name.upper()} - computing for feature {str(feature)} with {'semantic regex' if self.is_semantic_regex else 'baseline'} description: {description}")

        # Generate positive examples using the eval model
        if not self.is_in_fade_generation_cache(feature, description):
            if logging:
                print(f"{self.name.upper()} - {str(feature)} not in generation cache, generating data")
            generated_positive_examples = self.generate_data(description, logging)
            if self.subject_model is not None:
                generated_positive_tokens, generated_positive_activations = feature.batch_query_feature_on_device(generated_positive_examples, self.subject_model, self.device)
            else:
                generated_positive_tokens, generated_positive_activations = feature.batch_query_feature(generated_positive_examples, self.ignore_first_token)
            util.batch_snip_activations(generated_positive_tokens, generated_positive_activations, length_in_tokens=self.n_tokens_per_sample)
            self.add_to_fade_generation_cache(feature, description, generated_positive_tokens, generated_positive_activations)
        generated_positive_tokens, generated_positive_activations = self.get_generations_from_fade_cache(feature, description)
        num_positives = len(generated_positive_tokens)
        if logging:
            print(f"{self.name.upper()} - {num_positives} generated positive examples with ~{len(generated_positive_tokens[0])} tokens each")

        # Sample negative examples from the dataset
        if not self.is_in_fade_data_cache(feature, 'negative'):
            if logging:
                print(f"{self.name.upper()} - {str(feature)} negatives not in data cache, sampling data")
            data_negative_tokens, data_negative_activations = self.fade_sample_negatives(feature, self.n_samples)
            self.add_to_fade_data_cache(feature, 'negative', data_negative_tokens, data_negative_activations)
        data_negatives = self.get_data_from_fade_cache(feature, 'negative')
        data_negative_tokens, data_negative_activations = data_negatives[0][:num_positives], data_negatives[1][:num_positives]
        if logging:
            print(f"{self.name.upper()} - {len(data_negative_tokens)} data negative examples with ~{len(data_negative_tokens[0])} tokens each")

        # Get the max activation for each generated positive and data negative example
        generated_positive_examples = util.format_data_strings(generated_positive_tokens, self.show_breaks)
        data_negative_examples = util.format_data_strings(data_negative_tokens, self.show_breaks)

        max_generated_positive_activations = [max(activation) for activation in generated_positive_activations]
        assert len(max_generated_positive_activations) == len(generated_positive_activations), f"Expected {len(generated_positive_activations)} max generated activations, got {len(max_generated_positive_activations)}"
        max_data_negative_activations = [max(activation) for activation in data_negative_activations]
        assert len(max_data_negative_activations) == len(data_negative_activations), f"Expected {len(data_negative_activations)} max data activations, got {len(max_data_negative_activations)}"

        print(f"{self.name.upper()} - {len(generated_positive_tokens)} generated positive: {list(zip(max_generated_positive_activations, generated_positive_examples))}")
        print(f"{self.name.upper()} - {len(data_negative_tokens)} data negative: {list(zip(max_data_negative_activations, data_negative_examples))}")

        for (tokens, activations) in zip(generated_positive_tokens, generated_positive_activations):
            result["data"]["positive"].append({
                "tokens": tokens,
                "activations": activations,
            })
        for (tokens, activations) in zip(data_negative_tokens, data_negative_activations):
            result["data"]["negative"].append({
                "tokens": tokens,
                "activations": activations,
            })

        # Compute the clarity metric
        labels = np.concatenate([np.ones(len(max_generated_positive_activations)), np.zeros(len(max_data_negative_activations))])
        activations = np.concatenate([max_generated_positive_activations, max_data_negative_activations])
        roc_auc = roc_auc_score(labels, activations)
        if math.isnan(roc_auc): # Handle NaN values when none (or all) of the data matches
            roc_auc = None
        clarity = float(abs(2 * roc_auc - 1))
        result["value"] = clarity
        print(f'{self.name.upper()}: {clarity}\n')
        return clarity, result
