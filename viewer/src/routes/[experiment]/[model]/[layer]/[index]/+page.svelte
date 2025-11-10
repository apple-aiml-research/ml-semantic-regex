<!--
For licensing see accompanying LICENSE file.
Copyright (C) 2025 Apple Inc. All Rights Reserved.
-->

<script>
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import Breadcrumbs from '$lib/components/Breadcrumbs.svelte';
	import DataExamples from '$lib/components/DataExamples.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import { base } from '$app/paths';
	import { formatExperimentName, experimentTypeMap } from '$lib/utils/formatExperimentName';
	import artifactsIndex from '$lib/assets/artifacts_index.json';

	let { data } = $props();

	// State for scroll shadow
	let showShadow = $state(false);

	// Scroll listener to show/hide shadow
	function handleScroll() {
		showShadow = window.scrollY > 0;
	}

	// State for selected metric
	let selectedMetric = $state(null);

	// State for metric example type toggle
	let selectedMetricExampleType = $state('positive');

	// Helper to extract experiment type and remainder
	function parseExperimentName(name) {
		const experimentTypes = Object.keys(experimentTypeMap);
		let parts = name.split('_');

		// Remove commit hash if present (6 hex characters)
		const firstPart = parts[0];
		const isCommitHash = /^[a-f0-9]{6}$/i.test(firstPart);
		if (isCommitHash) {
			parts.shift();
		}

		// Find matching experiment type
		for (const expType of experimentTypes) {
			const typeParts = expType.split('_');
			const testParts = parts.slice(0, typeParts.length).join('_');

			if (testParts === expType) {
				return {
					type: expType,
					remainder: parts.slice(typeParts.length).join('_')
				};
			}
		}

		// No match found
		return {
			type: parts[0],
			remainder: parts.slice(1).join('_')
		};
	}

	// Get unique experiments from artifacts_index.json
	const otherExperiments = $derived.by(() => {
		// Parse current experiment
		const currentParsed = parseExperimentName(data.experiment);

		// Extract unique experiment names from the artifacts index
		const experiments = new Set(artifactsIndex.map((item) => item.experiment));

		// Construct the expected fileName for the current feature
		const expectedFileName = `${data.content.feature.model_id}_${data.content.feature.layer}_${data.content.feature.index}`;

		// Filter to experiments with same remainder AND where this specific feature exists
		return Array.from(experiments).filter((exp) => {
			const expParsed = parseExperimentName(exp);

			// Check if remainders match
			if (expParsed.remainder !== currentParsed.remainder) {
				return false;
			}

			// Check if this specific feature exists in the artifacts index for this experiment
			const featureExists = artifactsIndex.some(
				(item) => item.experiment === exp && item.fileName === expectedFileName
			);

			return featureExists;
		});
	});

	// Helper to construct experiment link
	function getExperimentLink(experiment) {
		return `${base}/${experiment}/${data.content.feature.model_id}/${data.content.feature.layer}/${data.content.feature.index}`;
	}

	// Get available metrics from evaluation data
	const availableMetrics = $derived.by(() => {
		if (!data.content?.evaluation) return [];

		return Object.keys(data.content.evaluation).filter(
			(key) =>
				data.content.evaluation[key] &&
				typeof data.content.evaluation[key] === 'object' &&
				data.content.evaluation[key].value !== undefined
		);
	});

	// Initialize with first metric when data changes
	$effect(() => {
		if (availableMetrics.length > 0) {
			selectedMetric = availableMetrics[0];
		} else {
			selectedMetric = null;
		}
	});

	// Calculate global maximum activation across all examples
	const globalMaxActivation = $derived.by(() => {
		let max = 0;

		// Check data examples from description.data
		if (data.content?.description?.data?.positive) {
			for (const example of data.content.description.data.positive) {
				const exampleMax = Math.max(...example.activations);
				max = Math.max(max, exampleMax);
			}
		}
		if (data.content?.description?.data?.negative) {
			for (const example of data.content.description.data.negative) {
				const exampleMax = Math.max(...example.activations);
				max = Math.max(max, exampleMax);
			}
		}

		// Check evaluation data
		if (data.content?.evaluation?.clarity?.data?.positive) {
			for (const example of data.content.evaluation.clarity.data.positive) {
				const exampleMax = Math.max(...example.activations);
				max = Math.max(max, exampleMax);
			}
		}
		if (data.content?.evaluation?.clarity?.data?.negative) {
			for (const example of data.content.evaluation.clarity.data.negative) {
				const exampleMax = Math.max(...example.activations);
				max = Math.max(max, exampleMax);
			}
		}
		if (data.content?.evaluation?.responsiveness?.data?.positive) {
			for (const example of data.content.evaluation.responsiveness.data.positive) {
				const exampleMax = Math.max(...example.activations);
				max = Math.max(max, exampleMax);
			}
		}
		if (data.content?.evaluation?.responsiveness?.data?.negative) {
			for (const example of data.content.evaluation.responsiveness.data.negative) {
				const exampleMax = Math.max(...example.activations);
				max = Math.max(max, exampleMax);
			}
		}

		return max;
	});

	// Helper function to format JSON nicely
	function formatValue(value) {
		if (typeof value === 'object' && value !== null) {
			return JSON.stringify(value, null, 2);
		}
		return value;
	}

	// Derived values for header stats
	const headerStats = $derived.by(() => {
		const stats = [];

		// All evaluation metrics dynamically
		if (data.content?.evaluation) {
			availableMetrics.forEach((metricName) => {
				const metricData = data.content.evaluation[metricName];
				if (metricData?.value !== undefined) {
					stats.push({
						label: metricName.charAt(0).toUpperCase() + metricName.slice(1),
						value: `${(metricData.value * 100).toFixed(1)}%`,
						category: 'performance'
					});
				}
			});
		}

		return stats;
	});

	// Get all data examples for the main display
	const mainDataExamples = $derived.by(() => {
		const examples = [];

		// Add positive examples from description.data
		if (data.content?.description?.data?.positive) {
			examples.push(
				...data.content.description.data.positive.map((ex) => ({ ...ex, type: 'positive' }))
			);
		}

		// Add negative examples from description.data
		if (data.content?.description?.data?.negative) {
			examples.push(
				...data.content.description.data.negative.map((ex) => ({ ...ex, type: 'negative' }))
			);
		}

		return examples;
	});
