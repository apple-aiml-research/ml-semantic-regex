<!--
For licensing see accompanying LICENSE file.
Copyright (C) 2025 Apple Inc. All Rights Reserved.
-->

<script>
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { navigating } from '$app/state';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Semantic Regex</title>
</svelte:head>

{#if navigating.to}
	<div class="fixed inset-0 flex items-center justify-center">
		<div class="text-center">
			<div
				class="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-gray-900"
			></div>
			<p class="text-gray-600">Loading...</p>
		</div>
	</div>
{:else}
	{@render children?.()}
{/if}
