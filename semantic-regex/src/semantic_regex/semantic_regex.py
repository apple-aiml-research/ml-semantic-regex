#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

"""Semantic Regex prompt generator package."""

import numpy as np
from typing import List, Optional, Tuple
import dspy

from . import util
from .prompts import semantic_regex_prompt
from . import neuronpedia


def _generate_examples(
    batch_tokens: List[List[str]],
    batch_activations: List[List[float]],
    activation_threshold: float = 0.3,
    n_data_examples: int = 10,
    n_tokens_per_sample: int = 32,
    sampling_method: str = 'top',
    show_breaks: bool = True,
    seed: int = 42
) -> str:
    """Generate formatted examples string from tokens and activations.

    This function processes token sequences and their corresponding activation values,
    filters based on activation thresholds, samples examples using specified methods,
    and formats them for use in semantic regex prompts.
    Args:
        batch_tokens: List of token sequences, where each sequence is a list of strings.
        batch_activations: List of activation sequences corresponding to batch_tokens.
        activation_threshold: Minimum relative activation threshold (0.0-1.0) for
            highlighting tokens. Tokens with activations below threshold * max_activation
            are filtered out.
        n_data_examples: Maximum number of examples to include in the output.
        n_tokens_per_sample: Number of tokens per example snippet.
        sampling_method: Method for selecting examples from filtered candidates.
            Options: 'top' (highest activations), 'random' (random sampling),
            'quantile' (distributed across activation quantiles).
        show_breaks: Whether to show token breaks in the formatted output.
        seed: Random seed for reproducible sampling when using 'random' or 'quantile' methods.
    Returns:
        Formatted string containing numbered examples with highlighted activations.
        Each example is on a separate line with format "N: <formatted_text>".

    Raises:
        ValueError: If sampling_method is not one of 'top', 'random', or 'quantile'.
    """
    util.set_seed(seed)

    # Process examples (copied logic from semantic_regex_description.py)
    positive_tokens, positive_activations = util.remove_duplicate_snippets(
        *util.batch_snip_activations(batch_tokens, batch_activations, length_in_tokens=n_tokens_per_sample)
    )

    # Filter out examples with low activation that will not be highlighted
    max_positive_activation = max([max(activations) for activations in positive_activations])
    threshold = activation_threshold * max_positive_activation
    filtered_positive_tokens, filtered_positive_activations = [], []
    for tokens, activations in zip(positive_tokens, positive_activations):
        if max(activations) >= threshold:
            filtered_positive_tokens.append(tokens)
            filtered_positive_activations.append(activations)

    # Sample the correct number using the sampling strategy
    if sampling_method == 'top':
        positive_tokens, positive_activations = filtered_positive_tokens[:n_data_examples], filtered_positive_activations[:n_data_examples]
    elif sampling_method == 'random':
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
            sampled_indices = sorted([int(np.quantile(range(len(max_activations)), q, method='nearest')) for q in quantiles])
            positive_tokens = [filtered_positive_tokens[i] for i in sampled_indices]
            positive_activations = [filtered_positive_activations[i] for i in sampled_indices]
    else:
        raise ValueError(f"Unknown sampling method: {sampling_method}")

    # Format examples
    examples_text = ""
    for i, (tokens, activations) in enumerate(zip(positive_tokens, positive_activations)):
        text = util.format_activation_string(tokens, activations, False, False, True, show_breaks, threshold)
        examples_text += f"{i+1}: {text.strip()}\n"

    return examples_text.strip()


def generate_semantic_regex_prompt(
    batch_tokens: List[List[str]],
    batch_activations: List[List[float]],
    activation_threshold: float = 0.3,
    n_data_examples: int = 10,
    n_tokens_per_sample: int = 32,
    sampling_method: str = 'top',
    show_breaks: bool = True,
    seed: int = 42
) -> dict:
    """Generate a semantic regex prompt with metadata.

    Creates a full prompt by combining the system instructions with formatted
    examples derived from token activations. The prompt is designed to guide
    language models in generating semantic regex patterns.

    Args:
        batch_tokens: List of token sequences, where each sequence is a list of strings.
        batch_activations: List of activation sequences corresponding to batch_tokens.
        activation_threshold: Minimum relative activation threshold (0.0-1.0) for
            highlighting tokens in examples.
        n_data_examples: Maximum number of examples to include in the prompt.
        n_tokens_per_sample: Number of tokens per example snippet.
        sampling_method: Method for selecting examples ('top', 'random', or 'quantile').
        show_breaks: Whether to show token breaks in the formatted examples.
        seed: Random seed for reproducible example selection.

    Returns:
        Dictionary containing:
            - 'prompt': Complete formatted prompt string ready for LLM input
            - 'parameters': Dictionary of all parameters used for reproducibility
    """

    # Get the system prompt
    system_prompt = semantic_regex_prompt.SYSTEM

    # Generate examples using shared logic
    examples = _generate_examples(
        batch_tokens, batch_activations, activation_threshold,
        n_data_examples, n_tokens_per_sample, sampling_method,
        show_breaks, seed
    )

    # Combine into a single prompt string
    full_prompt = f"{system_prompt}\n\nHere are examples:\n\n{examples}"

    return {
        "prompt": full_prompt,
        "parameters": {
            "activation_threshold": activation_threshold,
            "n_data_examples": n_data_examples,
            "n_tokens_per_sample": n_tokens_per_sample,
            "sampling_method": sampling_method,
            "show_breaks": show_breaks,
            "seed": seed
            }
        }


