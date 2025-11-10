<!--
For licensing see accompanying LICENSE file.
Copyright (C) 2025 Apple Inc. All Rights Reserved.
-->

<script>
	let { data } = $props();
	import { base } from '$app/paths';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { formatExperimentName } from '$lib/utils/formatExperimentName';
	import { filterCompleteFeatures } from '$lib/utils/filterMetrics';

	// Get original counts by experiment
	const experimentCounts = $derived(
		data.allExperimentResults.reduce((acc, result) => {
			acc[result.experiment] = (acc[result.experiment] || 0) + 1;
			return acc;
		}, {})
	);

	// Filter artifacts and group by experiment (for metrics)
	const filteredArtifacts = $derived(filterCompleteFeatures(data.allExperimentResults));

	const experiments = $derived(
		filteredArtifacts.reduce((acc, result) => {
			if (!acc[result.experiment]) {
				acc[result.experiment] = [];
			}
			acc[result.experiment].push(result);
			return acc;
		}, {})
	);

	const experimentEntries = $derived(Object.entries(experiments));

	const numDecimalPlaces = 2;

	const authors = [
		{ name: 'Angie Boggust', affiliation: [1], marker: '*' },
		{ name: 'Donghao Ren', affiliation: [2] },
		{ name: 'Yannick Assogba', affiliation: [2] },
		{ name: 'Dominik Moritz', affiliation: [2] },
		{ name: 'Arvind Satyanarayan', affiliation: [1] },
		{ name: 'Fred Hohman', affiliation: [2] }
	];

	const affiliations = ['MIT CSAIL', 'Apple'];

	function getAffiliationNames(affiliationIndices) {
		return affiliationIndices.map((i) => affiliations[i - 1]).join(', ');
	}
</script>

