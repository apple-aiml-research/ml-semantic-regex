#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# LLM feature description methods.

import os
import json
from openai import OpenAI
from typing import List
from abc import ABC, abstractmethod
from jsonschema import validate

from dotenv import load_dotenv
load_dotenv()

import util
import features
import evaluate

class FeatureDescription(ABC):
    """Abstract base class for feature description methods."""

    def __init__(self, output_dir: str, seed: int, input_dir: str = None, subject_model = None):
        """Args: output_dir: Directory to save output artifacts."""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.output_dir = output_dir
        self.input_dir = input_dir if input_dir is not None else output_dir
        with open("feature_description_schema.json") as f:
            self.result_schema = json.load(f)
        self.client = OpenAI(api_key=self.openai_api_key)
        self.seed = seed

        self.subject_model = subject_model

    @abstractmethod
    def generate(
            self,
            feature: features.Feature,
            model_name: str,
            logging: bool = False,
            **kwargs
        ) -> dict:
        """Generate a feature description."""
        pass

    def evaluate(
            self,
            metrics: List[str],
            description: str,
            feature: features.Feature,
            eval_model_name: str,
            data_model_name: str,
            ignore_first_token: bool,
            show_breaks: bool,
            logging: bool,
            **kwargs) -> dict:
        """Evaluate the feature description using specified metrics.
        Args:
            metrics: List of metric names to compute.
            description: The feature description to evaluate.
            feature: The Feature object associated with the description.
            eval_model_name: Name of the model used for description-feature match evaluation.
            data_model_name: Name of the model used for generating data examples.
            ignore_first_token: Whether to ignore the activation of the first token if its a special token in the examples.
            show_breaks: Whether to include line breaks in the examples.
            logging: Whether to print out metric computation details.
        Returns:
            A dictionary mapping metric names to their computed results."""

        # Check if results already exist on disk
        if os.path.exists(self.result_input_filename(feature)):
            with open(self.result_input_filename(feature), "r") as f:
                result = json.load(f)
            if "evaluation" in result:
                existing_metrics = [key for key in result["evaluation"].keys() if 'value' in result["evaluation"][key] and result["evaluation"][key]['value'] is not None]
                remaining_metrics = [m for m in metrics if m not in existing_metrics]
                if len(remaining_metrics) == 0:
                    print(f"{self.name.upper()} - Accessing evaluation results from disk for feature {feature}")
                    return result["evaluation"]
                else:
                    print(f"{[m.upper() for m in existing_metrics]} already computed, computing remaining metrics: {[m.upper() for m in remaining_metrics]}")
                    metrics = remaining_metrics

        util.set_seed(self.seed)
        evaluator = evaluate.Evaluator(
            metrics,
            eval_model_name,
            data_model_name,
            ignore_first_token,
            show_breaks,
            self.is_semantic_regex,
            logging=logging,
            subject_model=self.subject_model
        )
        evaluation_result = evaluator.evaluate(description, feature)
        return evaluation_result

    def write_result(self, result: dict) -> None:
        """Write the result to a JSON file and validate against the schema.
        Args:
            result: The result dictionary to write and validate.
        """
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        validate(instance=result, schema=self.result_schema)
        feature = features.Feature(
            model_id = result["feature"]['model_id'],
            layer = result["feature"]['layer'],
            index = result["feature"]['index'],
        )
        with open(self.result_output_filename(feature), "w") as f:
            json.dump(result, f, indent=2)

    def result_output_filename(self, feature: features.Feature) -> str:
        output_filename = os.path.join(self.output_dir, f"{feature.model_id}_{feature.layer}_{feature.index}.json")
        return output_filename

    def result_input_filename(self, feature: features.Feature) -> str:
        input_filename = os.path.join(self.input_dir, f"{feature.model_id}_{feature.layer}_{feature.index}.json")
        return input_filename

    def format_message(self, role: str, content: str) -> dict:
        return {
            "role": role,
            "content": content
        }

    def generate_and_evaluate(self, **kwargs) -> dict:
        """Generate a feature description and evaluate it using specified metrics."""
        result = self.generate(
            **kwargs
        )
        if 'metrics' not in kwargs:
            kwargs['metrics'] = []
        evaluation_result = self.evaluate(
            metrics=kwargs['metrics'],
            description=result['description']['description'],
            feature=kwargs['feature'],
            eval_model_name=kwargs['eval_model_name'],
            data_model_name=kwargs['data_model_name'],
            ignore_first_token=kwargs['ignore_first_token'],
            show_breaks=kwargs['show_breaks'],
            logging=kwargs['logging'],
        )
        result["evaluation"].update(evaluation_result)
        return result

    def get_existing_explanation(self, feature: features.Feature, model_name: str) -> str | None:
        """Check if an explanation already exists for the given feature.
        Args:
            feature: The Feature object to check.
        Returns:
            True if an explanation file exists, False otherwise.
        """
        explanation_file = os.path.join(self.explanation_dir, f'{str(feature)}.json')
        if os.path.exists(explanation_file):
            with open(explanation_file, 'r') as f:
                existing_explanations = json.load(f)
            for explanation in existing_explanations:
                if explanation.get("explanationModelName") == model_name and explanation.get('typeName') == self.name:
                    return explanation["description"]