class SemanticRegexGenerator(dspy.Signature):
    """Generate a semantic regex from highlighted text examples."""

    prompt = dspy.InputField(desc="Complete semantic regex prompt with instructions and highlighted text examples")
    semantic_regex = dspy.OutputField(desc="Semantic regex pattern that captures the highlighted concept")


def generate_semantic_regex(
    prompt_data: dict,
    lm: Optional[dspy.LM] = None,
    temperature: float = 1.0,
    logging: bool = False
) -> dict:
    """Generate a semantic regex description using DSPy for model agnosticism.

    Takes a formatted prompt and uses a language model to generate a semantic
    regex pattern that captures the concept highlighted in the examples.

    Args:
        prompt_data: Dictionary from generate_semantic_regex_prompt() containing
            'prompt' (str) and 'parameters' (dict) keys.
        lm: DSPy language model instance. If None, uses the currently configured
            DSPy language model.
        temperature: Sampling temperature for language model generation (0.0-2.0).
            Higher values increase randomness in outputs.
        logging: Whether to print debug information including the full prompt
            and generated semantic regex.

    Returns:
        Dictionary containing:
            - 'description': Parsed semantic regex pattern string
            - 'prompt': Original prompt used for generation
            - 'lm': Language model instance used
            - 'parameters': Combined parameters from prompt generation and this function

    Raises:
        Exception: If there's an error during semantic regex generation, wraps
            the underlying exception with additional context.
    """

    # Extract prompt from the prompt_data dict
    prompt = prompt_data["prompt"]
    prompt_parameters = prompt_data.get("parameters", {})

    # Set up DSPy language model if provided
    if lm is not None:
        dspy.configure(lm=lm, temperature=temperature)

    if logging:
        print(f"FULL SEMANTIC REGEX PROMPT:")
        print(prompt)
        print('\n')

    # Use DSPy to generate the semantic regex
    generator = dspy.ChainOfThought(SemanticRegexGenerator)

    try:
        result = generator(prompt=prompt)
        description = _parse_semantic_regex_response(result.semantic_regex)

        if logging:
            print(f"GENERATED SEMANTIC REGEX: {description}\n")

        return {
            "description": description,
            "prompt": prompt,
            "lm": lm,
            "parameters": {
                "temperature": temperature,
                **prompt_parameters
            }
        }

    except Exception as e:
        raise Exception(f"Error generating semantic regex: {e}")


def _parse_semantic_regex_response(response: str) -> str:
    """Parse the semantic regex from the LLM response.

    Extracts the semantic regex pattern from the language model's response
    by looking for the 'SR: ' prefix and returning the content that follows.

    Args:
        response: Raw response string from the language model.

    Returns:
        Cleaned semantic regex pattern string with leading/trailing whitespace removed.

    Raises:
        ValueError: If the response doesn't contain the expected 'SR: ' prefix,
            indicating an unexpected response format.
    """
    if "SR: " in response:
        return response.split("SR: ")[-1].strip()
    else:
        raise ValueError(f"Could not find 'SR: ' in response: {response}")


def get_neuronpedia_data(model_id: str, layer: str, feature_index: int) -> Tuple[List[List[str]], List[List[float]]]:
    """Get tokens and activations from a Neuronpedia feature.

    Retrieves activating examples for a specific feature from Neuronpedia,
    returning the data in a format ready for semantic regex generation.

    Args:
        model_id: Model identifier string (e.g., 'gemma-2-2b', 'gpt2-small').
        layer: Layer identifier string (e.g., 'blocks.12.hook_resid_post').
        feature_index: Integer index of the feature within the specified layer.

    Returns:
        Tuple containing:
            - batch_tokens: List of token sequences (List[List[str]])
            - batch_activations: List of corresponding activation values (List[List[float]])

        The returned data is formatted for direct use with generate_semantic_regex_prompt().
    """
    feature = neuronpedia.Feature(model_id, layer, feature_index)
    return feature.get_activating_examples()