</script>

<svelte:head>
	<title
		>{data.content.feature.model_id +
			'/' +
			data.content.feature.layer +
			'/' +
			data.content.feature.index || 'Not Found'} | Semantic Regex</title
	>
</svelte:head>

<svelte:window onscroll={handleScroll} />

<div class="min-h-screen bg-gray-50">
	<!-- Sticky Header Container -->
	<div
		class="sticky top-0 z-10 border-b border-gray-300 bg-gray-50 transition-shadow duration-200 {showShadow
			? 'shadow-sm'
			: ''}"
	>
		<div class="mx-auto max-w-6xl px-4 py-3 sm:py-4">
			<!-- Breadcrumbs -->
			<Breadcrumbs
				experiment={data.experiment}
				modelId={data.content.feature.model_id}
				layer={data.content.feature.layer}
				index={data.content.feature.index}
			/>
		</div>
	</div>

	<div class="mx-auto max-w-6xl px-4 py-4 sm:py-8">
		<div class="flex flex-col gap-4 sm:gap-6">
			<!-- Title Section -->
			<div class="border-b border-gray-200 py-3 sm:py-5">
				<!-- Experiment Switcher -->
				{#if otherExperiments.length > 0}
					<div class="flex flex-wrap gap-2 pb-3">
						{#each otherExperiments as experiment}
							{#if experiment === data.experiment}
								<span
									class="rounded-full border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 sm:px-3 sm:py-1.5 sm:text-sm"
								>
									{formatExperimentName(experiment, true)}
								</span>
							{:else}
								<a
									href={getExperimentLink(experiment)}
									class="rounded-full border border-gray-200 bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-400 transition-colors hover:border-gray-300 hover:bg-gray-50 hover:text-gray-500 sm:px-3 sm:py-1.5 sm:text-sm"
								>
									{formatExperimentName(experiment, true)}
								</a>
							{/if}
						{/each}
					</div>
				{/if}

				<div class="flex items-start justify-between">
					<div class="flex-1">
						<h1 class="mb-2 font-mono text-2xl font-bold text-gray-900 sm:mb-3 sm:text-3xl">
							{data.content.description?.description || 'No Description'}
						</h1>
						<div class="flex flex-wrap items-center gap-2 text-xs text-gray-600 sm:text-sm">
							<span class="break-all">{data.content.feature.model_id}</span>
							<span class="text-gray-400">•</span>
							<span>Layer {data.content.feature.layer}</span>
							<span class="text-gray-400">•</span>
							<span>Feature {data.content.feature.index}</span>
						</div>
					</div>
				</div>
			</div>

			<!-- Stats Section -->
			{#if headerStats.length > 0}
				<div class="">
					<div class="grid grid-cols-2 gap-2 sm:gap-3 md:grid-cols-3 lg:grid-cols-6">
						{#each headerStats as stat}
							<div
								class="rounded-md border border-gray-200 bg-white p-2.5 shadow-sm transition-colors sm:p-3"
							>
								<p class="text-xs font-medium uppercase tracking-wide text-gray-500">
									{stat.label}
								</p>
								<p class="mt-1 text-base font-semibold text-gray-900 sm:text-lg">
									{stat.value}
								</p>

								<!-- Visual indicator for metrics -->
								{#if stat.category === 'performance'}
									{@const numericValue = parseFloat(stat.value) / 100}
									{#if !isNaN(numericValue)}
										<div class="mt-2">
											<ProgressBar value={numericValue} min={0} max={1} />
										</div>
									{/if}
								{/if}
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Data Examples -->
			{#if mainDataExamples.length > 0}
				<div class="rounded-lg border border-gray-200 bg-white p-4 shadow-sm sm:p-6">
					<DataExamples
						examples={mainDataExamples}
						maxActivation={globalMaxActivation}
						paginate={true}
						itemsPerPage={10}
					/>
				</div>
			{/if}

			<!-- Metrics Section -->
			{#if headerStats.length > 0}
				<div class="flex min-h-[500px] flex-col gap-4 lg:flex-row lg:gap-6">
					<!-- Left Sidebar: Metrics Navigation - Horizontal on mobile, vertical on desktop -->
					<div class="w-full lg:w-80">
						<div class="rounded-lg border border-gray-200 bg-white p-4 shadow-sm sm:p-6">
							<h2
								class="mb-3 flex items-center text-lg font-semibold text-gray-900 sm:mb-4 sm:text-xl"
							>
								Metrics
								<span class="ml-2 text-xs font-normal text-gray-500 sm:text-sm">
									({availableMetrics.length} total)
								</span>
							</h2>
							<!-- Mobile: Horizontal scroll buttons -->
							<div class="space-y-2 lg:space-y-3">
								<div
									class="flex gap-2 overflow-x-auto pb-2 lg:flex-col lg:overflow-visible lg:pb-0"
								>
									{#each availableMetrics as metricName}
										<button
											class="flex-shrink-0 cursor-pointer rounded-md border p-2.5 text-left transition-all hover:border-gray-300 hover:bg-gray-50 lg:w-full lg:flex-shrink lg:p-3 {selectedMetric ===
											metricName
												? 'border-gray-400 bg-gray-50 shadow-sm'
												: 'border-gray-200'}"
											onclick={() => (selectedMetric = metricName)}
										>
											<div class="mb-1.5 flex items-center justify-between lg:mb-2">
												<span
													class="whitespace-nowrap text-xs font-medium text-gray-900 sm:text-sm"
												>
													{metricName.charAt(0).toUpperCase() + metricName.slice(1)}
												</span>
												<span class="ml-2 text-xs font-medium text-gray-600 sm:text-sm">
													{(data.content.evaluation[metricName].value * 100).toFixed(1)}%
												</span>
											</div>
											<div class="mt-1.5 lg:mt-2">
												<ProgressBar
													value={data.content.evaluation[metricName].value}
													min={0}
													max={1}
													height="h-1"
												/>
											</div>
										</button>
									{/each}
								</div>
							</div>
						</div>
					</div>

					<!-- Right Panel: Metric Details -->
					<div class="flex-1 rounded-lg border border-gray-200 bg-white p-4 shadow-sm sm:p-6">
						{#if selectedMetric}
							{@const metricData = data.content.evaluation[selectedMetric]}
							<div
								class="mb-3 flex flex-col gap-2 sm:mb-4 sm:flex-row sm:items-center sm:justify-between"
							>
								<h2 class="flex items-center text-lg font-semibold text-gray-900 sm:text-xl">
									{selectedMetric.charAt(0).toUpperCase() + selectedMetric.slice(1)}
									<span class="ml-2 text-xs font-normal text-gray-500 sm:text-sm">
										({(metricData.value * 100).toFixed(1)}%)
									</span>
								</h2>

								<!-- Toggle buttons -->
								{#if metricData.data?.positive?.length > 0 || metricData.data?.negative?.length > 0}
									<div class="flex rounded-md border border-gray-200 bg-gray-50 p-1">
										{#if metricData.data?.positive?.length > 0}
											<button
												class="flex-1 cursor-pointer rounded px-2 py-1 text-xs font-medium transition-all sm:flex-none {selectedMetricExampleType ===
												'positive'
													? 'bg-white text-gray-900 shadow-sm'
													: 'text-gray-600 hover:text-gray-800'}"
												onclick={() => (selectedMetricExampleType = 'positive')}
											>
												Positive ({metricData.data.positive.length})
											</button>
										{/if}
										{#if metricData.data?.negative?.length > 0}
											<button
												class="flex-1 cursor-pointer rounded px-2 py-1 text-xs font-medium transition-all sm:flex-none {selectedMetricExampleType ===
												'negative'
													? 'bg-white text-gray-900 shadow-sm'
													: 'text-gray-600 hover:text-gray-800'}"
												onclick={() => (selectedMetricExampleType = 'negative')}
											>
												Negative ({metricData.data.negative.length})
											</button>
										{/if}
									</div>
								{/if}
							</div>
							<hr class="mb-3 border-gray-200 sm:mb-4" />

							<!-- Examples for Selected Type -->
							<div class="space-y-4">
								{#if selectedMetricExampleType === 'positive' && metricData.data?.positive?.length > 0}
									<DataExamples
										examples={metricData.data.positive}
										title="Positive Examples"
										showControls={false}
										compact={true}
										maxActivation={globalMaxActivation}
										showMatchColumn={true}
										paginate={true}
									/>
								{:else if selectedMetricExampleType === 'negative' && metricData.data?.negative?.length > 0}
									<DataExamples
										examples={metricData.data.negative}
										title="Negative Examples"
										showControls={false}
										compact={true}
										maxActivation={globalMaxActivation}
										showMatchColumn="{true},"
										paginate={true}
									/>
								{:else}
									<div class="py-8 text-center text-sm text-gray-500">
										<p>No examples available for this metric</p>
									</div>
								{/if}
							</div>
						{:else}
							<div class="flex h-64 items-center justify-center text-sm text-gray-500">
								<p>Select a metric to view its details</p>
							</div>
						{/if}
					</div>
				</div>
			{:else}
				<div
					class="rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-500 shadow-sm sm:p-6"
				>
					No metrics available for this feature.
				</div>
			{/if}

			<!-- Parameters -->
			{#if data.content?.description?.parameters}
				<div class="rounded-lg border border-gray-200 bg-white p-4 shadow-sm sm:p-6">
					<h2 class="mb-3 flex items-center text-lg font-semibold text-gray-900 sm:mb-4 sm:text-xl">
						Parameters
					</h2>
					<div class="grid grid-cols-1 gap-3 sm:gap-4 md:grid-cols-2 lg:grid-cols-3">
						{#each Object.entries(data.content.description.parameters) as [key, value]}
							<div class="rounded-md border border-gray-100 bg-gray-50 p-3 sm:p-4">
								<div class="mb-1 text-xs font-medium text-gray-600 sm:text-sm">
									{key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
								</div>
								<div class="break-all font-mono text-xs text-gray-900 sm:text-sm">
									{formatValue(value)}
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>
