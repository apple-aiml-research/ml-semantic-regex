#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Generate and evaluate feature descriptions.

import os
import time
import torch
import argparse
import itertools
import numpy as np
from huggingface_hub import login
from transformer_lens import HookedTransformer

from dotenv import load_dotenv
load_dotenv()

import util
import methods
import features

def get_feature_source_parameters(model_id, feature_source, layer):
    """Get number of layers and SAE size for a given model and feature source."""
    feature_index = 0
    feature = features.Feature(model_id, f"{layer}-{feature_source}", feature_index)
    try:
        model_num_layers = feature.get_model_num_layers()
        num_sae_features = feature.get_sae_size()
    except Exception as e:
        if str(e).startswith("No activating"): # Some features do not have activating data, so try again
            num_tries = 5
            for i in range(num_tries):
                try:
                    feature = features.Feature(model_id, f"{layer}-{feature_source}", feature_index+i)
                    model_num_layers = feature.get_model_num_layers()
                    num_sae_features = feature.get_sae_size()
                    break
                except Exception as e:
                    if str(e).startswith("No activating"):
                        continue
                    else:
                        raise e
        else:
            raise e
    return model_num_layers, num_sae_features

def main(args):
    """Generate and evaluate feature descriptions."""
    layer = 0
    if args.layers:
        layer = args.layers[0]
    model_num_layers, num_sae_features = get_feature_source_parameters(args.model_id, args.feature_source, layer)
    util.set_seed(args.seed)

    # Set of select feature layers
    if args.layers is None or len(args.layers) == 0: # randomly select layers
        if args.num_layers > 0:
            args.layers = np.random.choice(range(model_num_layers), size=args.num_layers, replace=False)
        else:
            args.layers = [l for l in range(model_num_layers)]
    assert args.feature_source is not None, "If no layers are specified, feature_source must be specified."
    layers = [f"{i}-{args.feature_source}" for i in args.layers]

    # Set of select feature indices
    if args.indices is None or len(args.indices) == 0:
        assert args.num_indices > 0, "If no indices are specified, num_indices must be greater than 0."
        args.indices = np.random.choice(range(num_sae_features), size=args.num_indices, replace=False)
    indices = [int(i) for i in args.indices]

    # Generate semantic regexes for each feature
    options = list(itertools.product(layers, indices))
    sleep_time = 60
    max_sleep_time = 600
    for i, (layer, index) in enumerate(options):
        print(f"PROCESSING {i+1}/{len(options)}")
        feature = features.Feature(args.model_id, layer, index)
        method_arguments = {
            "feature": feature,
            "model_name": args.description_model_name,
            "data_model_name": args.data_model_name,
            "eval_model_name": args.eval_model_name,
            "n_data_examples": args.n_data_examples,
            "n_tokens_per_sample": args.n_tokens_per_sample,
            "show_breaks": args.show_breaks,
            "ignore_first_token": args.ignore_first_token,
            "logging": args.logging,
            "metrics": args.metrics,
            "activation_threshold": args.activation_threshold,
            "sampling_method": args.sampling_method,
        }
        for method in args.methods: # Doing methods together allows them to share a cache
            try:
                result = method.generate(**method_arguments)
                if result['description']['description'].strip() == 'N/A':
                    print(f"No description generated for {feature}, skipping evaluation.")
                    continue
                if args.evaluate:
                    evaluation_result = method.evaluate(description=result['description']['description'], **method_arguments)
                    result["evaluation"].update(evaluation_result)
                method.write_result(result)
                sleep_time = 60 # Reset sleep time after a successful request
            except Exception as e:
                if '429' in str(e): # Rate limit error
                    print(f"Rate limited, waiting {sleep_time} seconds...")
                    time.sleep(sleep_time)
                    sleep_time = min(sleep_time * 2, max_sleep_time) # Exponential backoff up to 10 minutes
                    if sleep_time < max_sleep_time:
                        options.append((layer, index)) # retry same feature
                elif str(e).startswith("No activating"): # No data on this feature
                    print(f"No activations found for {feature}, skipping.")
                    break
                else:
                    print(f"Error generating semantic regex for {feature}: {e}")
                continue



