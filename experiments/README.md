# Semantic Regex: Experiments

This repository contains code to generate and evaluate semantic regex feature descriptions, and to replicate the experiments from the paper.

## Installation

```bash
# Clone this repo
git clone https://github.com/apple/ml-semantic-regex
cd ml-semantic-regex/experiments

# Install uv (if not already installed)
# https://docs.astral.sh/uv/getting-started/installation/
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and create virtual environment
uv sync

# Activate the environment (optional, but recommended for running scripts directly)
source .venv/bin/activate

# For Jupyter notebooks
uv run jupyter lab
```

## Usage

This repo is designed to generate and evaluate semantic regexes on LLM features.

### Generating and Evaluating Feature Descriptions
- Example usage: `semantic_regex.ipynb`
- Large-scale experiments: `run_job.py`

### Pre-generated Feature Descriptions
- Results from all experiments are in `artifacts/experiments/`
- These can be explored interactively via our [**viewer**](https://apple.github.io/ml-semantic-regex/)

## Results

To replicate the main results from our paper:

- **Section 5.1: Semantic Regexes are as Accurate as Natural Language**
  Benchmarking code: `notebooks/benchmarking_results.ipynb`

- **Section 5.2: Semantic Regexes Improve Conciseness and Consistency**
  Conciseness: `notebooks/benchmarking_results.ipynb`
  Consistency: `notebooks/abstraction_results.ipynb`

- **Section 5.3: Semantic Regexes Reflect Feature Complexity**
  Code: `notebooks/abstraction_results.ipynb`

- **Section 5.4: Semantic Regexes Help People Build Mental Models of LLM Features**
  Raw responses: `human_study/responses/`
  Analysis: `human_study/human_study_evaluation.ipynb`


## Repo Structure
```
experiments/
│
├── artifacts/      # gpt2 and gemma feature description results
├── human_study/    # data and results from the user study
├── methods/        # feature description methods
│   ├── base_feature_description.py    # base class
│   ├── semantic_regex_description.py  # semantic regex method
│   └── ...
├── metrics/        # evaluation metrics
├── notebooks/      # experiment notebooks for paper results
│   ├── abstraction_results.ipynb      # feature complexity analysis
│   ├── benchmarking_results.ipynb     # quantitative comparison
│   ├── consistency_results.ipynb      # feature description consistency analysis
│   └── ...
├── prompts/         # prompts for methods and metrics
├── tests/           # tests
├── evaluate.py      # feature description evaluation
├── features.py      # based class for LLM features
├── util.py          # utility functions
├── run_job.py       # experiment script
├── pyproject.toml   # project dependencies
└── README.md
```