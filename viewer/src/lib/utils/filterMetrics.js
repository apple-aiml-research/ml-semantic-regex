// For licensing see accompanying LICENSE file.
// Copyright (C) 2025 Apple Inc. All Rights Reserved.

/**
 * Filters artifacts to only include features that:
 * 1. Have all 6 metrics (clarity, responsiveness, purity, detection, fuzzing, faithfulness)
 * 2. The same feature (model_id + layer + index) has all 6 metrics across ALL experiments it appears in
 *
 * @param {Array} artifacts - Array of artifact objects from artifacts_index.json
 * @returns {Array} - Filtered artifacts array
 */
export function filterCompleteFeatures(artifacts) {
	const REQUIRED_METRICS = [
		'clarity',
		'responsiveness',
		'purity',
		'detection',
		'fuzzing',
		'faithfulness'
	];
	const EXCLUDED_EXPERIMENTS = ['figures', 'human_study'];

	// Filter out excluded experiments
	const validArtifacts = artifacts.filter(
		(artifact) => !EXCLUDED_EXPERIMENTS.some((excluded) => artifact.experiment.includes(excluded))
	);

	// Helper to get feature key
	const getFeatureKey = (artifact) => {
		const feature = artifact.content?.feature;
		if (!feature) return null;
		return `${feature.model_id}:${feature.layer}:${feature.index}`;
	};

	// Helper to check if an artifact has all required metrics
	const hasAllMetrics = (artifact) => {
		if (!artifact.content?.evaluation) return false;
		return REQUIRED_METRICS.every(
			(metric) =>
				artifact.content.evaluation[metric]?.value != null &&
				!isNaN(artifact.content.evaluation[metric].value)
		);
	};

	// Group artifacts by feature key
	const featureGroups = new Map();

	validArtifacts.forEach((artifact) => {
		const key = getFeatureKey(artifact);
		if (!key) return;

		if (!featureGroups.has(key)) {
			featureGroups.set(key, []);
		}
		featureGroups.get(key).push(artifact);
	});

	// Find features where ALL instances have all metrics
	const completeFeatureKeys = new Set(
		[...featureGroups.entries()]
			.filter(([_, artifacts]) => artifacts.every(hasAllMetrics))
			.map(([key, _]) => key)
	);

	// Return only artifacts for complete features
	return validArtifacts.filter((artifact) => {
		const key = getFeatureKey(artifact);
		return key && completeFeatureKeys.has(key);
	});
}
