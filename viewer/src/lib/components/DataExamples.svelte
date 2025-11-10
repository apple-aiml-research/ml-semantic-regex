<!--
For licensing see accompanying LICENSE file.
Copyright (C) 2025 Apple Inc. All Rights Reserved.
-->

<script>
	import Icon from './Icon.svelte';
	import IconButton from './IconButton.svelte';

	let {
		examples,
		title = 'Data Examples',
		showControls = true,
		compact = false,
		showTitle = true,
		maxActivation = null,
		showMatchColumn = false,
		paginate = false,
		itemsPerPage = 5
	} = $props();

	// Pagination state
	let currentPage = $state(0);

	// Calculate paginated examples
	const paginatedExamples = $derived.by(() => {
		if (!paginate || !examples) return examples;

		const start = currentPage * itemsPerPage;
		const end = start + itemsPerPage;
		return examples.slice(start, end);
	});

	const totalPages = $derived(paginate && examples ? Math.ceil(examples.length / itemsPerPage) : 1);

	// Reset to first page when examples change
	$effect(() => {
		if (examples) {
			currentPage = 0;
		}
	});

	function goToNextPage() {
		if (currentPage < totalPages - 1) {
			currentPage++;
		}
	}

	function goToPreviousPage() {
		if (currentPage > 0) {
			currentPage--;
		}
	}

	// Calculate max activation - use provided value or calculate locally as fallback
	const effectiveMaxActivation = $derived.by(() => {
		if (maxActivation !== null) {
			return maxActivation;
		}

		// Fallback to local calculation if no global max provided
		let max = 0;
		if (examples) {
			for (const example of examples) {
				const exampleMax = Math.max(...example.activations);
				max = Math.max(max, exampleMax);
			}
		}
		return max;
	});

	// Calculate local max for comparison
	const localMaxActivation = $derived.by(() => {
		let max = 0;
		if (examples) {
			for (const example of examples) {
				const exampleMax = Math.max(...example.activations);
				max = Math.max(max, exampleMax);
			}
		}
		return max;
	});

	// Generate colorbar gradient stops
	const colorbarGradient = $derived.by(() => {
		const stops = [];
		for (let i = 0; i <= 100; i += 5) {
			const intensity = i / 100;
			const activation = intensity * effectiveMaxActivation;
			const color = getActivationColor(activation, effectiveMaxActivation);
			stops.push(`${color} ${i}%`);
		}
		return `linear-gradient(to right, ${stops.join(', ')})`;
	});

	// Generate tick values for the colorbar
	const colorbarTicks = $derived.by(() => {
		const ticks = [];
		const numTicks = 3;
		for (let i = 0; i < numTicks; i++) {
			const ratio = i / (numTicks - 1);
			const value = ratio * effectiveMaxActivation;
			const position = ratio * 100;
			ticks.push({ value, position });
		}
		return ticks;
	});

	// Toggle states
	let showActivations = $state(true);
	let showHighlighting = $state(true);
	let centerAlign = $state(false);

	// Store references to token elements for width calculation
	let tokenElements = $state({});

	// Function to find the index of the token with maximum activation
	function getMaxActivationIndex(activations) {
		let maxIndex = 0;
		let maxValue = activations[0];
		for (let i = 1; i < activations.length; i++) {
			if (activations[i] > maxValue) {
				maxValue = activations[i];
				maxIndex = i;
			}
		}
		return maxIndex;
	}

	// Color interpolation function for activation values
	function getActivationColor(activation, maxActivation) {
		if (activation <= 0) return 'rgb(243, 244, 246)'; // gray-100 for zero/negative

		// Normalize activation to 0-1 range
		const intensity = Math.min(activation / maxActivation, 1);

		// Interpolate from light blue to dark blue
		const r = Math.round(239 - (239 - 59) * intensity); // 239 (light) to 59 (dark)
		const g = Math.round(246 - (246 - 130) * intensity); // 246 (light) to 130 (dark)
		const b = Math.round(255 - (255 - 246) * intensity); // 255 (light) to 246 (dark)

		return `rgb(${r}, ${g}, ${b})`;
	}

	// Get text color based on background intensity
	function getTextColor(activation, maxActivation) {
		if (activation <= 0) return 'rgb(55, 65, 81)'; // gray-700

		const intensity = Math.min(activation / maxActivation, 1);
		return intensity > 0.5 ? 'rgb(255, 255, 255)' : 'rgb(30, 58, 138)'; // white for dark bg, blue-900 for light bg
	}

	// Format token display
	function formatToken(token) {
		return (
			token
				.replace(/\u2581/g, '_')
				.replace(/\n/g, '\\n')
				.replace(/\t/g, '\\t')
				.replace(/\r/g, '\\r') || '·'
		);
	}
