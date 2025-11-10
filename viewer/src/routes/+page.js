// For licensing see accompanying LICENSE file.
// Copyright (C) 2025 Apple Inc. All Rights Reserved.

import { getAllResults } from '$lib/utils/loadResults.js';

export async function load() {
	return {
		allExperimentResults: getAllResults()
	};
}
