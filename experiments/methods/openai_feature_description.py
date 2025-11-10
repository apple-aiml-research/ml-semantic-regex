#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# LLM feature description method replicating the method from OpenAI's "Language models can explain neurons in language models"
# Paper: https://openaipublic.blob.core.windows.net/neuron-explainer/paper/index.html
# Code: https://github.com/openai/automated-interpretability/tree/main
# This implementation is adapted from the Neuronpedia's implementation of the same paper: https://github.com/hijohnnylin/automated-interpretability and https://github.com/hijohnnylin/neuronpedia/

import os
import json
import numpy as np
from typing import List

import util
import features
from methods import FeatureDescription
from prompts.methods import oai_token_act_pair_prompt


class OAITokenActPair(FeatureDescription):
    """OpenAI's feature description method from "Language models can explain neurons in language models".
    Adapted from the Neuronpedia's implementation of the same method (oai_token-act-pair)."""

    def __init__(self, output_dir: str, seed: int, input_dir: str = None, subject_model = None):
        super().__init__(output_dir, seed, input_dir, subject_model)
        self.is_semantic_regex = False
        self.name = "oai_token-act-pair"

        self.system_message = oai_token_act_pair_prompt.SYSTEM
        self.example_inputs = oai_token_act_pair_prompt.EXAMPLES
        self.example_outputs = oai_token_act_pair_prompt.EXAMPLE_EXPLANATIONS

        # Paramters used in the original implementation
        self.n_few_shot_examples = len(self.example_inputs) # Taken directly from the OpenAI prompt
        self.n_data_examples = 5 # Parameter from OpenAI paper
        self.n_tokens_per_sample = 64 # Parameter from OpenAI paper
        self.temperature = 1.0 # Parameter from OpenAI paper
        self.max_completion_tokens = 4096 # Parameter from Neuronpedia implementation
        self.top_p = 1.0 # Parameter from Neuronpedia implementation
        self.show_breaks = True

    def generate(
            self,
            feature: features.Feature,
            model_name: str,
            logging: bool = False,
            **_
        ):

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
                "method": self.name,
                "parameters": {
                    "model_name": model_name,
                    "n_few_shot_examples": self.n_few_shot_examples,
                    "n_data_examples": self.n_data_examples,
                    "n_tokens_per_sample": self.n_tokens_per_sample,
                    "show_breaks": self.show_breaks
                },
                "data": {
                    "positive": [],
                },
            },
            "evaluation": {}
        }
        print('_________________________________________________________________')
        print(f"METHOD: {self.name}\n")
        print(f"FEATURE: {feature}\n")

        # Check if results already exist on disk
        if os.path.exists(self.result_input_filename(feature)):
            print(f"{self.name.upper()} - Accessing results from disk for feature {feature}")
            with open(self.result_input_filename(feature), "r") as f:
                result = json.load(f)
            print(f"DESCRIPTION: {result['description']['description']}\n")
            return result

        # Get the activating data examples
        data = feature.get_activating_examples()
        if len(data[0]) == 0 or len(data[1]) == 0:
            raise ValueError(f"No activating examples found for feature {feature}")
        tokens, activations = util.remove_duplicate_snippets(*util.batch_snip_activations(*data, length_in_tokens=self.n_tokens_per_sample))
        tokens, activations = tokens[:self.n_data_examples], activations[:self.n_data_examples] # Only show n_data_examples strings
        normalized_activations = self.normalize_activations(activations, max_value=10)
        assert max([max(a) for a in normalized_activations]) <= 10, "Normalized activations should be <= 10"
        assert min([min(a) for a in normalized_activations]) >= 0, "Normalized activations should be >= 0"

        # Set up the instructions and few shot examples for the model
        messages = [self.format_message('system', self.system_message)]
        for i in range(self.n_few_shot_examples):
            messages.append(self.format_message('user', self.example_inputs[i]))
            messages.append(self.format_message('assistant', self.example_outputs[i]))

        # Make the prompt to generate a descroption of this feature
        new_message = f"""\nNeuron {self.n_few_shot_examples + 1}\nActivations:"""
        for token_list, activation_list, normalized_activation_list in zip(tokens, activations, normalized_activations):
            new_message += self.format_example(token_list, normalized_activation_list)
            result["description"]["data"]["positive"].append({
                "tokens": token_list,
                "activations": activation_list,
            })

        new_message += f"\n\nExplanation of neuron {self.n_few_shot_examples+1} behavior: the main thing this neuron does is find"
        messages += [self.format_message('user', new_message)]

        if logging:
            print(f"{self.name.upper()} PROMPT:")
            for message in messages:
                print(f"  Role: {message['role']}, Content: {message['content']}")

        # Generate the description
        try:
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=self.temperature,
                max_completion_tokens=self.max_completion_tokens,
                top_p=self.top_p,
            )
            print('COST', response.usage.completion_tokens, response.usage.prompt_tokens, 'COST')
        except Exception as e:
            raise Exception(f"Error generating {self.name} description for model {model_name}: {e}")

        assert len(response.choices) == 1, "Expected exactly one completion from the model."
        description = response.choices[0].message.content
        result["description"]["description"] = description
        result["description"]["description_id"] = response.id.split("chatcmpl-")[-1]
        print(f"DESCRIPTION: {description}\n")
        return result

    def format_example(self, tokens: List[str], activations: List[float]) -> str:
        """Format a single example for the feature description method.
         Args:
             tokens: List of tokens.
             activations: List of corresponding activation values.
         Returns:
             A formatted string in the token<tab>activation format.
         """
        string = """\n<start>"""
        for token, activation in zip(tokens, activations):
            string += f"\n{token}\t{activation}"
        string += "\n<end>"
        return string

    def normalize_activations(self, activations: List[List[float]], max_value: int = 10) -> List[List[float]]:
        """Normalize activations between 0 and specified maximum value.
        Args:
            activations: A list of lists of activation values.
            max_value: The maximum value to normalize to.
        Returns:
            A list of lists of normalized activation values (ints). Negative activations are set to 0. Positive values are scaled to the range [0, max_value].
        """
        normalized_activations = []
        max_activation = max(activations[0])
        for activation_list in activations:
            normalized_activation_list = np.array(activation_list)
            normalized_activation_list[normalized_activation_list < 0] = 0
            normalized_activation_list /= max_activation
            normalized_activation_list *= max_value
            normalized_activation_list = np.floor(normalized_activation_list).astype(int).tolist()
            normalized_activations.append(normalized_activation_list)
        return normalized_activations
