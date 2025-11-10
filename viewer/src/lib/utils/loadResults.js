// For licensing see accompanying LICENSE file.
// Copyright (C) 2025 Apple Inc. All Rights Reserved.

import artifactsIndex from '../assets/artifacts_index.json';

export function getAllResults() {
	return artifactsIndex;
}

function parseResultPath(path) {
	const pathParts = path.replace('experiments/', '').split('/');
	return {
		experiment: pathParts[0],
		result: pathParts[1].replace('.json.gz', '')
	};
}

export function getResultByModelLayerIndex(model, layer, index, experiment) {
	// Convert the route params back to the original filename format
	const filename = `${model}_${layer}_${index}`;

	for (let item of artifactsIndex) {
		if (item.fileName == filename) {
			// If experiment is specified, check if the path contains it
			if (experiment) {
				const pathParts = item.fetchPath.split('/');
				if (pathParts.includes(experiment)) {
					return item;
				}
			}
		}
	}
}

// Helper function to extract route params from a result object
export function getRouteParamsFromResult(result) {
	const { model_id, layer, index } = result.content.feature;
	return {
		model: model_id,
		layer: layer,
		index: index.toString()
	};
}

// Get all results with their corresponding route parameters
export function getAllResultsWithRoutes() {
	return getAllResults().map((result) => ({
		...result,
		routeParams: getRouteParamsFromResult(result)
	}));
}

// New helper functions for dropdown options
export function getAvailableExperiments() {
	const results = getAllResults();
	const experiments = new Set();
	results.forEach((result) => {
		if (result.experiment) {
			experiments.add(result.experiment);
		}
	});
	return Array.from(experiments).sort();
}

export function getAvailableModels(experiment = null) {
	const results = getAllResults();
	const models = new Set();
	results.forEach((result) => {
		if (result.content?.feature?.model_id && (!experiment || result.experiment === experiment)) {
			models.add(result.content.feature.model_id);
		}
	});
	return Array.from(models).sort();
}

export function getAvailableLayersForModel(modelId, experiment = null) {
	const results = getAllResults();
	const layers = new Set();
	results.forEach((result) => {
		if (
			result.content?.feature?.model_id === modelId &&
			result.content?.feature?.layer !== undefined &&
			(!experiment || result.experiment === experiment)
		) {
			layers.add(result.content.feature.layer);
		}
	});
	return Array.from(layers).sort((a, b) => a - b);
}

export function getAvailableIndicesForModelLayer(modelId, layer, experiment = null) {
	const results = getAllResults();
	const indices = new Set();
	results.forEach((result) => {
		if (
			result.content?.feature?.model_id === modelId &&
			result.content?.feature?.layer === layer &&
			result.content?.feature?.index !== undefined &&
			(!experiment || result.experiment === experiment)
		) {
			indices.add(result.content.feature.index);
		}
	});
	return Array.from(indices).sort((a, b) => a - b);
}

// Get a random feature from a specific experiment
export function getRandomFeatureFromExperiment(experiment) {
	const results = getAllResults();
	const featuresInExperiment = results.filter(
		(result) =>
			result.experiment === experiment &&
			result.content?.feature?.model_id &&
			result.content?.feature?.layer !== undefined &&
			result.content?.feature?.index !== undefined
	);

	if (featuresInExperiment.length === 0) return null;

	const randomResult =
		featuresInExperiment[Math.floor(Math.random() * featuresInExperiment.length)];

	return {
		model: randomResult.content.feature.model_id,
		layer: randomResult.content.feature.layer,
		index: randomResult.content.feature.index
	};
}
