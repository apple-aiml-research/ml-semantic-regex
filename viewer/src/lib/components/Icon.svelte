<!--
For licensing see accompanying LICENSE file.
Copyright (C) 2025 Apple Inc. All Rights Reserved.
-->

<script>
	let { icon, height = 'h-4', width = 'w-4', color = 'text-gray-600', style = '' } = $props();

	import IconArrowLeft from 'virtual:icons/fa7-solid/arrow-left';
	import IconArrowRight from 'virtual:icons/fa7-solid/arrow-right';
	import IconList from 'virtual:icons/fa7-solid/list';
	import IconPaintBrush from 'virtual:icons/fa7-solid/paint-brush';
	import IconShuffle from 'virtual:icons/fa7-solid/shuffle';
	import IconHashtag from 'virtual:icons/fa7-solid/hashtag';
	import IconAlignCenter from 'virtual:icons/fa7-solid/align-center';
	import IconAlignLeft from 'virtual:icons/fa7-solid/align-left';
	import IconAlignXMark from 'virtual:icons/fa7-solid/xmark';
	import IconFilter from 'virtual:icons/fa7-solid/filter';
	import IconCheck from 'virtual:icons/fa7-solid/check';
	import IconFileAlt from 'virtual:icons/fa7-regular/file-alt';
	import IconGithub from 'virtual:icons/fa7-brands/github';
	import IconLineChart from 'virtual:icons/fa7-solid/line-chart';
	import IconPython from 'virtual:icons/fa7-brands/python';
	import IconChevronDown from 'virtual:icons/fa7-solid/chevron-down';
	import IconRightDown from 'virtual:icons/fa7-solid/chevron-right';

	const iconMap = {
		'arrow-left': IconArrowLeft,
		'arrow-right': IconArrowRight,
		list: IconList,
		'paint-brush': IconPaintBrush,
		shuffle: IconShuffle,
		hashtag: IconHashtag,
		'align-center': IconAlignCenter,
		'align-left': IconAlignLeft,
		xmark: IconAlignXMark,
		filter: IconFilter,
		check: IconCheck,
		'file-alt': IconFileAlt,
		github: IconGithub,
		'line-chart': IconLineChart,
		python: IconPython,
		'chevron-down': IconChevronDown,
		'chevron-right': IconRightDown
	};
</script>

{#if iconMap[icon]}
	{@const IconComponent = iconMap[icon]}
	<IconComponent class="{height} {width} {color} {style}" />
{:else}
	{icon}
{/if}
