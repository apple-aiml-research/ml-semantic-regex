#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Test semantic regex generation on hand-labeled features

import json
from contextlib import redirect_stdout

import util
import features
import methods


def generate_data(feature, n_data_examples, n_tokens_per_sample):
    """Generate activating data for a feature."""
    positive_data = feature.get_activating_examples()
    if len(positive_data[0]) == 0 or len(positive_data[1]) == 0:
        raise ValueError(f"No activating examples found for feature {feature}")
    positive_data = util.remove_duplicate_snippets(*util.batch_snip_activations(*positive_data, length_in_tokens=n_tokens_per_sample))
    positive_data = positive_data[0][:n_data_examples], positive_data[1][:n_data_examples]
    return positive_data


def run_test(feature, expected_outputs, semantic_regex_method, model, n_data_examples, n_tokens_per_sample, sampling_method):
    """Run a single test of semantic regex generation."""
    with redirect_stdout(None):
        semantic_regex_result = semantic_regex_method.generate(
            feature,
            model_name=model,
            n_data_examples=n_data_examples,
            n_tokens_per_sample=n_tokens_per_sample,
            show_activations=False,
            show_null_activations=False,
            merge_activations=True,
            show_breaks=True,
            activation_threshold=0.3,
            sampling_method=sampling_method,
            logging=False)
    semantic_regex = semantic_regex_result['description']['description']
    passed = semantic_regex in expected_outputs
    return passed, semantic_regex


def run_tests(parameters, num_runs=5, write_results=False, types={}):
    """Run tests of semantic regex generation on hand-labeled features."""
    n_data_examples = parameters.get('n_data_examples', 10)
    n_tokens_per_sample = parameters.get('n_tokens_per_sample', 32)
    model = parameters.get('model', 'gpt-4o-mini')
    sampling_method = parameters.get('sampling_method', 'top')

    with open("prompts/prompt_test_features.json", "r", encoding="utf-8") as f:
        test_features = json.load(f)

    if types:
        test_features = [f for f in test_features if f['type'] in types]

    output = []
    semantic_regex_method = methods.SemanticRegex(output_dir='./artifacts', seed=97)
    for test_feature in test_features:
        feature = features.Feature(
            model_id=test_feature['model_id'],
            layer=test_feature['layer'],
            index=test_feature['index'],
        )
        expected_outputs = test_feature['expected_semantic_regex']
        feature_output = {
            'test_name': test_feature['name'],
            'model_id': feature.model_id,
            'layer': feature.layer,
            'index': feature.index,
            'type': test_feature['type'],
            'expected_outputs': expected_outputs,
            'results': [],
            'successes': [],
            'success_rate': 0
        }
        for test_run in range(num_runs):
            passed, semantic_regex = run_test(feature, expected_outputs, semantic_regex_method, model, n_data_examples, n_tokens_per_sample, sampling_method)
            feature_output['results'].append(semantic_regex)
            feature_output['successes'].append(int(passed))
        feature_output['success_rate'] = sum(feature_output['successes']) / num_runs
        output.append(feature_output)
        print(f"{feature_output['success_rate']:.2%}: {feature_output['results']} == {expected_outputs}")

    if write_results:
        with open(f'evaluation_results.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)

    return output
