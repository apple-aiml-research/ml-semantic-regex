<!--
For licensing see accompanying LICENSE file.
Copyright (C) 2025 Apple Inc. All Rights Reserved.
-->

<script>
	let {
		value,
		min = 0,
		max = 1,
		height = 'h-1.5',
		width = 'w-full',
		showValue = false,
		className = ''
	} = $props();

	// Calculate the percentage for the bar
	const percentage = $derived.by(() => {
		if (typeof value !== 'number' || isNaN(value)) return 0;
		const normalizedValue = Math.max(min, Math.min(max, value));
		return ((normalizedValue - min) / (max - min)) * 100;
	});
</script>

<div class="flex items-center space-x-2">
	<div class="{height} {width} rounded bg-gray-200 {className}">
		<div
			style:width="{percentage}%"
			class="{height} rounded bg-gray-500 transition-all duration-300"
		></div>
	</div>
	{#if showValue}
		<span class="min-w-0 text-xs text-gray-500">
			{typeof value === 'number' ? value.toFixed(2) : value}
		</span>
	{/if}
</div>
