<!--
For licensing see accompanying LICENSE file.
Copyright (C) 2025 Apple Inc. All Rights Reserved.
-->

<script>
	let { icon, onclick, disabled = false, active = false, title = '' } = $props();

	import Icon from './Icon.svelte';
</script>

<button
	{onclick}
	{disabled}
	{title}
	class="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full border border-gray-300 bg-white transition-colors hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
	class:bg-blue-50={active}
	class:border-blue-300={active}
	class:text-blue-700={active}
>
	<Icon {icon} />
</button>
