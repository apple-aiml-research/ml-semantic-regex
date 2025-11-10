#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Base class for feature description metrics.

import json
import os
import random
import features
import numpy as np
from openai import OpenAI
from typing import List
from abc import ABC, abstractmethod

from dotenv import load_dotenv
load_dotenv()

import util
import features


class Metric(ABC):
    """Abstract base class for metrics."""
    data_cache = {} # Share data generation across all metric computations

    def __init__(self, eval_model_name, data_model_name, is_semantic_regex, ignore_first_token, show_breaks, subject_model, seed=42):
        """A metric object is specific to its evaluation parameters."""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=openai_api_key)

        self.eval_model_name = eval_model_name
        self.data_model_name = data_model_name

        self.n_samples = 50 # For consistency between Eleuther and FADE
        self.n_tokens_per_sample = 32 # To match Eleuther's token length
        self.is_semantic_regex = is_semantic_regex
        self.ignore_first_token = ignore_first_token
        self.show_breaks = show_breaks

        self.seed = seed
        self.set_seed()

        self.parameters = {
            "evaluation_model_name": self.eval_model_name,
            "data_generation_model_name": self.data_model_name,
            "n_samples": self.n_samples,
            "n_tokens_per_sample": self.n_tokens_per_sample,
            "is_semantic_regex": self.is_semantic_regex,
            "ignore_first_token": ignore_first_token,
            "show_breaks": show_breaks,
            "seed": self.seed,
        }

        self.subject_model = subject_model
        if self.subject_model is not None:
            self.device = 'cuda'
            self.subject_model = subject_model


    @abstractmethod
    def compute(self, description, feature, **kwargs):
        pass

    def set_seed(self):
        random.seed(self.seed)
        np.random.seed(self.seed)

    # ------- DATA SAMPLING -------

    def sample_features(self, n_layers, n_features, feature):
        """Sample features from the same model, avoiding the given feature."""
        excluded_layer = int(feature.layer.split('-')[0])
        excluded_index = int(feature.index)
        feature_source = '-'.join(feature.layer.split('-')[1:])

        total_num_options = n_layers * n_features
        sampled_layer = excluded_layer
        sampled_index = excluded_index
        while sampled_layer == excluded_layer and sampled_index == excluded_index:
            sample = random.sample(range(total_num_options), 1)[0]
            sampled_layer = sample // n_features
            sampled_index = sample % n_features

        sampled_feature = features.Feature(
            feature.model_id,
            f"{sampled_layer}-{feature_source}",
            sampled_index,
        )
        return sampled_feature

    def sample_dataset(self, feature, n_data_examples):
        """Sample random examples from the dataset."""
        model_num_layers = feature.get_model_num_layers()
        sae_size = feature.get_sae_size()
        data_tokens, data_activations = [], []
        for _ in range(n_data_examples):
            tokens, activations = [], []
            while len(tokens) == 0: # Avoid features with no activating data
                try:
                    random_feature = self.sample_features(model_num_layers, sae_size, feature)
                    tokens, activations = random_feature.get_activating_examples()
                except: continue
            random_index = random.sample(range(len(tokens)), 1)[0]
            data_tokens.append(tokens[random_index])
            data_activations.append(activations[random_index])
        return data_tokens, data_activations

    def parse_response_into_list(self, response):
        """Parse LLM response into a list."""
        start = response.find('[')
        if start == -1:
            print(f"No '[' found in generated data response. {response}")
            return []

        try:
            value, end = json.JSONDecoder().raw_decode(response[start:])
        except json.JSONDecodeError as e:
            print(f"JSON parse failed: {e}\nExcerpt: {response[start:start+120]!r}")
            return []

        if not isinstance(value, list):
            print(f"Parsed JSON is not a list: {type(value)}")
            return []

        # Optionally ensure all elements are strings
        value = [str(x) for x in value]
        return value