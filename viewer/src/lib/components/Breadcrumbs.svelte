<!--
For licensing see accompanying LICENSE file.
Copyright (C) 2025 Apple Inc. All Rights Reserved.
-->

<script>
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import IconButton from './IconButton.svelte';
	import Icon from './Icon.svelte';
	import {
		getAvailableExperiments,
		getAvailableModels,
		getAvailableLayersForModel,
		getAvailableIndicesForModelLayer,
		getRandomFeatureFromExperiment
	} from '$lib/utils/loadResults.js';
	import { formatExperimentName } from '$lib/utils/formatExperimentName';

	let { experiment, modelId = null, layer = null, index = null } = $props();

	// Dropdown states
	let showExperimentDropdown = $state(false);
	let showModelDropdown = $state(false);
	let showLayerDropdown = $state(false);
	let showIndexDropdown = $state(false);

	// Get available options for dropdowns
	let availableExperiments = $derived(getAvailableExperiments());
	let availableModels = $derived(getAvailableModels(experiment));
	let availableLayers = $derived(modelId ? getAvailableLayersForModel(modelId, experiment) : []);
	let availableIndices = $derived(
		modelId && layer ? getAvailableIndicesForModelLayer(modelId, layer, experiment) : []
	);

	// Navigation functions
	function navigateToExperiment(experiment) {
		// Always go to experiment page, don't try to find a specific feature
		goto(`${base}/${experiment}/`);
		showExperimentDropdown = false;
	}

	function navigateToModel(modelId) {
		const layers = getAvailableLayersForModel(modelId, experiment);
		if (layers.length > 0) {
			const indices = getAvailableIndicesForModelLayer(modelId, layers[0], experiment);
			if (indices.length > 0) {
				goto(`${base}/${experiment}/${modelId}/${layers[0]}/${indices[0]}`);
			}
		}
		showModelDropdown = false;
	}

	function navigateToLayer(layer) {
		const indices = getAvailableIndicesForModelLayer(modelId, layer, experiment);
		if (indices.length > 0) {
			goto(`${base}/${experiment}/${modelId}/${layer}/${indices[0]}`);
		}
		showLayerDropdown = false;
	}

	function navigateToIndex(index) {
		goto(`${base}/${experiment}/${modelId}/${layer}/${index}`);
		showIndexDropdown = false;
	}

	function navigateToRandomFeature() {
		const randomFeature = getRandomFeatureFromExperiment(experiment);
		if (randomFeature) {
			goto(
				`${base}/${experiment}/${randomFeature.model}/${randomFeature.layer}/${randomFeature.index}`
			);
		}
	}

	function navigateToNextFeature() {
		if (!modelId || !layer || index === null) return;

		const currentIndex = index;
		const indices = getAvailableIndicesForModelLayer(modelId, layer, experiment);
		const nextIndex = indices.find((i) => i > currentIndex);
		if (nextIndex) {
			goto(`${base}/${experiment}/${modelId}/${layer}/${nextIndex}`);
		}
	}

	function navigateToPreviousFeature() {
		if (!modelId || !layer || index === null) return;

		const currentIndex = index;
		const indices = getAvailableIndicesForModelLayer(modelId, layer, experiment);
		const previousIndex = indices
			.slice()
			.reverse()
			.find((i) => i < currentIndex);
		if (previousIndex) {
			goto(`${base}/${experiment}/${modelId}/${layer}/${previousIndex}`);
		}
	}

	function navigateToExperimentList() {
		goto(`${base}/${experiment}/`);
	}

	function hasNextFeature() {
		if (!modelId || !layer || index === null) return false;

		const currentIndex = index;
		const indices = getAvailableIndicesForModelLayer(modelId, layer, experiment);
		return indices.some((i) => i > currentIndex);
	}

	function hasPreviousFeature() {
		if (!modelId || !layer || index === null) return false;

		const currentIndex = index;
		const indices = getAvailableIndicesForModelLayer(modelId, layer, experiment);
		return indices.some((i) => i < currentIndex);
	}

	// Close dropdowns when clicking outside
	function handleClickOutside(event) {
		if (!event.target.closest('.dropdown-container')) {
			showExperimentDropdown = false;
			showModelDropdown = false;
			showLayerDropdown = false;
			showIndexDropdown = false;
		}
	}

	// Handle touch events for mobile
	function handleTouchOutside(event) {
		handleClickOutside(event);
	}