if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--methods', type=str, nargs='+',  default=['semantic_regex'], choices=['semantic_regex', 'oai_token-act-pair', 'eleuther_acts_top20'],
                        help='Which method to run.')
    parser.add_argument('--seed', type=int, default=97,
                        help='Random seed for selecting layers and features.')
    parser.add_argument('--evaluate', action="store_true",
                        help='Whether to evaluate the generated description.')

    parser.add_argument('--model_id', '-m', type=str, default='gpt2-small',
                        help='Neuronpedia model ID')
    parser.add_argument('--feature_source', '-f', type=str, default='res-jb',
                        help='Neuronpedia feature source')

    parser.add_argument('--layers', type=str, nargs='+',
                        help='Neuronpedia layer(s).')
    parser.add_argument('--num_layers', type=int, default=0,
                        help='Number of layers to generate semantic regexes for')

    parser.add_argument('--indices', type=str, nargs='+',
                        help='Neuronpedia feature index')
    parser.add_argument('--num_indices', type=int, default=0,
                        help='Number of indices to generate semantic regexes for per layer')

    parser.add_argument('--description_model_name', type=str, default='gpt-4o-mini',
                        help='OpenAI model to use to generate description.')
    parser.add_argument('--data_model_name', type=str, default='gpt-4o-mini',
                        help='OpenAI model to use to generate data from the description.')
    parser.add_argument('--eval_model_name', type=str, default='gpt-4o-mini',
                        help='OpenAI model to use to evaluate description.')

    parser.add_argument('--n_data_examples', type=int, default=10,
                        help='Number of data examples to use')
    parser.add_argument('--n_tokens_per_sample', type=int, default=32,
                        help='Number of tokens per data examples')
    parser.add_argument('--show_breaks', type=bool, default=True,
                        help='Whether to show breaks between examples in the visualization')
    parser.add_argument('--ignore_first_token', type=bool, default=True,
                        help='Whether to ignore the first token activations (usually a special token)')
    parser.add_argument('--logging', type=bool, default=False,
                        help='Whether to print logging information')
    parser.add_argument('--activation_threshold', type=float, default=0.3,
                        help='Activation threshold as a fraction of the max activation for displaying activations')
    parser.add_argument('--sampling_method', type=str, default='top', choices=['top', 'random'],
                        help='Method for sampling data examples from the activating examples.')

    parser.add_argument('--metrics', type=str, nargs='+', default=['clarity', 'responsiveness', 'purity', 'detection', 'fuzzing', 'faithfulness'], choices=['clarity', 'responsiveness', 'purity', 'detection', 'fuzzing', 'faithfulness'],
                        help='Which evaluation metrics to compute.')

    parser.add_argument('--git_hash', type=str, default=None,
                        help='Git hash to append to directory to save results to.')
    parser.add_argument('--output_dir_suffix', type=str, default='',
                        help='Suffix to append to output directory.')

    hf_token = os.getenv("HUGGINGFACE_HUB_TOKEN")
    assert hf_token is not None, "HUGGINGFACE_HUB_TOKEN environment variable not set."
    login(token=hf_token)

    args = parser.parse_args()
    args.output_dir = './artifacts/experiments/temp'

    subject_model = None
    print(f"Querying features locally? {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        subject_model = HookedTransformer.from_pretrained_no_processing(args.model_id, device='cuda')
        subject_model.eval()
        print('Computing feature queries on device')

    method_map = {
        'semantic_regex': methods.SemanticRegex,
        'oai_token-act-pair': methods.OAITokenActPair,
        'eleuther_acts_top20': methods.EleutherActsTop20,
    }
    method_instances = []
    for method in args.methods:
        if method in method_map:
            output_subdir = f"{args.git_hash}_{method}_{args.model_id}_{args.feature_source}"
            if args.output_dir_suffix and len(args.output_dir_suffix) > 0:
                output_subdir += f"_{args.output_dir_suffix}"
            method_output_dir = os.path.join(args.output_dir, 'experiments', output_subdir)
            method_input_dir = os.path.join(os.getcwd(), 'artifacts', 'experiments', output_subdir)
            method_instances.append(
                method_map[method](method_output_dir, args.seed, method_input_dir, subject_model)
            )
        else:
            raise ValueError(f"Unknown method: {method}.")
    args.methods = method_instances

    main(args)
