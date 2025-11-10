# Semantic Regex

Auto-Interpreting LLM Features with a Structured Language

## Overview

`semantic-regex` is a Python package for interpreting neural network features using the *semantic regex language* for automatic interpretability. Given an input list of tokens and another list of their activation values, it can either: (1) generate the full prompt for generating a semantic regex, and/or (2) pass the prompt to dspy to generate the semantic regex result. The semantic regex language is designed to capture the diverse activation patterns of LLM features, while providing the additional affordances of a structured language.

This package accompanies the research paper:

**Semantic Regexes: Auto-Interpreting LLM Features with a Structured Language**\
[Angie Boggust](https://angieboggust.com), [Donghao Ren](https://donghaoren.org), [Yannick Assogba](https://clome.info), [Dominik Moritz](https://www.domoritz.de), [Arvind Satyanarayan](https://arvindsatya.com), [Fred Hohman](https://fredhohman.com)\
arXiv, 2025.\
[Paper](https://arxiv.org/abs/2510.06378), [GitHub](https://github.com/apple/ml-semantic-regex), [Python package](https://pypi.org/project/semantic-regex), [Viewer](https://apple.github.io/ml-semantic-regex)

## Installation

Install the package using pip:

```bash
pip install semantic-regex
```

Or for development, clone the repository and install with uv:

```bash
git clone https://github.com/apple/ml-semantic-regex.git
cd semantic-regex
uv sync
```

## Quick Start

The general flow is get tokens (`batch_tokens`) and activations (`batch_activations`), generate the prompt (`generate_semantic_regex_prompt`), and then generate the semantic regex (`generate_semantic_regex)`.

To start, you can bring your own tokens and activations, or load them using an optoinal Neuronpedia API.

```python
from semantic_regex import get_neuronpedia_data, generate_semantic_regex_prompt, generate_semantic_regex
import dspy

# Step 1a: Bring your own tokens and activations
batch_tokens = [
    ["The", "quick", "brown", "fox", "jumps"],
    ["A", "fast", "red", "car", "speeds"],
    ["She", "ran", "quickly", "through", "forest"]
]

batch_activations = [
    [0.1, 0.9, 0.2, 0.1, 0.1],  # "quick" activates strongly
    [0.1, 0.8, 0.2, 0.1, 0.1],  # "fast" activates strongly
    [0.1, 0.1, 0.9, 0.1, 0.1]   # "quickly" activates strongly
]

# Step 1b: Or get them from Neuronpedia
batch_tokens, batch_activations = get_neuronpedia_data(
    model_id="gpt2-small",
    layer="0-res-jb",
    feature_index=21896
)

# Step 2: Generate prompt data with parameters
prompt_data = generate_semantic_regex_prompt(
    batch_tokens=batch_tokens,
    batch_activations=batch_activations,
    activation_threshold=0.3,
    n_data_examples=3,
    show_breaks=True,
    seed=42
)

## Optionally view the prompt
prompt = prompt_data["prompt"]

# Step 3: Use with dspy to generate semantic regex
lm = dspy.LM('openai/gpt-4o-mini')  # or any other supported model

result = generate_semantic_regex(
    prompt_data=prompt_data,
    lm=lm,
    temperature=0.7,
    logging=True  # Print the prompt and generated regex
)

## Output of the form: [:field speed:]
print(f"Generated semantic regex: {result['description']}")
```

## API Reference

### `generate_semantic_regex_prompt()`

Generate a semantic regex prompt with metadata from tokens and activations.

**Parameters:**

- `batch_tokens` (List[List[str]]): List of token sequences
- `batch_activations` (List[List[float]]): List of corresponding activation sequences
- `activation_threshold` (float, default=0.3): Minimum activation threshold for highlighting
- `n_data_examples` (int, default=10): Number of examples to include in prompt
- `n_tokens_per_sample` (int, default=32): Number of tokens per example snippet
- `sampling_method` (str, default='top'): Sampling strategy - 'top', 'random', or 'quantile'
- `show_breaks` (bool, default=True): Whether to show line breaks in examples
- `seed` (int, default=42): Random seed for reproducibility

**Returns:**

- `dict`: Dictionary containing:
  - `prompt` (str): Complete prompt string that can be used with any language model
  - `parameters` (dict): All parameters used for generation (for reproducibility)

### `generate_semantic_regex()`

Generate a semantic regex pattern using DSPy for model-agnostic generation.

**Parameters:**

- `prompt_data` (dict): Dictionary from `generate_semantic_regex_prompt()` with 'prompt' and 'parameters'
- `lm` (Optional[dspy.LM], default=None): DSPy language model instance
- `temperature` (float, default=1.0): Sampling temperature for the language model
- `logging` (bool, default=False): Whether to print the prompt and generated regex

**Returns:**

- `dict`: Dictionary containing:
  - `description` (str): Generated semantic regex pattern
  - `prompt` (str): The original prompt used
  - `lm` (dspy.LM): The language model used
  - `parameters` (dict): All parameters used for generation (prompt + LM parameters)

### `get_neuronpedia_data()`

Get tokens and activations from a Neuronpedia feature.

**Parameters:**

- `model_id` (str): Model identifier (e.g., 'gpt2-small')
- `layer` (str): Layer identifier (e.g., '0-res-jb')
- `feature_index` (int): Feature index number

**Returns:**

- `Tuple[List[List[str]], List[List[float]]]`: (batch_tokens, batch_activations) ready for prompt generation

**Note:** Requires the `neuronpedia` package to be installed separately.

## Semantic Regex Language

The package generates prompts that help language models create patterns using a structured language:

- `[:symbol X:]` - matches exact phrase X
- `[:lexeme X:]` - matches phrase X and its syntactic variants
- `[:field X:]` - matches phrase X and its semantic variants
- `S1 S2` - matches sequence where S1 is followed by S2
- `S1|S2` - matches either S1 or S2
- `S?` - matches S or nothing (optional)
- `@{:context C:}(S)` - matches S only in context C

## Testing

Run the test suite:

```bash
uv run pytest
uv run pytest --capture=no  # Show print statements
```

Run specific test functions:

```bash
uv run pytest tests/test_api.py::test_basic_functionality
uv run pytest tests/test_api.py::simple_test
```

## Development

### Setup

1. Clone the repository:

```bash
git clone https://github.com/apple/ml-semantic-regex.git
cd semantic-regex
```

2. Install uv, see <https://docs.astral.sh/uv/getting-started/installation/>.

3. Run the test suite:

```bash
uv run pytest
uv run pytest --capture=no  # Show print statements
```