</script>

<svelte:window onclick={handleClickOutside} ontouchstart={handleTouchOutside} />

<div class="flex items-center justify-between">
	<!-- Scrollable breadcrumbs container on mobile -->
	<nav
		class="scrollbar-hide flex min-w-0 flex-1 items-center space-x-1 overflow-x-auto text-xs sm:text-sm md:overflow-visible"
	>
		<a href="{base}/" class="cursor-pointer whitespace-nowrap text-gray-500 hover:text-gray-800"
			>Home</a
		>
		<span class="flex-shrink-0 px-1 text-gray-400">/</span>

		<!-- Experiment Dropdown -->
		<div class="dropdown-container relative flex-shrink-0">
			<button
				onclick={(e) => {
					e.stopPropagation();
					showExperimentDropdown = !showExperimentDropdown;
				}}
				class="flex min-h-[36px] cursor-pointer items-center whitespace-nowrap py-1.5 text-gray-500 transition-all hover:text-gray-800 sm:min-h-0 sm:py-2"
			>
				<div>{formatExperimentName(experiment, true)}</div>
				<div class="ml-1"><Icon color="text-gray-500" icon="chevron-down" width="w-[0.75em]"/></div>
			</button>
			{#if showExperimentDropdown}
				<div
					class="fixed left-4 right-4 top-16 z-50 max-h-[60vh] overflow-y-auto rounded-md border border-gray-200 bg-white shadow-lg sm:absolute sm:left-0 sm:right-auto sm:top-full sm:mt-1 sm:max-h-80 sm:w-max"
				>
					<div
						class="sticky top-0 border-b border-gray-200 bg-gray-50 px-3 py-2 text-xs font-medium text-gray-500"
					>
						Experiment
					</div>
					<div class="max-h-[calc(60vh-2rem)] overflow-y-auto sm:max-h-80">
						{#each availableExperiments as exp}
							<button
								onclick={() => navigateToExperiment(exp)}
								class="block w-full px-3 py-2.5 text-left text-sm transition-colors hover:bg-gray-100"
								class:bg-blue-50={exp === experiment}
								class:text-blue-700={exp === experiment}
							>
								{formatExperimentName(exp)}
							</button>
						{/each}
					</div>
				</div>
			{/if}
		</div>

		<!-- Only show model dropdown if modelId is provided -->
		{#if modelId}
			<span class="flex-shrink-0 px-1 text-gray-400">/</span>

			<!-- Model Dropdown -->
			<div class="dropdown-container relative flex-shrink-0">
				<button
					onclick={(e) => {
						e.stopPropagation();
						showModelDropdown = !showModelDropdown;
					}}
					class="flex min-h-[36px] cursor-pointer items-center whitespace-nowrap py-1.5 text-gray-500 transition-all hover:text-gray-800 sm:min-h-0 sm:py-2"
				>
					<div>{modelId}</div>
					<div class="ml-1"><Icon color="text-gray-500" icon="chevron-down" width="w-[0.75em]"/></div>
				</button>
				{#if showModelDropdown}
					<div
						class="fixed left-4 right-4 top-16 z-50 max-h-[60vh] overflow-y-auto rounded-md border border-gray-200 bg-white shadow-lg sm:absolute sm:left-0 sm:right-auto sm:top-full sm:mt-1 sm:max-h-80 sm:w-max"
					>
						<div
							class="sticky top-0 border-b border-gray-200 bg-gray-50 px-3 py-2 text-xs font-medium text-gray-500"
						>
							Model
						</div>
						<div class="max-h-[calc(60vh-2rem)] overflow-y-auto sm:max-h-80">
							{#each availableModels as model}
								<button
									onclick={() => navigateToModel(model)}
									class="block w-full px-3 py-2.5 text-left text-sm transition-colors hover:bg-gray-100"
									class:bg-blue-50={model === modelId}
									class:text-blue-700={model === modelId}
								>
									{model}
								</button>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Only show layer dropdown if layer is provided -->
		{#if layer}
			<div class="flex-shrink-0 px-1 text-gray-400">/</div>

			<!-- Layer Dropdown -->
			<div class="dropdown-container relative flex-shrink-0">
				<button
					onclick={(e) => {
						e.stopPropagation();
						showLayerDropdown = !showLayerDropdown;
					}}
					class="flex min-h-[36px] cursor-pointer items-center whitespace-nowrap py-1.5 text-gray-500 transition-all hover:text-gray-800 sm:min-h-0 sm:py-2"
				>
					<div>{layer}</div>
					<div class="ml-1"><Icon color="text-gray-500" icon="chevron-down" width="w-[0.75em]"/></div>
				</button>
				{#if showLayerDropdown}
					<div
						class="fixed left-4 right-4 top-16 z-50 max-h-[60vh] overflow-y-auto rounded-md border border-gray-200 bg-white shadow-lg sm:absolute sm:left-0 sm:right-auto sm:top-full sm:mt-1 sm:max-h-80 sm:w-max"
					>
						<div
							class="sticky top-0 border-b border-gray-200 bg-gray-50 px-3 py-2 text-xs font-medium text-gray-500"
						>
							Layer
						</div>
						<div class="max-h-[calc(60vh-2rem)] overflow-y-auto sm:max-h-80">
							{#each availableLayers as lay}
								<button
									onclick={() => navigateToLayer(lay)}
									class="block w-full px-3 py-2.5 text-left text-sm transition-colors hover:bg-gray-100"
									class:bg-blue-50={lay === layer}
									class:text-blue-700={lay === layer}
								>
									{lay}
								</button>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Only show index dropdown if index is provided -->
		{#if index !== null}
			<span class="flex-shrink-0 px-1 text-gray-400">/</span>

			<!-- Index Dropdown -->
			<div class="dropdown-container relative flex-shrink-0">
				<button
					onclick={(e) => {
						e.stopPropagation();
						showIndexDropdown = !showIndexDropdown;
					}}
					class="flex min-h-[36px] cursor-pointer items-center whitespace-nowrap py-1.5 text-gray-500 transition-all hover:text-gray-800 sm:min-h-0 sm:py-2"
				>
					<div>{index}</div>
					<div class="ml-1"><Icon color="text-gray-500" icon="chevron-down" width="w-[0.75em]"/></div>
				</button>
				{#if showIndexDropdown}
					<div
						class="fixed left-4 right-4 top-16 z-50 max-h-[60vh] overflow-y-auto rounded-md border border-gray-200 bg-white shadow-lg sm:absolute sm:left-0 sm:right-auto sm:top-full sm:mt-1 sm:max-h-80 sm:w-max"
					>
						<div
							class="sticky top-0 border-b border-gray-200 bg-gray-50 px-3 py-2 text-xs font-medium text-gray-500"
						>
							Feature
						</div>
						<div class="max-h-[calc(60vh-2rem)] overflow-y-auto sm:max-h-80">
							{#each availableIndices as idx}
								<button
									onclick={() => navigateToIndex(idx)}
									class="block w-full px-3 py-2.5 text-left text-sm transition-colors hover:bg-gray-100"
									class:bg-blue-50={idx === index}
									class:text-blue-700={idx === index}
								>
									{idx}
								</button>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</nav>

	<div class="flex flex-shrink-0 space-x-1.5 border-l border-gray-300 pl-2 md:border-none md:pl-0">
		<!-- Experiment List Button -->
		<IconButton icon="list" onclick={navigateToExperimentList} title="Experiment list" />

		<!-- Only show navigation buttons if we have model, layer, and index -->
		{#if modelId && layer && index !== null}
			<!-- Previous and Next Feature Buttons -->
			<IconButton
				icon="arrow-left"
				onclick={navigateToPreviousFeature}
				disabled={!hasPreviousFeature()}
				title="Previous feature"
			/>

			<IconButton
				icon="arrow-right"
				onclick={navigateToNextFeature}
				disabled={!hasNextFeature()}
				title="Next feature"
			/>
		{/if}

		<!-- Randomize Button (always show if we have an experiment) -->
		<IconButton icon="shuffle" onclick={navigateToRandomFeature} title="Random feature" />
	</div>
</div>

<style>
	/* Hide scrollbar but keep functionality */
	.scrollbar-hide {
		-ms-overflow-style: none;
		scrollbar-width: none;
	}
	.scrollbar-hide::-webkit-scrollbar {
		display: none;
	}
</style>
