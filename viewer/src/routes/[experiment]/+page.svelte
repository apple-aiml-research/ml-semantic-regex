<!--
For licensing see accompanying LICENSE file.
Copyright (C) 2025 Apple Inc. All Rights Reserved.
-->

<script>
	import { base } from '$app/paths';
	import { getAllResults } from '$lib/utils/loadResults.js';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Breadcrumbs from '$lib/components/Breadcrumbs.svelte';
	import { formatExperimentName, getExperimentType } from '$lib/utils/formatExperimentName';

	let { data } = $props();

	// State for scroll shadow
	let showShadow = $state(false);

	// Filter state
	let activeFilters = $state(new Set());

	// Infinite scroll state
	let displayLimit = $state(100);
	let scrollContainer = $state(null);
	const LOAD_MORE_INCREMENT = 100;

	// Check if this is a semantic regex experiment
	const isSemanticRegex = $derived(getExperimentType(data.experiment) === 'semantic_regex');

	// Available filter options
	const filterOptions = ['symbol', 'lexeme', 'field', '@', '|', '?', 'combination'];

	// Get all results for this experiment
	const experimentResults = $derived(
		getAllResults().filter((result) => result.experiment === data.experiment)
	);

	// Filter results based on active filters
	const filteredResults = $derived.by(() => {
		if (activeFilters.size === 0) return experimentResults;

		return experimentResults.filter((result) => {
			const description = result.content?.description?.description;
			if (!description) return false;

			return Array.from(activeFilters).every((filter) => {
				// Special handling for combination filter
				if (filter === 'combination') {
					// Check if there are 2 or more '[' characters
					const matches = description.match(/\[/g);
					return matches && matches.length >= 2;
				}

				// Standard case-insensitive search for other filters
				return description.toLowerCase().includes(filter.toLowerCase());
			});
		});
	});

	// Limit displayed results for performance
	const displayedResults = $derived(filteredResults.slice(0, displayLimit));
	const hasMoreResults = $derived(displayLimit < filteredResults.length);

	// Infinite scroll handler
	function handleScroll() {
		showShadow = window.scrollY > 0;

		// Check if near bottom of page
		const scrollHeight = document.documentElement.scrollHeight;
		const scrollTop = window.scrollY;
		const clientHeight = window.innerHeight;

		// Load more when within 500px of bottom
		if (scrollHeight - (scrollTop + clientHeight) < 500 && hasMoreResults) {
			displayLimit += LOAD_MORE_INCREMENT;
		}
	}

	// Toggle filter function
	function toggleFilter(filter) {
		if (!isSemanticRegex) return; // Don't allow toggling if not semantic regex

		if (activeFilters.has(filter)) {
			activeFilters.delete(filter);
		} else {
			activeFilters.add(filter);
		}
		activeFilters = new Set(activeFilters); // Trigger reactivity
		// Reset display limit when filters change
		displayLimit = 100;
	}
	// Simple derived values without complex logic (updated to use displayed results)
	const allModels = $derived.by(() => {
		const models = new Map();
		displayedResults.forEach((result) => {
			if (!result.content?.feature) return;
			const { model_id, layer, index } = result.content.feature;
			if (!models.has(model_id)) {
				models.set(model_id, new Map());
			}

			const modelMap = models.get(model_id);
			if (!modelMap.has(layer)) {
				modelMap.set(layer, []);
			}

			modelMap.get(layer).push(result);
		});

		// Sort results within each layer by index for consistent ordering
		models.forEach((modelMap) => {
			modelMap.forEach((layerResults) => {
				layerResults.sort((a, b) => a.content.feature.index - b.content.feature.index);
			});
		});

		return models;
	});

	// Helper function to get route to specific feature
	function getFeatureRoute(result) {
		const { model_id, layer, index } = result.content.feature;
		return `${base}/${data.experiment}/${model_id}/${layer}/${index}`;
	}

	// Helper function to truncate long regex patterns
	function truncateRegex(regex, maxLength = 80) {
		if (!regex || regex.length <= maxLength) return regex;
		return regex.substring(0, maxLength) + '...';
	}

	// Helper function to highlight filtered terms in regex
	function highlightFilteredTerms(description) {
		if (!description || activeFilters.size === 0) return description;

		let highlighted = description;
		Array.from(activeFilters).forEach((filter) => {
			const escapedFilter = filter.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
			const regexPattern = new RegExp(`(${escapedFilter})`, 'gi');
			highlighted = highlighted.replace(
				regexPattern,
				'<mark class="bg-yellow-200 px-1 rounded">$1</mark>'
			);
		});

		return highlighted;
	}
</script>

<svelte:head>
	<title>{formatExperimentName(data.experiment) || 'Not Found'} | Semantic Regex</title>
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
			<Breadcrumbs experiment={data.experiment} />
		</div>
	</div>

	<div class="mx-auto max-w-6xl px-4 py-4 sm:py-8">
		<!-- Header -->

		<div class="mb-6 sm:mb-8">
			<h1 class="mb-2 text-2xl font-bold text-gray-900 sm:text-3xl">
				{formatExperimentName(data.experiment)}
			</h1>
			<p class="text-sm text-gray-600 sm:text-base">
				{filteredResults.length.toLocaleString('en-US')} features across {allModels.size}
				{allModels.size === 1 ? 'model' : 'models'}
				{#if activeFilters.size > 0}
					<span class="text-xs text-gray-500 sm:text-sm">
						(filtered from {experimentResults.length.toLocaleString('en-US')} total)
					</span>
				{/if}
				{#if hasMoreResults}
					<span class="text-xs text-gray-500 sm:text-sm">
						(showing first {displayedResults.length.toLocaleString('en-US')})
					</span>
				{/if}
			</p>

			<!-- Filters -->
			<div class="mt-4 flex flex-wrap gap-2">
				<span
					class="flex items-center text-xs font-medium transition-colors sm:text-sm {isSemanticRegex
						? 'text-gray-700'
						: 'text-gray-400 opacity-60'}"
					><Icon
						icon="filter"
						style="mr-2 {isSemanticRegex ? 'text-gray-700' : 'text-gray-400 opacity-60'}"
					/> Filter:</span
				>
				{#each filterOptions as filter}
					<button
						onclick={() => toggleFilter(filter)}
						disabled={!isSemanticRegex}
						class="rounded-full px-2.5 py-1 text-xs font-medium transition-colors sm:px-3 sm:text-sm
							{isSemanticRegex
							? activeFilters.has(filter)
								? 'cursor-pointer border border-blue-100 bg-blue-100 text-blue-800 hover:bg-blue-100'
								: 'cursor-pointer border border-gray-300 bg-white text-gray-700 hover:bg-gray-100'
							: 'cursor-not-allowed border border-gray-50 bg-gray-100 text-gray-400 opacity-60'}"
					>
						{filter}
					</button>
				{/each}
				{#if activeFilters.size > 0}
					<button
						onclick={() => {
							activeFilters.clear();
							activeFilters = new Set();
							displayLimit = 100;
						}}
						class="ml-2 flex cursor-pointer items-center rounded-full bg-red-100 px-2.5 py-1 text-xs font-medium text-red-500 hover:bg-gray-200 sm:px-3 sm:text-sm"
					>
						<Icon icon="xmark" style="text-red-500 mr-0.5" height="h-3" width="h-3" />
						<span>Clear</span>
					</button>
				{/if}
			</div>
		</div>

		<!-- Results by Model and Layer -->
		{#if allModels.size > 0}
			<div class="space-y-6 sm:space-y-8">
				{#each Array.from(allModels.entries()) as [modelId, layers]}
					<div class="rounded-lg border border-gray-200 bg-white">
						<div class="border-b border-gray-200 bg-gray-50 px-4 py-3 sm:px-6 sm:py-4">
							<h2 class="text-lg font-semibold text-gray-900 sm:text-xl">{modelId}</h2>
							<p class="text-xs text-gray-600 sm:text-sm">
								{layers.size}
								{layers.size === 1 ? 'layer' : 'layers'}
							</p>
						</div>

						<div class="divide-y divide-gray-200">
							{#each Array.from(layers.entries()) as [layer, layerResults]}
								<div class="p-4 sm:p-6">
									<div class="mb-3 flex items-center justify-between sm:mb-4">
										<h3 class="text-base font-medium text-gray-900 sm:text-lg">Layer {layer}</h3>
										<span class="text-xs text-gray-500 sm:text-sm">
											{layerResults.length.toLocaleString('en-US')}
											{layerResults.length === 1 ? 'feature' : 'features'}
										</span>
									</div>

									<!-- Table Headers - Hidden on mobile -->
									<div class="mb-2 hidden items-center border-b border-gray-200 px-4 pb-2 lg:flex">
										<div class="w-16 text-xs font-semibold uppercase tracking-wider text-gray-600">
											Index
										</div>
										<div
											class="flex-1 text-xs font-semibold uppercase tracking-wider text-gray-600"
										>
											Description
										</div>
										<div
											class="flex items-center space-x-4 text-xs font-semibold uppercase tracking-wider text-gray-600"
										>
											<div class="flex w-[50px] flex-col items-center">
												<span class="mb-1">Clarity</span>
											</div>
											<div class="flex w-[50px] flex-col items-center">
												<span class="mb-1">Resp.</span>
											</div>
											<div class="flex w-[50px] flex-col items-center">
												<span class="mb-1">Purity</span>
											</div>
											<div class="flex w-[50px] flex-col items-center">
												<span class="mb-1">Detect</span>
											</div>
											<div class="flex w-[50px] flex-col items-center">
												<span class="mb-1">Fuzzing</span>
											</div>
											<div class="flex w-[50px] flex-col items-center">
												<span class="mb-1">Faithful</span>
											</div>
										</div>
										<div class="ml-4 w-4"></div>
									</div>

									<!-- Feature List -->
									<div class="divide-y divide-gray-200">
										{#each layerResults as result}
											{@const feature = result.content.feature}
											{@const description = result.content.description}
											{@const evaluation = result.content.evaluation}
											<div class="group relative">
												<a
													href={getFeatureRoute(result)}
													class="block px-3 py-3 transition-all duration-150 hover:bg-gray-50 lg:px-4 lg:py-1.5 lg:hover:bg-gray-100"
												>
													<!-- Mobile Layout (simple, no metrics) -->
													<div class="lg:hidden">
														<div class="flex justify-between gap-3">
															<div class="min-w-0 flex-1">
																<div class="mb-1 font-mono text-sm font-medium text-gray-500">
																	Index {feature.index}
																</div>
																{#if description?.description}
																	<code
																		class="block break-words rounded bg-gray-100 px-2 py-1 text-xs text-gray-700"
																	>
																		{@html highlightFilteredTerms(description.description)}
																	</code>
																{/if}
															</div>
															<Icon color="text-gray-400" icon="chevron-right"/>
														</div>
													</div>

													<!-- Desktop Table Layout -->
													<div class="hidden lg:flex lg:items-center">
														<div class="w-16 font-mono text-sm font-medium text-gray-500">
															{feature.index}
														</div>
														<div class="flex-1">
															{#if description?.description}
																<code
																	class="inline-block max-w-md overflow-hidden text-ellipsis whitespace-nowrap rounded bg-gray-100 px-2 py-1 text-sm text-gray-700"
																>
																	{@html highlightFilteredTerms(
																		truncateRegex(description.description)
																	)}
																</code>
															{/if}
														</div>
														<div class="flex items-center space-x-4 text-xs text-gray-500">
															<!-- Clarity -->
															<div class="flex w-[50px] flex-col items-center">
																{#if evaluation?.clarity?.value !== undefined}
																	<span class="mb-1"
																		>{(evaluation.clarity.value * 100).toFixed(0)}%</span
																	>
																	<ProgressBar
																		value={evaluation.clarity.value}
																		min={0}
																		max={1}
																		height="h-1"
																		width="w-[40px]"
																	/>
																{:else}
																	<span class="text-gray-300">-</span>
																{/if}
															</div>

															<!-- Responsiveness -->
															<div class="flex w-[50px] flex-col items-center">
																{#if evaluation?.responsiveness?.value !== undefined}
																	<span class="mb-1"
																		>{(evaluation.responsiveness.value * 100).toFixed(0)}%</span
																	>
																	<ProgressBar
																		value={evaluation.responsiveness.value}
																		min={0}
																		max={1}
																		height="h-1"
																		width="w-[40px]"
																	/>
																{:else}
																	<span class="text-gray-300">-</span>
																{/if}
															</div>

															<!-- Purity -->
															<div class="flex w-[50px] flex-col items-center">
																{#if evaluation?.purity?.value !== undefined}
																	<span class="mb-1"
																		>{(evaluation.purity.value * 100).toFixed(0)}%</span
																	>
																	<ProgressBar
																		value={evaluation.purity.value}
																		min={0}
																		max={1}
																		height="h-1"
																		width="w-[40px]"
																	/>
																{:else}
																	<span class="text-gray-300">-</span>
																{/if}
															</div>

															<!-- Detection -->
															<div class="flex w-[50px] flex-col items-center">
																{#if evaluation?.detection?.value !== undefined}
																	<span class="mb-1"
																		>{(evaluation.detection.value * 100).toFixed(0)}%</span
																	>
																	<ProgressBar
																		value={evaluation.detection.value}
																		min={0}
																		max={1}
																		height="h-1"
																		width="w-[40px]"
																	/>
																{:else}
																	<span class="text-gray-300">-</span>
																{/if}
															</div>

															<!-- Fuzzing -->
															<div class="flex w-[50px] flex-col items-center">
																{#if evaluation?.fuzzing?.value !== undefined}
																	<span class="mb-1"
																		>{(evaluation.fuzzing.value * 100).toFixed(0)}%</span
																	>
																	<ProgressBar
																		value={evaluation.fuzzing.value}
																		min={0}
																		max={1}
																		height="h-1"
																		width="w-[40px]"
																	/>
																{:else}
																	<span class="text-gray-300">-</span>
																{/if}
															</div>

															<!-- Faithfulness -->
															<div class="flex w-[50px] flex-col items-center">
																{#if evaluation?.faithfulness?.value !== undefined}
																	<span class="mb-1"
																		>{(evaluation.faithfulness.value * 100).toFixed(0)}%</span
																	>
																	<ProgressBar
																		value={evaluation.faithfulness.value}
																		min={0}
																		max={1}
																		height="h-1"
																		width="w-[40px]"
																	/>
																{:else}
																	<span class="text-gray-300">-</span>
																{/if}
															</div>
														</div>
														<div class="pl-3">
															<Icon color="text-gray-400" icon="chevron-right" width="w-[0.5em]"/>
														</div>
													</div>
												</a>
											</div>
										{/each}
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/each}
			</div>

			<!-- Add loading indicator -->
			{#if hasMoreResults && displayedResults.length > 0}
				<div class="mt-8 flex justify-center">
					<div class="text-sm text-gray-500">Loading more results...</div>
				</div>
			{/if}
		{:else}
			<div class="rounded-lg border border-gray-200 bg-white p-12 text-center">
				<h3 class="mt-2 text-sm font-medium text-gray-900">No results found</h3>
				<p class="mt-1 text-sm text-gray-500">
					No features found for the experiment "{data.experiment}".
				</p>
			</div>
		{/if}
	</div>
</div>
