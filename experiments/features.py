#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Neuronpedia API feature functions to access feature info, activating examples, and explanations.

import numpy as np
import util
import requests
import torch
from sae_lens import SAE
from typing import List, Tuple


class Feature():
    """A class representing an individual feature in a model."""

    def __init__(self, model_id: str, layer: str, index: int):
        self.model_id = model_id
        self.layer = layer
        self.index = index
        self.cache = {}

    def __str__(self) -> str:
        return f"{self.model_id}_{self.layer}_{self.index}"

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "layer": self.layer,
            "index": self.index
        }

    def get_feature_info(self) -> dict:
        """Get feature info from Neuronpedia.
        Returns:
            A dictionary containing the feature information.
        Raises:
            Exception: If the API call fails or returns no data.
        """
        if str(self) not in self.cache:
            r = requests.get(
                f"https://www.neuronpedia.org/api/feature/{self.model_id}/{self.layer}/{self.index}",
            )
            if r.status_code != 200:
                raise Exception(f"Failed to get feature info for feature {str(self)}: {r}")
            if r.json() is None or r.json()['maxActApprox'] == 0:
                raise Exception(f"No activating data for feature {str(self)}.")
            self.cache[str(self)] = r.json()
        return self.cache[str(self)]

    def get_sae_size(self) -> int:
        """Get SAE size for a this feature source.
        Returns:
            The SAE size as an integer.
        Raises:
            ValueError: If the SAE size is not found in the feature's source.
        """
        feature_info = self.get_feature_info()
        sae_size = feature_info.get('source', {}).get('saelensConfig', {}).get('d_sae', 0)
        if sae_size == 0:
            raise ValueError(f"SAE size not found for feature {self}")
        return sae_size

    def get_model_num_layers(self) -> int:
        """Get the number of layers in the model for this feature.
        Returns:
            The number of layers in the model as an integer.
        Raises:
            ValueError: If the model's number of layers is not found.
        """
        feature_info = self.get_feature_info()
        model_num_layers = feature_info.get('model', {}).get('layers', 0)
        if model_num_layers == 0:
            raise ValueError(f"Model num layers not found for feature {self}")
        return model_num_layers

    def get_examples(self) -> Tuple[List[List[str]], List[List[float]]]:
        """Get the examples for this feature.
        Returns:
            A tuple containing a list of tokens and a list of their activations.
        Raises:
            Exception: If the API call fails or returns no data.
        """
        feature_info = self.get_feature_info()
        tokens = []
        activations = []
        for item in feature_info.get('activations', []):
            formatted_tokens, formatted_activations = util.batch_replace_html_anomalies_and_special_chars(item['tokens'], item['values'])
            tokens.append(formatted_tokens)
            activations.append(formatted_activations)
        if len(tokens) == 0:
            raise Exception(f"No examples found for feature {self}")
        return tokens, activations

    def get_activating_examples(self) -> Tuple[List[List[str]], List[List[float]]]:
        """Get the activating examples for this feature.
        Returns:
            A tuple containing a list of tokens and a list of their activations.
        Raises:
            Exception: If the API call fails or returns no data.
        """
        tokens, activations = self.get_examples()
        filtered_tokens, filtered_activations = [], []
        for t, a in zip(tokens, activations):
            if max(a) > 0:
                filtered_tokens.append(t)
                filtered_activations.append(a)
        if len(filtered_tokens) == 0:
            raise Exception(f"No activating examples found for feature {self}")
        return filtered_tokens, filtered_activations

    def get_non_activating_examples(self) -> Tuple[List[List[str]], List[List[float]]]:
        """Get the non-activating examples for this feature.
        Returns:
            A tuple containing a list of tokens and a list of their activations.
        Raises:
            Exception: If the API call fails or returns no data.
        """
        tokens, activations = self.get_examples()
        filtered_tokens, filtered_activations = [], []
        for t, a in zip(tokens, activations):
            if max(a) <= 0:
                filtered_tokens.append(t)
                filtered_activations.append(a)
        return filtered_tokens, filtered_activations

    def get_activating_examples_per_quantile(self, n_quantiles: int, n_examples_per_quantile: int) -> Tuple[List[List[str]], List[List[float]]]:
        """Access a feature's activating examples, sampled evenly across activation quantiles.
        Args:
            n_quantiles: The number of quantiles to divide the activating examples into.
            n_examples_per_quantile: The number of examples to sample from each quantile.
        Returns:
            A tuple containing a list of tokens and a list of their activations.
        """
        tokens, activations = self.get_activating_examples()
        tokens, activations = util.remove_duplicate_snippets(tokens, activations)
        assert n_quantiles > 0, "n_quantiles must be greater than 0"
        assert n_examples_per_quantile > 0, "n_examples_per_quantile must be greater than 0"

        quantile_size = len(tokens) // n_quantiles
        selected_tokens = []
        selected_activations = []
        for i in range(n_quantiles):
            quantile_indices = list(range(i * quantile_size, (i + 1) * quantile_size))
            sampled_indices = np.random.choice(quantile_indices, size=min(n_examples_per_quantile, len(quantile_indices)), replace=False)
            sampled_indices.sort()
            selected_tokens.extend([tokens[j] for j in sampled_indices])
            selected_activations.extend([activations[j] for j in sampled_indices])
        return selected_tokens, selected_activations


    def get_positive_logits(self) -> Tuple[List[str], List[float]]:
        """Get the positive logits for this feature.
        Returns:
            A tuple containing a list of tokens and a list of their logit scores.
        Raises:
            Exception: If the API call fails or returns no data.
        """
        feature_info = self.get_feature_info()
        positive_tokens = feature_info.get('pos_str', [])
        positive_logit_scores = feature_info.get('pos_values', [])
        positive_tokens, positive_logit_scores = util.batch_replace_html_anomalies_and_special_chars(positive_tokens, positive_logit_scores)
        return positive_tokens, positive_logit_scores

    def get_explanation(self, model: str, method: str) -> dict:
        """Get feature description from Neuronpedia.
        Args:
            model: The description model name.
            method: The description method name.
        Returns:
            dict: The explanation data. If multiple explanations match, returns the first one.
        Raises:
            Exception: If no explanations are found for the given model and method.
        """
        explanations = self.get_explanations()
        model_explanations = [explanation for explanation in explanations if explanation['explanationModelName'] == model and explanation['typeName'] == method]
        if len(model_explanations) == 0:
            raise Exception(f"No explanations found for model {model} and method {method}. Available: {[(exp['explanationModelName'], exp['typeName']) for exp in explanations]}.")
        if len(model_explanations) > 1:
            print(f"Warning: Multiple explanations found for model {model} and method {method}. Returning the first one.")
        return model_explanations[0]

    def get_explanations(self) -> List[dict]:
        """Gets all explanations for the feature from Neuronpedia.
        Returns:
            A list of explanation data.
        Raises:
            Exception: If the API call fails or returns no data.
        """
        feature_info = self.get_feature_info()
        explanations = feature_info.get('explanations', [])
        return explanations

    def query_feature(self, text: str, ignore_first_token: bool) -> Tuple[List[str], List[float]]:
        """Query Neuronpedia API for activations of a feature on given text.
        Args:
            text: The input text to evaluate.
            ignore_first_token: Whether to ignore the first token if it's a special token.
        Returns:
            A tuple containing a list of tokens and a list of their activations.
        Raises:
            Exception: If the API call fails or returns no data.
            AssertionError: If the returned data is invalid.
        """
        assert len(text) > 0, "Text must not be empty"

        r = requests.post(
            "https://www.neuronpedia.org/api/activation/new",
            headers={
                "Content-Type": "application/json"
            },
            json={
                "feature": {
                    "modelId": self.model_id,
                    "source": self.layer,
                    "index": f"{self.index}"
                },
                "customText": text
            }
        )

        if r.status_code != 200:
            raise Exception(f"Failed to query feature {self} with text {text}: {r.status_code}")

        r = r.json()
        tokens = r.get('tokens', [])
        activations = r.get('values', [])

        assert len(tokens) > 0, "No tokens returned from the API"
        assert len(tokens) == len(activations), "Tokens and activations must have the same length"

        if ignore_first_token and tokens[0] in ['<|endoftext|>', '<bos>']:
            tokens = tokens[1:]
            activations = activations[1:]

        return tokens, activations

    def batch_query_feature(self, texts: List[str], ignore_first_token: bool) -> Tuple[List[List[str]], List[List[float]]]:
        """Batch query Neuronpedia API for activations of a feature on multiple texts.
        Args:
            texts: A list of input texts to evaluate.
            ignore_first_token: Whether to ignore the first token if it's a special token.
        Returns:
            A tuple containing a list of lists of tokens and a list of lists of their activations.
        Raises:
            Exception: If any API call fails or returns no data.
            AssertionError: If any returned data is invalid.
        """
        tokens = []
        activations = []
        for text in texts:
            t, a = self.query_feature(text, ignore_first_token)
            tokens.append(t)
            activations.append(a)
        return tokens, activations

    def batch_query_feature_on_device(self, texts: List[str], model, device):
        """Batch query a feature on a local model using SAE-Lens.
        Args:
            texts: A list of input texts to evaluate.
            model: The language model to use for evaluation.
            device: The device to run the model on.
        Returns:
            A tuple containing a list of lists of tokens and a list of lists of their activations.
        """
        print(f"Querying feature {self} on local model")
        sae, hook_name = self.load_sae(device)
        sae.eval()
        model.eval()

        tokens = model.to_tokens(texts, prepend_bos=True).to("cuda")
        with torch.no_grad():
            _, cache = model.run_with_cache(tokens, names_filter=[hook_name])
        model_activations = cache[hook_name]

        with torch.no_grad():
            try:
                _, sae_activations = sae(model_activations, return_latents=True)
            except TypeError:
                sae_activations = sae.encode(model_activations)

        feature_activations = sae_activations[:, :, self.index].cpu().numpy()
        activations = []
        tokens = []
        for i, text in enumerate(texts):
            text_tokens = list(model.to_str_tokens(text, prepend_bos=False))
            tokens.append(text_tokens)
            length = len(text_tokens)
            activations.append(list([float(x) for x in feature_activations[i, 1:length+1]]))
        return tokens, activations


    def steer(self, text: str, strength: float, num_tokens: int,) -> str:
        """Steer a feature using Neuronpedia API with given text and strength.
        Args:
            text: The input text to use for steering.
            strength: The strength of the steering.
            num_tokens: The number of tokens to generate.
        Returns:
            A tuple containing the steered text and the default text.
        Raises:
            Exception: If the API call fails or returns no data.
        """
        r = requests.post("https://www.neuronpedia.org/api/steer",
            headers={
                "Content-Type": "application/json",
            },
            json={
                "prompt": text,
                "modelId": self.model_id,
                "features": [
                    {
                    "modelId": self.model_id,
                    "layer": self.layer,
                    "index": self.index,
                    "strength": strength
                    }
                ],
                "temperature": 0.5,
                "n_tokens": num_tokens,
                "freq_penalty": 1,
                "seed": 97,
                "strength_multiplier": 1
            }
        )

        if r.status_code != 200:
            raise Exception(f"Failed to steer feature {self} with text {text}: {r.status_code}")

        r = r.json()
        steered_text = r['STEERED'][len(text):]
        return steered_text

    def steer_on_device(self, texts: List[str], strength: float, num_tokens: int, model, device, sae, hook_name) -> str:
        """Steer a featureo n a local model using SAE-Lens with given text and strength.
        Args:
            text: The input text to use for steering.
            strength: The strength of the steering.
            num_tokens: The number of tokens to generate.
            model: The language model to use for generation.
            device: The device to run the model on.
        Returns:
            A tuple containing the steered text and the default text.
        Raises:
            Exception: If the API call fails or returns no data.
        """
        sae.eval()
        model.eval()

        steering_vector = sae.W_dec[self.index].to(device)

        @torch.no_grad()
        def steering_hook(activation, hook):
            v = steering_vector.to(dtype=activation.dtype)
            # return, don't mutate in-place
            activation = activation.clone()
            activation[:, -1, :] += strength * steering_vector
            return activation

        def hooked_generate(texts, forward_hooks):
            per_token = [model.to_tokens(t, prepend_bos=True).to(device)[0] for t in texts]
            per_length = [t.shape[0] for t in per_token]
            batch_size = len(per_token)
            max_length = max(per_length)

            # Left pad the inputs so that generation starts from the end of the text
            eos_id = model.tokenizer.eos_token_id
            tokens = torch.full(
                (batch_size, max_length),
                fill_value=eos_id,
                dtype=per_token[0].dtype,
                device=device,
            )
            for i, (t, l) in enumerate(zip(per_token, per_length)):
                tokens[i, -l:] = t

            with torch.no_grad():
                with model.hooks(fwd_hooks=forward_hooks):
                    steered_tokens = model.generate(
                        stop_at_eos=False,
                        input=tokens,
                        max_new_tokens=num_tokens,
                        do_sample=True,
                        temperature=0.5,
                        freq_penalty=1.0,
                    )

            steered_texts = []
            for i, l in enumerate(per_length):
                # start = max_length - l + 1 # +1 to skip the initial BOS token
                start = -num_tokens
                steered_text = model.to_string(steered_tokens[i, start:])
                steered_texts.append(steered_text)
            return steered_texts

        model.reset_hooks()
        editing_hooks = [(hook_name, steering_hook)]
        steered_texts = hooked_generate(texts, editing_hooks)
        return steered_texts

    def load_sae(self, device: str) -> SAE:
        """Load the SAE for this feature."""
        feature_info = self.get_feature_info()
        cfg = feature_info['source']['saelensConfig']
        hook_name = cfg.get('hook_point', cfg.get('hook_name'))
        if hook_name is None:
            raise ValueError(f"Hook name not found for feature {self}")

        sae_id = feature_info['source']['saelensSaeId']
        release = feature_info['source']['saelensRelease']

        sae, _, _ = SAE.from_pretrained(release=release, sae_id=sae_id, device=device)
        sae.eval()

        return sae, hook_name
