// For licensing see accompanying LICENSE file.
// Copyright (C) 2025 Apple Inc. All Rights Reserved.

import { getResultByModelLayerIndex } from '$lib/utils/loadResults.js';
import { error } from '@sveltejs/kit';
import { base } from '$app/paths';
import decompress from 'brotli/decompress';

export async function load({ params, fetch }) {
	const { experiment, model, layer, index } = params;

	// Find the result that matches these parameters within the specific experiment
	const result = getResultByModelLayerIndex(model, layer, parseInt(index), experiment);

	if (!result) {
		throw error(404, 'Feature not found');
	}

	const resp = await fetch(base + '/' + result.fetchPath);
	const data = decompress(new Uint8Array(await resp.arrayBuffer()));
	const jsonData = JSON.parse(new TextDecoder().decode(data));

	return {
		experiment,
		content: jsonData[result.fileName]
	};
}