<div class="min-h-screen bg-gray-50">
	<div class="mx-auto max-w-4xl px-4 py-8 sm:py-12">
		<div class="mb-8 sm:mb-12">
			<h1 class="mb-4 text-2xl font-bold text-gray-900 sm:text-3xl md:text-4xl">
				Semantic Regexes: Auto-Interpreting LLM Features with a Structured Language
			</h1>

			<div
				class="text-md mb-3 flex flex-wrap items-baseline gap-x-1 text-sm text-gray-600 sm:text-base"
			>
				{#each authors as author, index}
					<span class="whitespace-nowrap">
						{author.name}<sup class="text-xs"
							>{author.affiliation.join(',')}{#if author.marker}{author.marker}{/if}</sup
						>{#if index < authors.length - 1},&nbsp;{/if}
					</span>
				{/each}
			</div>

			<div class="mb-2 flex flex-wrap gap-x-2 gap-y-1 text-xs text-gray-500 sm:text-sm">
				{#each affiliations as affiliation, index}
					<div><sup>{index + 1}</sup>{affiliation}</div>
				{/each}
				<div><sup>*</sup>Work done at Apple</div>
			</div>

			<div
				class="text-md mb-3 flex flex-wrap items-center gap-2 text-sm text-gray-600 sm:gap-3 sm:text-base"
			>
				<span class=""> arXiv </span>
				<span class="text-gray-400">•</span>
				<span>October 2025</span>
			</div>

			<p class="mb-4 text-sm leading-relaxed text-gray-600">
				Semantic regexes are an automated interpretability method that describe LLM features using a
				structured language. Semantic regexes provide accurate, concise, and consistent feature
				descriptions that help humans build mental models of feature activations.
			</p>

			<div class="flex flex-wrap gap-2 sm:gap-3">
				<a
					href="https://arxiv.org/abs/2510.06378"
					class="inline-flex items-center gap-2 rounded-full border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
				>
					<Icon icon={'file-alt'} />
					<span>Paper</span>
				</a>
				<a
					href="https://github.com/apple/ml-semantic-regex"
					class="inline-flex items-center gap-2 rounded-full border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
				>
					<Icon icon={'github'} />
					<span>GitHub</span>
				</a>
				<a
					href="https://pypi.org/project/semantic-regex/"
					class="inline-flex items-center gap-2 rounded-full border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
				>
					<Icon icon={'python'} />
					<span>Python Package</span>
				</a>
				<a
					href="https://apple.github.io/ml-semantic-regex"
					class="inline-flex items-center gap-2 rounded-full border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
				>
					<Icon icon={'line-chart'} />
					<span>Viewer</span>
				</a>
			</div>
		</div>

		<!-- <hr class="border-gray-300 pb-12" /> -->

		<div class="space-y-4">
			{#each experimentEntries as [experimentName, results]}
				<a
					href={experimentName}
					class="block rounded-lg border border-gray-200 bg-white p-4 duration-200 hover:scale-[1.01] hover:shadow-md sm:p-6"
				>
					<div class="flex items-start justify-between gap-3">
						<div class="min-w-0 flex-1">
							<h2 class="mb-3 text-lg font-semibold text-gray-900 sm:text-xl">
								{formatExperimentName(experimentName)}
							</h2>

							<!-- Results count (using original count) -->
							<div class="mb-3 flex flex-wrap items-center gap-2 text-xs text-gray-500">
								<div class="flex items-center gap-1">
									<Icon icon={'file-alt'} color="text-gray-500" />
									<span>
										{experimentCounts[experimentName].toLocaleString('en-US')}{experimentCounts[
											experimentName
										] === 1
											? ' result'
											: ' results'}
									</span>
								</div>
								<div>•</div>
								<div class="break-all font-mono">{experimentName}</div>
							</div>

							<hr class="mb-4 border-gray-200" />

							<!-- Metrics grid - responsive: 1 column on mobile, 2 on larger screens -->
							<div class="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2 sm:gap-x-12">
								{#if results.some((r) => r.content?.evaluation?.clarity !== undefined)}
									{@const clarityResults = results.filter(
										(r) => r.content.evaluation.clarity !== undefined
									)}
									{@const clarity =
										clarityResults
											.map((r) => r.content.evaluation.clarity.value)
											.reduce((a, b) => a + b, 0) / clarityResults.length}
									<div class="flex items-center justify-between gap-2">
										<span class="flex-shrink-0 text-gray-600">Clarity</span>
										<div class="flex flex-shrink-0 items-center gap-2">
											<span class="font-medium text-gray-800"
												>{(clarity * 100).toFixed(numDecimalPlaces)}%</span
											>
											<ProgressBar value={clarity} min={0} max={1} height="h-2" width="w-16" />
										</div>
									</div>
								{/if}

								{#if results.some((r) => r.content?.evaluation?.responsiveness !== undefined)}
									{@const responsivenessResults = results.filter(
										(r) => r.content.evaluation.responsiveness !== undefined
									)}
									{@const responsiveness =
										responsivenessResults
											.map((r) => r.content.evaluation.responsiveness.value)
											.reduce((a, b) => a + b, 0) / responsivenessResults.length}
									<div class="flex items-center justify-between gap-2">
										<span class="flex-shrink-0 text-gray-600">Responsiveness</span>
										<div class="flex flex-shrink-0 items-center gap-2">
											<span class="font-medium text-gray-800"
												>{(responsiveness * 100).toFixed(numDecimalPlaces)}%</span
											>
											<ProgressBar
												value={responsiveness}
												min={0}
												max={1}
												height="h-2"
												width="w-16"
											/>
										</div>
									</div>
								{/if}

								{#if results.some((r) => r.content?.evaluation?.purity !== undefined)}
									{@const purityResults = results.filter(
										(r) => r.content.evaluation.purity !== undefined
									)}
									{@const purity =
										purityResults
											.map((r) => r.content.evaluation.purity.value)
											.reduce((a, b) => a + b, 0) / purityResults.length}
									<div class="flex items-center justify-between gap-2">
										<span class="flex-shrink-0 text-gray-600">Purity</span>
										<div class="flex flex-shrink-0 items-center gap-2">
											<span class="font-medium text-gray-800"
												>{(purity * 100).toFixed(numDecimalPlaces)}%</span
											>
											<ProgressBar value={purity} min={0} max={1} height="h-2" width="w-16" />
										</div>
									</div>
								{/if}

								{#if results.some((r) => r.content?.evaluation?.detection !== undefined)}
									{@const detectionResults = results.filter(
										(r) => r.content.evaluation.detection !== undefined
									)}
									{@const detection =
										detectionResults
											.map((r) => r.content.evaluation.detection.value)
											.reduce((a, b) => a + b, 0) / detectionResults.length}
									<div class="flex items-center justify-between gap-2">
										<span class="flex-shrink-0 text-gray-600">Detection</span>
										<div class="flex flex-shrink-0 items-center gap-2">
											<span class="font-medium text-gray-800"
												>{(detection * 100).toFixed(numDecimalPlaces)}%</span
											>
											<ProgressBar value={detection} min={0} max={1} height="h-2" width="w-16" />
										</div>
									</div>
								{/if}

								{#if results.some((r) => r.content?.evaluation?.fuzzing !== undefined)}
									{@const fuzzingResults = results.filter(
										(r) => r.content.evaluation.fuzzing !== undefined
									)}
									{@const fuzzing =
										fuzzingResults
											.map((r) => r.content.evaluation.fuzzing.value)
											.reduce((a, b) => a + b, 0) / fuzzingResults.length}
									<div class="flex items-center justify-between gap-2">
										<span class="flex-shrink-0 text-gray-600">Fuzzing</span>
										<div class="flex flex-shrink-0 items-center gap-2">
											<span class="font-medium text-gray-800"
												>{(fuzzing * 100).toFixed(numDecimalPlaces)}%</span
											>
											<ProgressBar value={fuzzing} min={0} max={1} height="h-2" width="w-16" />
										</div>
									</div>
								{/if}

								{#if results.some((r) => r.content?.evaluation?.faithfulness !== undefined)}
									{@const faithfulnessResults = results.filter(
										(r) => r.content.evaluation.faithfulness !== undefined
									)}
									{@const faithfulness =
										faithfulnessResults
											.map((r) => r.content.evaluation.faithfulness.value)
											.reduce((a, b) => a + b, 0) / faithfulnessResults.length}
									<div class="flex items-center justify-between gap-2">
										<span class="flex-shrink-0 text-gray-600">Faithfulness</span>
										<div class="flex flex-shrink-0 items-center gap-2">
											<span class="font-medium text-gray-800"
												>{(faithfulness * 100).toFixed(numDecimalPlaces)}%</span
											>
											<ProgressBar value={faithfulness} min={0} max={1} height="h-2" width="w-16" />
										</div>
									</div>
								{/if}
							</div>
						</div>
						<Icon color="text-gray-400" icon="chevron-right"/>
					</div>
				</a>
			{/each}
		</div>
	</div>
</div>
