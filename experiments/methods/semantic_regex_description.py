#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# LLM Sematnic Regex feature description method.

import os
import json
import numpy as np

import util
import features
from methods import FeatureDescription
from prompts.methods import semantic_regex_prompt


class SemanticRegex(FeatureDescription):
    """Semantic Regex feature description method."""

    def __init__(self, output_dir: str, seed: int, input_dir: str = None, subject_model: str = None):
        super().__init__(output_dir, seed, input_dir, subject_model)
        self.is_semantic_regex = True
        self.name = "semantic_regex"

        self.system_prompt = semantic_regex_prompt.SYSTEM

        self.temperature = 1.0
        self.top_p = 1.0


    def generate(
            self,
            feature: features.Feature,
            model_name: str,
            show_breaks: bool = True,
            logging: bool = False,
            activation_threshold: float = 0.3,
            n_data_examples: int = 10,
            n_tokens_per_sample: int = 32,
            sampling_method: str = 'top', # 'top', 'random', or 'quantile'
            **_
            ) -> dict:
        """Generate a semantic regex description for a given feature.
        Args:
            feature: The Feature object for which to generate a description.
            model_name: Name of the model used to generate the description.
            n_data_examples: Number of examples to use for metric computation.
            n_tokens_per_sample: Number of tokens to include for each example centered around the max activation
            show_breaks: Whether to include new line breaks in the examples.
            logging: Whether to print out generation details.
        Returns:
            A dictionary containing the feature, description, data examples, and evaluation results.
        """
        util.set_seed(self.seed)

        result = {
            "feature": {
                "model_id": feature.model_id,
                "layer": feature.layer,
                "index": int(feature.index),
            },
            "description": {
                "description": None,
                "description_id": None,
                "method": "semantic_regex",
                "parameters": {
                    "model_name": model_name,
                    "n_data_examples": n_data_examples,
                    "n_tokens_per_sample": n_tokens_per_sample,
                    "show_breaks": show_breaks,
                    "activation_threshold": activation_threshold,
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "sampling_method": sampling_method,
                },
                "data": {
                    "positive": [],
                },
            },
            "evaluation": {}
        }

        print('_________________________________________________________________')
        print(f"METHOD: {self.name}")
        print(f"FEATURE: {feature}\n")

        # Check if results already exist on disk
        if os.path.exists(self.result_input_filename(feature)):
            print(f"{self.name.upper()} - Accessing results from disk for feature {feature}")
            with open(self.result_input_filename(feature), "r") as f:
                result = json.load(f)
            print(f"DESCRIPTION: {result['description']['description']}\n")
            return result

        # Get the activating data examples
        positive_data = feature.get_activating_examples()
        if len(positive_data[0]) == 0 or len(positive_data[1]) == 0:
            raise ValueError(f"No activating examples found for feature {feature}")

        # Set up the prompt
        messages = semantic_regex_prompt.prompt()

        # Set up the new example to be labeled
        positive_tokens, positive_activations = util.remove_duplicate_snippets(*util.batch_snip_activations(*positive_data, length_in_tokens=n_tokens_per_sample))

        # Filter out examples with low activation that will not be highlighted
        max_positive_activation = max([max(activations) for activations in positive_activations])
        threshold = activation_threshold * max_positive_activation
        filtered_positive_tokens, filtered_positive_activations = [], []
        for tokens, activations in zip(positive_tokens, positive_activations):
            if max(activations) >= threshold:
                filtered_positive_tokens.append(tokens)
                filtered_positive_activations.append(activations)

        # Sample the correct number using the sampling stretegy
        if sampling_method == 'top': # Only show n_data_examples strings
            positive_tokens, positive_activations = filtered_positive_tokens[:n_data_examples], filtered_positive_activations[:n_data_examples]
        elif sampling_method == 'random': # Randomly sample n_data_examples strings
            if len(filtered_positive_tokens) <= n_data_examples:
                positive_tokens, positive_activations = filtered_positive_tokens, filtered_positive_activations
            else:
                sampled_indices = sorted(np.random.choice(len(filtered_positive_tokens), n_data_examples, replace=False))
                positive_tokens = [filtered_positive_tokens[i] for i in sampled_indices]
                positive_activations = [filtered_positive_activations[i] for i in sampled_indices]
        elif sampling_method == 'quantile':
            if len(filtered_positive_tokens) <= n_data_examples:
                positive_tokens, positive_activations = filtered_positive_tokens, filtered_positive_activations
            else:
                quantiles = np.linspace(0, 1, n_data_examples + 2)[1:-1]
                max_activations = [max(activations) for activations in filtered_positive_activations]
                sampled_indices = sorted([int(np.quantile(range(len(max_activations)), q, interpolation='nearest')) for q in quantiles])
                positive_tokens = [filtered_positive_tokens[i] for i in sampled_indices]
                positive_activations = [filtered_positive_activations[i] for i in sampled_indices]
        else:
            raise ValueError(f"Unknown sampling method: {sampling_method}")

        example = """
"""
        for i, (tokens, activations) in enumerate(zip(positive_tokens, positive_activations)):
            result["description"]["data"]["positive"].append({
                "tokens": tokens,
                "activations": activations,
            })
            text = util.format_activation_string(tokens, activations, False, False, True, show_breaks, threshold)
            example += f"{i+1}: {text.strip()}\n"
        messages.append(self.format_message("user", example))

        if logging:
            print(f"{self.name.upper()} PROMPT:")
            for message in messages:
                print(f"  Role: {message['role']}, Content: {message['content']}")
            print('\n')

        # Generate the description
        try:
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=self.temperature,
                top_p=self.top_p,
            )
            print('COST', response.usage.completion_tokens, response.usage.prompt_tokens, 'COST')
        except Exception as e:
            raise Exception(f"Error generating {self.name} description for model {model_name}: {e}")

        description = self.parse_response(response.choices[0].message.content)
        result["description"]["description"] = description
        result["description"]["description_id"] = response.id.split("chatcmpl-")[-1]

        print(f"{self.name.upper()}: {description}\n")

        return result

    def parse_response(self, response: str) -> str:
        """Get the semantic regex after the explanation."""
        if "SR: " in response:
            return response.split("SR: ")[-1].strip()
        else:
            raise ValueError(f"Could not find 'SR: ' in response: {response}")
