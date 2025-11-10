#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Utility functions for Semantic Regex Autointerp.

from typing import List, Tuple
import numpy as np
import random


# Tokenizer bugs that need to be replaced with correct characters
HTML_ANOMALY_AND_SPECIAL_CHARS_REPLACEMENTS = {
    "âĢĶ": "—",  # em dash
    "âĢĵ": "–",  # en dash
    "âĢľ": '"',  # left double curly quote
    "âĢĿ": '"',  # right double curly quote
    "âĢĺ": "'",  # left single curly quote
    "âĢĻ": "'",  # right single curly quote
    "âĢĭ": " ",  # zero width space
    "âĢ¦": "...",  # ellipsis
    "Ġ": " ",  # space
    "Ċ": "\n",  # line break
    "<0x0A>": "\n",
    "ĉ": "\t",  # tab
    "▁": " ",  # \u2581, gemma 2 uses this as a space
    # "<|endoftext|>": " ",
    # "<bos>": " ",
    # "<|begin_of_text|>": " ",
    # "<|end_of_text|>": " ",
}

def _handle_paired_token_anomalies(tokens: List[str], activations: List[float]) -> List[str]:
    """Tokenization errors that start with âĢ are fixed by looking at pairs of tokens."""
    fixed_tokens = []
    fixed_activations = []
    i = 0
    n = len(tokens)
    while i < n:
        if i + 1 < n:
            pair = tokens[i] + tokens[i + 1]
            if pair in HTML_ANOMALY_AND_SPECIAL_CHARS_REPLACEMENTS:
                fixed_tokens.append(HTML_ANOMALY_AND_SPECIAL_CHARS_REPLACEMENTS[pair])
                fixed_activations.append(max(activations[i], activations[i + 1]))
                i += 2
                continue
        fixed_tokens.append(tokens[i])
        fixed_activations.append(activations[i])
        i += 1
    return fixed_tokens, fixed_activations

def replace_html_anomalies_and_special_chars(text: str) -> str:
    """Replace known HTML anomalies and special characters in a string."""
    for old_char, new_char in HTML_ANOMALY_AND_SPECIAL_CHARS_REPLACEMENTS.items():
        text = text.replace(old_char, new_char)
    return text

def batch_replace_html_anomalies_and_special_chars(tokens: List[str], activations: List[str]) -> List[str]:
    """Replace known HTML anomalies and special characters in a list of tokens."""
    fixed_tokens = []
    for token in tokens:
        formatted_token = replace_html_anomalies_and_special_chars(token)
        fixed_tokens.append(formatted_token)
    fixed_tokens, fixed_activations = _handle_paired_token_anomalies(fixed_tokens, activations)
    return fixed_tokens, fixed_activations

def format_data_string(tokens: List[str], show_breaks: bool) -> str:
    """Format a list of tokens into a single string, optionally removing line breaks.
    Args:
        tokens: List of tokens to format.
        show_breaks: Whether to include line breaks in the output string.
    Returns:
        A formatted string.
    """
    string = ''.join(tokens)
    if not show_breaks:
        string = string.replace("\n", " ")
    return string

def format_data_strings(batch_tokens: List[List[str]], show_breaks: bool) -> List[str]:
    """Format a batch of lists of tokens into a list of strings, optionally removing line breaks.
    Args:
        batch_tokens: A list of lists of tokens to format.
        show_breaks: Whether to include line breaks in the output strings.
    Returns:
        A list of formatted strings.
    """
    return [format_data_string(tokens, show_breaks) for tokens in batch_tokens]

def format_activation_string(tokens: List[str], activations: List[float], show_activations: bool, show_null_activations: bool, merge_activations: bool, show_breaks: bool, activation_threshold: int) -> str:
    """Format tokens and their activations into a single string with activation annotations.
    Args:
        tokens: List of tokens.
        activations: List of corresponding activation values.
        show_activations: Whether to include activation values in the output string.
        show_null_activations: Whether to include zero activation values in the output string.
        merge_activations: Whether to merge consecutive tokens with positive activations.
        show_breaks: Whether to include line breaks in the output string.
    Returns:
        A formatted string with activation annotations.
    Raises:
        AssertionError: If the input lists are of different lengths or if invalid parameter combinations are provided.
    """
    assert len(tokens) == len(activations), "Tokens and activations must have the same length"
    if not show_activations:
        assert not show_null_activations, "Cannot show null activations when not showing activations"
    if merge_activations:
        assert not show_activations, "Cannot merge activations when showing activations"

    if not show_activations:
        string = ''.join(f"<<{token}>>" if activation > activation_threshold else token for token, activation in zip(tokens, activations))
        if merge_activations:
            string = string.replace(">><<", "")
    else:
        if show_null_activations:
            string = ''.join(f"{token}<<{activation:.1f}>>" for token, activation in zip(tokens, activations))
        else:
            string = ''.join(f"{token}<<{activation:.1f}>>" if activation > activation_threshold else f"{token}" for token, activation in zip(tokens, activations))
    if not show_breaks:
        string = string.replace("\n", " ")
    return string

