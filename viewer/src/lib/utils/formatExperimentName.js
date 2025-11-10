// For licensing see accompanying LICENSE file.
// Copyright (C) 2025 Apple Inc. All Rights Reserved.

export const experimentTypeMap = {
	semantic_regex: 'Semantic Regex',
	eleuther_acts_top20: 'Max Acts',
	'oai_token-act-pair': 'Token Act Pair'
};

export function formatExperimentName(name, experimentOnly = false) {
	const parts = name.split('_');

	// Check if first part is a commit hash (6 hex characters)
	const firstPart = parts[0];
	const isCommitHash = /^[a-f0-9]{6}$/i.test(firstPart);

	// Remove commit hash if present
	if (isCommitHash) {
		parts.shift();
	}

	// Check if the first two parts match any experiment type
	let formattedType = '';
	let remainingParts = [...parts];

	for (const [key, value] of Object.entries(experimentTypeMap)) {
		const keyParts = key.split('_');
		const testParts = parts.slice(0, keyParts.length).join('_');

		if (testParts === key) {
			formattedType = value;
			remainingParts = parts.slice(keyParts.length);
			break;
		}
	}

	// If no match found, just capitalize first part
	if (!formattedType) {
		formattedType = parts[0].charAt(0).toUpperCase() + parts[0].slice(1);
		remainingParts = parts.slice(1);
	}

	// Return just the type if experimentOnly is true
	if (experimentOnly) {
		return formattedType;
	}

	// Format the remaining parts
	const formatted = remainingParts.map((part) => part.charAt(0).toUpperCase() + part.slice(1));

	// Join experiment type separately, then add remaining parts with >
	if (formatted.length > 0) {
		return formattedType + ' / ' + formatted.join(' / ');
	}
	return formattedType;
}

// New function to get the experiment type
export function getExperimentType(name) {
	const parts = name.split('_');

	// Remove commit hash if present
	const firstPart = parts[0];
	const isCommitHash = /^[a-f0-9]{6}$/i.test(firstPart);
	if (isCommitHash) {
		parts.shift();
	}

	// Check if the first two parts match any experiment type
	for (const [key, value] of Object.entries(experimentTypeMap)) {
		const keyParts = key.split('_');
		const testParts = parts.slice(0, keyParts.length).join('_');

		if (testParts === key) {
			return key; // Return the raw key like 'semantic_regex'
		}
	}

	return parts[0] || null;
}
