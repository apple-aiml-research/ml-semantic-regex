#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# LLM feature description method replicating the default method from Eleuther's "Automatically Interpreting Millions of Features in Large Language Models"
# Paper: https://arxiv.org/pdf/2410.13928
# Code: https://github.com/EleutherAI/delphi
# This implementation is adapted from the Neuronpedia's implementation of the same method: https://github.com/hijohnnylin/automated-interpretability and https://github.com/hijohnnylin/neuronpedia/

import os
import re
import json
from typing import List

import util
import features
from methods import FeatureDescription
from prompts.methods import eleuther_acts_top20_prompt


class EleutherActsTop20(FeatureDescription):
    """Eleuther Acts Top 20 feature description method.
    Adapted from the EleutherAI Default Explainer in: https://github.com/EleutherAI/delphi/"""

    def __init__(self, output_dir: str, seed: int, input_dir: str = None, subject_model = None):
        super().__init__(output_dir, seed, input_dir, subject_model)
        self.is_semantic_regex = False
        self.name = "eleuther_acts_top20"

        self.system_message = eleuther_acts_top20_prompt.SYSTEM
        self.example_inputs = eleuther_acts_top20_prompt.EXAMPLES
        self.example_outputs = eleuther_acts_top20_prompt.EXAMPLE_EXPLANATIONS

        # Paramters used in the original implementation
        self.n_few_shot_examples = len(self.example_inputs) # Taken directly from the EleutherAI prompt
        self.n_data_examples = 20 # Parameter from Neuronpedia implementation
        self.n_tokens_per_sample = 32 # Parameter from EleutherAI implementation
        self.activation_threshold = 0.6 # Threshold for highlighting tokens (60% of max activation) from Neuronpedia implementation
        self.temperature = 0.7 # Parameter from Neuronpedia implementation
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
                    "show_breaks": self.show_breaks,
                    "activation_threshold": self.activation_threshold,
                    "temperature": self.temperature,
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

        # Set up the instructions and few shot examples for the model
        messages = [self.format_message("system", self.system_message)]
        for i in range(self.n_few_shot_examples):
            messages.append(self.format_message('user', self.example_inputs[i]))
            messages.append(self.format_message('assistant', self.example_outputs[i]))

        # Make the prompt to generate a description of this feature
        examples = []
        for i, (token_list, activation_list) in enumerate(zip(tokens, activations)):
            examples.append(f"EXAMPLE {i+1}: {self.format_example(token_list, activation_list)}")
            result["description"]["data"]["positive"].append({
                "tokens": token_list,
                "activations": activation_list,
            })
        examples = '\n'.join(examples)
        user_start = f"\n{examples}\n"
        messages.append(self.format_message('user', user_start))

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
            )
            print('COST', response.usage.completion_tokens, response.usage.prompt_tokens, "COST")
            description = self.parse_explanation(response.choices[0].message.content)
        except Exception as e:
            raise Exception(f"Error generating {self.name} description for model {model_name}: {e}")

        result["description"]["description"] = description
        result["description"]["description_id"] = response.id.split("chatcmpl-")[-1]
        print(f"DESCRIPTION: {description}\n")

        return result

    def format_example(self, tokens: List[str], activations: List[float]) -> str:
        """Format a single example for the feature description method. Taken directly from EleutherAI's Explainer._highlight().
         Args:
             tokens: List of tokens.
             activations: List of corresponding activation values.
         Returns:
             A formatted string with tokens that activate more than 60% of the max activation highlighted in << >>.
         """
        result = ""
        threshold = max(activations) * self.activation_threshold

        def check(i):
            return activations[i] > threshold

        i = 0
        while i < len(tokens):
            if check(i):
                result += "<<"

                while i < len(tokens) and check(i):
                    result += tokens[i]
                    i += 1
                result += ">>"
            else:
                result += tokens[i]
                i += 1

        return "".join(result).strip()

    def parse_explanation(self, text: str) -> str:
        """Parse the explanation from the model's response."""
        try:
            match = re.search(r"\[EXPLANATION\]:\s*(.*)", text, re.DOTALL)
            if match:
                return match.group(1).strip()
            else:
                raise Exception(f"Explanation parsing regex failed: {repr(e)}")
        except Exception as e:
            raise Exception(f"Explanation parsing regex failed: {repr(e)}")
