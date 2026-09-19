<script lang="ts">
	import { DEMO_STATES, type DemoState } from '$lib/state/kit.svelte';

	interface Props {
		current: DemoState;
		onPick: (id: DemoState) => void;
	}

	let { current, onPick }: Props = $props();
</script>

<div class="bar">
	<span class="caption" id="demo-bar-label">See how it handles each state</span>
	<div class="options" role="group" aria-labelledby="demo-bar-label">
		{#each DEMO_STATES as state (state.id)}
			<button
				type="button"
				class="option"
				class:on={current === state.id}
				aria-pressed={current === state.id}
				onclick={() => onPick(state.id)}
			>
				{state.label}
			</button>
		{/each}
	</div>
</div>

<style>
	.bar {
		background: var(--s1);
		padding: 14px clamp(16px, 3.5vw, 24px);
		display: flex;
		gap: 18px;
		align-items: center;
		flex-wrap: wrap;
	}

	.caption {
		font-size: 15px;
		color: var(--ink-2);
	}

	.options {
		display: flex;
		gap: 6px;
		flex-wrap: wrap;
	}

	.option {
		font-family: inherit;
		font-size: 13px;
		text-align: left;
		background: var(--bg);
		color: var(--ink-3);
		border: 0;
		padding: 9px 13px;
		cursor: pointer;
		transition: background 160ms ease-out;
	}

	.option:hover {
		background: var(--s3);
	}

	/* The design gives the active button 8px 12px against the inactive 9px 13px,
	   with border:0 on both, so switching state reflows the row by 2px. Padding
	   is kept equal here so the bar never shifts under the cursor. */
	.option.on {
		background: var(--ink);
		color: var(--bg);
	}

	.option.on:hover {
		background: var(--ink);
	}
</style>
