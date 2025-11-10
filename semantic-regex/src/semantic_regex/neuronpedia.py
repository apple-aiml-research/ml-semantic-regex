#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

"""Neuronpedia API integration for semantic regex generation."""

import requests
from typing import List, Tuple
from . import util


class Feature:
    """A minimal feature class for accessing Neuronpedia data."""

    def __init__(self, model_id: str, layer: str, index: int):
        self.model_id = model_id
        self.layer = layer
        self.index = index
        self.cache = {}

    def __str__(self) -> str:
        return f"{self.model_id}_{self.layer}_{self.index}"

    def get_feature_info(self) -> dict:
        """Get feature info from Neuronpedia API."""
        cache_key = str(self)
        if cache_key not in self.cache:
            r = requests.get(
                f"https://www.neuronpedia.org/api/feature/{self.model_id}/{self.layer}/{self.index}"
            )
            if r.status_code != 200:
                raise Exception(f"Failed to get feature info for {self}: {r.status_code}")

            data = r.json()
            if data is None or data.get('maxActApprox', 0) == 0:
                raise Exception(f"No activating data for feature {self}")

            self.cache[cache_key] = data
        return self.cache[cache_key]

    def get_activating_examples(self) -> Tuple[List[List[str]], List[List[float]]]:
        """Get activating examples for semantic regex generation."""
        feature_info = self.get_feature_info()

        tokens = []
        activations = []

        for item in feature_info.get('activations', []):
            # Clean up tokens and activations
            clean_tokens, clean_activations = util.batch_replace_html_anomalies_and_special_chars(
                item['tokens'], item['values']
            )

            # Only include examples that actually activate
            if max(clean_activations) > 0:
                tokens.append(clean_tokens)
                activations.append(clean_activations)

        if len(tokens) == 0:
            raise Exception(f"No activating examples found for feature {self}")

        return tokens, activations