def batch_format_activation_string(batch_tokens: List[List[str]], batch_activations: List[List[float]], show_activations: bool, show_null_activations: bool, merge_activations: bool, show_breaks: bool, activation_threshold: int) -> List[str]:
    """Format a batch of tokens and their activations into strings with activation annotations.
    Args:
        batch_tokens: A list of lists of tokens.
        batch_activations: A list of lists of corresponding activation values.
        show_activations: Whether to include activation values in the output strings.
        show_null_activations: Whether to include zero activation values in the output strings.
        merge_activations: Whether to merge consecutive tokens with positive activations.
        show_breaks: Whether to include line breaks in the output strings.
    Returns:
        A list of formatted strings with activation annotations.
    Raises:
        AssertionError: If the input lists are of different lengths or if invalid parameter combinations are provided.
    """
    assert len(batch_tokens) == len(batch_activations), "Batch tokens and activations must have the same number of examples"
    formatted_strings = []
    for tokens, activations in zip(batch_tokens, batch_activations):
        formatted_string = format_activation_string(tokens, activations, show_activations, show_null_activations, merge_activations, show_breaks, activation_threshold=activation_threshold)
        formatted_strings.append(formatted_string)
    return formatted_strings

def batch_snip_activations(tokens: List[List[str]], activations: List[List[float]], length_in_tokens: int) -> Tuple[List[List[str]], List[List[float]]]:
    """Extract snippets of tokens and activations around the maximum activation for each example.
    Args:
        tokens: A list of lists of tokens.
        activations: A list of lists of corresponding activation values.
        length_in_tokens: The number of tokens to include in each example, centered around the max value.
    Returns:
        A tuple containing a list of lists of snipped tokens and a list of lists of their activations.
    Raises:
        AssertionError: If the input lists are of different lengths.
    """
    assert len(tokens) == len(activations), "Tokens and activations must have the same number of examples"
    snipped_tokens = []
    snipped_activations = []
    for t, a in zip(tokens, activations):
        snipped_t, snipped_a = snip_activations(t, a, length_in_tokens)
        snipped_tokens.append(snipped_t)
        snipped_activations.append(snipped_a)
    return snipped_tokens, snipped_activations

def snip_activations(tokens: List[str], activations: List[float], length_in_tokens: int) -> Tuple[List[str], List[float]]:
    """Extract a snippet of tokens and activations around the maximum activation.
    Args:
        tokens: A list of tokens.
        activations: A list of corresponding activation values.
        length_in_tokens: The number of tokens to include in each example, centered around the max value.
    Returns:
        A tuple containing a list of snipped tokens and a list of their activations.
    Raises:
        AssertionError: If the input lists are of different lengths.
    """
    assert len(tokens) == len(activations), "Tokens and activations must have the same length"
    n_tokens_before_max = length_in_tokens // 2
    n_tokens_after_max = length_in_tokens // 2
    if length_in_tokens % 2 == 0: # Even length, means start and end windows are not symmetric
        n_tokens_after_max = length_in_tokens // 2 - 1
    assert n_tokens_before_max + n_tokens_after_max + 1 == length_in_tokens, "Length in tokens must equal the sum of tokens before and after max plus one"
    max_index = np.argmax(activations)
    if max(activations) == 0:
        max_index = len(tokens) // 2 # If all activations are zero, center the snippet
    start = max(0, max_index - n_tokens_before_max)
    end = min(len(tokens), max_index + n_tokens_after_max + 1)
    assert len(tokens[start:end]) == len(activations[start:end]) <= length_in_tokens, "Snipped tokens and activations must have the same length and be less than or equal to length_in_tokens"
    return tokens[start:end], activations[start:end]

def remove_duplicate_snippets(tokens: List[List[str]], activations: List[List[float]]) -> Tuple[List[List[str]], List[List[float]]]:
    """Remove duplicate snippets based on token sequences.
    Args:
        tokens: A list of lists of tokens.
        activations: A list of lists of corresponding activation values.
    Returns:
        A tuple containing a list of lists of unique tokens and a list of lists of their activations.
    Raises:
        AssertionError: If the input lists are of different lengths.
    """
    assert len(tokens) == len(activations), "Tokens and activations must have the same number of examples"
    seen = set()
    unique_indices = []
    for i, token_list in enumerate(tokens):
        text = ''.join(token_list)
        if text not in seen:
            seen.add(text)
            unique_indices.append(i)
    return [tokens[i] for i in unique_indices], [activations[i] for i in unique_indices]

def is_number(value: str) -> bool:
    """Check if a string can be converted to a float.
    Args:
        value: The string to check.
    Returns:
        True if the string can be converted to a float, False otherwise.
    """
    try:
        float(value)
        return True
    except ValueError:
        return False

def set_seed(seed: int):
    """Set the random seed for reproducibility.
    Args:
        seed: The seed value to set.
    """
    random.seed(seed)
    np.random.seed(seed)
