// For licensing see accompanying LICENSE file.
// Copyright (C) 2025 Apple Inc. All Rights Reserved.

export async function load({ params }) {
	return {
		experiment: params.experiment
	};
}