</script>

<div class="space-y-4">
	{#if showTitle || showControls}
		<div class="flex flex-col justify-between gap-2 sm:flex-row">
			{#if showTitle}
				<h2
					class="flex items-center {compact
						? 'text-xs font-medium text-gray-700 sm:text-sm'
						: 'text-lg font-semibold text-gray-900 sm:text-xl'}"
				>
					{title}
					<span class="ml-2 text-xs font-normal text-gray-500 sm:text-sm">
						({examples?.length ? `${examples.length}` : ''} total)
					</span>
				</h2>
				{#if showMatchColumn && examples?.some((ex) => ex.match !== undefined)}
					<h2
						class="flex items-center {compact
							? 'text-xs font-medium text-gray-700 sm:text-sm'
							: 'text-lg font-semibold text-gray-900 sm:text-xl'}"
					>
						Matched
					</h2>
				{/if}
			{/if}

			{#if showControls}
				<!-- Toggle Buttons -->
				<div class="flex items-center space-x-1.5">
					<!-- Colorbar Legend -->
					{#if showHighlighting}
						<div class="flex flex-col items-center pl-4 pr-2 sm:pr-4">
							<div class="flex flex-col">
								<!-- Gradient bar -->
								<div
									class="h-1.5 w-24 rounded-sm sm:w-32"
									style="background: {colorbarGradient};"
								></div>
								<!-- Tick marks and labels -->
								<div class="relative mt-1 h-3 w-24 sm:w-32">
									{#each colorbarTicks as tick}
										<div
											class="absolute flex flex-col items-center"
											style="left: {tick.position}%; transform: translateX(-50%);"
										>
											<!-- Tick mark -->
											<div class="h-1 w-px bg-gray-400"></div>
											<!-- Label -->
											<span class="mt-0.5 font-mono text-[8px] text-gray-500 sm:text-[9px]">
												{tick.value.toFixed(tick.value < 1 ? 2 : 1)}
											</span>
										</div>
									{/each}
								</div>
							</div>
						</div>
					{/if}

					<IconButton
						icon="paint-brush"
						onclick={() => (showHighlighting = !showHighlighting)}
						active={showHighlighting}
						title="Toggle highlighting"
					/>

					<IconButton
						icon="hashtag"
						onclick={() => (showActivations = !showActivations)}
						active={showActivations}
						title="Toggle activation values"
					/>

					<IconButton
						icon={centerAlign ? 'align-center' : 'align-left'}
						onclick={() => (centerAlign = !centerAlign)}
						active={centerAlign}
						title="Toggle alignment"
					/>
				</div>
			{/if}
		</div>
	{/if}

	{#if examples && examples.length > 0}
		<div class="overflow-y-auto">
			{#each paginatedExamples as example, i}
				{@const maxActivationIndex = getMaxActivationIndex(example.activations)}
				{@const actualIndex = paginate ? currentPage * itemsPerPage + i : i}
				<div
					class="flex items-start gap-2 py-2 sm:gap-3 sm:py-3"
					class:border-t={i > 0}
					class:border-gray-200={i > 0}
				>
					<div
						class="mt-1 flex-shrink-0 {compact
							? 'text-[10px] sm:text-xs'
							: 'text-xs sm:text-sm'} font-medium text-gray-500"
					>
						E{actualIndex + 1}:
					</div>

					{#if centerAlign}
						<!-- Three-column layout: left tokens | max token | right tokens -->
						<div class="flex flex-1 gap-0.5 overflow-x-auto">
							<!-- Left tokens (before max) - right aligned -->
							<div class="flex min-w-0 flex-1 flex-wrap justify-end gap-0.5">
								{#each example.tokens.slice(0, maxActivationIndex) as token, j}
									<div class="flex flex-col items-center">
										<span
											class="flex items-center rounded px-1 py-0.5 font-mono transition-all duration-200 sm:px-1.5 {compact
												? 'min-h-[1.25rem] text-[10px] sm:text-xs'
												: 'min-h-[1.5rem] text-xs sm:text-sm'}"
											style={showHighlighting
												? `background-color: ${getActivationColor(example.activations[j], effectiveMaxActivation)}; color: ${getTextColor(example.activations[j], effectiveMaxActivation)};`
												: 'background-color: rgb(243, 244, 246); color: rgb(55, 65, 81);'}
											class:font-medium={showHighlighting && example.activations[j] > 0}
										>
											{formatToken(token)}
										</span>
										{#if showActivations}
											<span
												class="mt-0.5 text-center font-mono leading-tight text-gray-500 transition-opacity {compact
													? 'text-[8px] sm:text-[9px]'
													: 'text-[9px] sm:text-[10px]'}"
											>
												{example.activations[j] === 0 ? '' : example.activations[j].toFixed(1)}
											</span>
										{/if}
									</div>
								{/each}
							</div>

							<!-- Max token - centered -->
							<div class="flex flex-shrink-0 flex-col items-center px-2 sm:px-4">
								<span
									class="flex items-center rounded px-1 py-0.5 font-mono transition-all duration-200 sm:px-1.5 {compact
										? 'min-h-[1.25rem] text-[10px] sm:text-xs'
										: 'min-h-[1.5rem] text-xs sm:text-sm'}"
									style={showHighlighting
										? `background-color: ${getActivationColor(example.activations[maxActivationIndex], effectiveMaxActivation)}; color: ${getTextColor(example.activations[maxActivationIndex], effectiveMaxActivation)};`
										: 'background-color: rgb(243, 244, 246); color: rgb(55, 65, 81);'}
									class:font-medium={showHighlighting &&
										example.activations[maxActivationIndex] > 0}
								>
									{formatToken(example.tokens[maxActivationIndex])}
								</span>
								{#if showActivations}
									<span
										class="mt-0.5 text-center font-mono leading-tight transition-opacity {compact
											? 'text-[8px] sm:text-[9px]'
											: 'text-[9px] sm:text-[10px]'} font-semibold text-blue-600"
									>
										{example.activations[maxActivationIndex] === 0
											? ''
											: example.activations[maxActivationIndex].toFixed(1)}
									</span>
								{/if}
							</div>

							<!-- Right tokens (after max) - left aligned -->
							<div class="flex min-w-0 flex-1 flex-wrap gap-0.5">
								{#each example.tokens.slice(maxActivationIndex + 1) as token, j}
									{@const tokenIndex = maxActivationIndex + 1 + j}
									<div class="flex flex-col items-center">
										<span
											class="flex items-center rounded px-1 py-0.5 font-mono transition-all duration-200 sm:px-1.5 {compact
												? 'min-h-[1.25rem] text-[10px] sm:text-xs'
												: 'min-h-[1.5rem] text-xs sm:text-sm'}"
											style={showHighlighting
												? `background-color: ${getActivationColor(example.activations[tokenIndex], effectiveMaxActivation)}; color: ${getTextColor(example.activations[tokenIndex], effectiveMaxActivation)};`
												: 'background-color: rgb(243, 244, 246); color: rgb(55, 65, 81);'}
											class:font-medium={showHighlighting && example.activations[tokenIndex] > 0}
										>
											{formatToken(token)}
										</span>
										{#if showActivations}
											<span
												class="mt-0.5 text-center font-mono leading-tight text-gray-500 transition-opacity {compact
													? 'text-[8px] sm:text-[9px]'
													: 'text-[9px] sm:text-[10px]'}"
											>
												{example.activations[tokenIndex] === 0
													? ''
													: example.activations[tokenIndex].toFixed(1)}
											</span>
										{/if}
									</div>
								{/each}
							</div>
						</div>
					{:else}
						<!-- Flex layout for left alignment -->
						<div class="flex flex-1 flex-wrap gap-0.5">
							{#each example.tokens as token, j}
								<div class="flex flex-col items-center">
									<span
										class="flex items-center rounded px-1 py-0.5 font-mono transition-all duration-200 sm:px-1.5 {compact
											? 'min-h-[1.25rem] text-[10px] sm:text-xs'
											: 'min-h-[1.5rem] text-xs sm:text-sm'}"
										style={showHighlighting
											? `background-color: ${getActivationColor(example.activations[j], effectiveMaxActivation)}; color: ${getTextColor(example.activations[j], effectiveMaxActivation)};`
											: 'background-color: rgb(243, 244, 246); color: rgb(55, 65, 81);'}
										class:font-medium={showHighlighting && example.activations[j] > 0}
									>
										{formatToken(token)}
									</span>
									{#if showActivations}
										<span
											class="mt-0.5 text-center font-mono leading-tight text-gray-500 transition-opacity {compact
												? 'text-[8px] sm:text-[9px]'
												: 'text-[9px] sm:text-[10px]'}"
										>
											{example.activations[j] === 0 ? '' : example.activations[j].toFixed(1)}
										</span>
									{/if}
								</div>
							{/each}
						</div>
					{/if}

					<!-- Match indicator column -->
					{#if showMatchColumn && example.match !== undefined}
						<div class="flex w-6 flex-shrink-0 items-start justify-center pt-1 sm:w-8">
							{#if example.match === 1}
								<span
									class="flex items-center justify-center text-base font-semibold text-green-600 sm:text-lg"
									title="Match"
								>
									<Icon icon="check" color="text-green-500" />
								</span>
							{:else}
								<span
									class="flex items-center justify-center text-base font-semibold text-red-600 sm:text-lg"
									title="No match"><Icon icon="xmark" color="text-red-500" /></span
								>
							{/if}
						</div>
					{/if}
				</div>
			{/each}
		</div>

		<!-- Pagination Controls -->
		{#if paginate && totalPages > 1}
			<div class="flex items-center justify-between border-t border-gray-200 pt-4">
				<button
					onclick={goToPreviousPage}
					disabled={currentPage === 0}
					class="flex cursor-pointer items-center gap-1 rounded-md border border-gray-300 bg-white px-2 py-1 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-white sm:px-3 sm:py-1.5 sm:text-sm"
				>
					<Icon icon="arrow-left" />
					<span class="hidden sm:inline">Previous</span>
					<span class="sm:hidden">Prev</span>
				</button>

				<span class="text-xs text-gray-600 sm:text-sm">
					Page {currentPage + 1} of {totalPages}
				</span>

				<button
					onclick={goToNextPage}
					disabled={currentPage === totalPages - 1}
					class="flex cursor-pointer items-center gap-1 rounded-md border border-gray-300 bg-white px-2 py-1 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-white sm:px-3 sm:py-1.5 sm:text-sm"
				>
					<span class="sm:hidden">Next</span>
					<span class="hidden sm:inline">Next</span>
					<Icon icon="arrow-right" />
				</button>
			</div>
		{/if}
	{/if}
</div>
