<script lang="ts">
	import { NARRATIVE, NARRATIVE_LABEL } from '$lib/data/narrative';
	import type { Narrative } from '$lib/types';

	interface Props {
		narrative?: Narrative;
		onClose: () => void;
	}

	let { narrative = NARRATIVE, onClose }: Props = $props();

	const label = $derived(narrative.label ?? NARRATIVE_LABEL);

	let panel = $state<HTMLElement | null>(null);

	// The sheet takes focus when it opens and Escape closes it, so it is
	// usable without a mouse. The design does not specify this behaviour.
	$effect(() => {
		panel?.focus();
	});

	function onKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') onClose();
	}
</script>

<svelte:window onkeydown={onKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="backdrop" onclick={onClose}>
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="sheet"
		bind:this={panel}
		tabindex="-1"
		role="dialog"
		aria-modal="true"
		aria-labelledby="narrative-heading"
		onclick={(e) => e.stopPropagation()}
	>
		<div class="sheet-head">
			<div class="titles">
				<h2 id="narrative-heading">Approved narrative</h2>
				<p class="sub">{label}. Read-only — HQ owns this.</p>
			</div>
			<button type="button" class="close" onclick={onClose}>Close</button>
		</div>

		<div class="pillars">
			<div class="kicker">Message pillars</div>
			{#each narrative.pillars as pillar (pillar.id)}
				<div class="pillar">
					<div class="pillar-title">{pillar.title}</div>
					<p class="pillar-body">{pillar.body}</p>
				</div>
			{/each}
		</div>

		<div class="never">
			<div class="kicker">Never say</div>
			{#each narrative.neverSay as phrase (phrase)}
				<div class="never-item">{phrase}</div>
			{/each}
		</div>
	</div>
</div>

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		background: rgba(10, 10, 10, 0.5);
		z-index: 40;
		display: flex;
		justify-content: flex-end;
	}

	.sheet {
		background: var(--s1);
		color: var(--ink);
		width: min(560px, 100%);
		height: 100%;
		overflow: auto;
		padding: clamp(24px, 5vw, 40px) clamp(20px, 5vw, 44px);
		box-sizing: border-box;
		display: grid;
		gap: 32px;
		align-content: start;
	}

	.sheet-head {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 24px;
	}

	.titles {
		display: grid;
		gap: 6px;
	}

	h2 {
		font-family: var(--serif);
		font-weight: 400;
		font-size: clamp(26px, 6vw, 32px);
		line-height: 1.1;
		letter-spacing: -0.02em;
		margin: 0;
	}

	.sub {
		font-size: 15px;
		color: var(--ink-3);
		margin: 0;
	}

	.close {
		font-family: inherit;
		font-size: 15px;
		text-align: left;
		background: transparent;
		color: var(--ink-2);
		border: 0;
		padding: 6px 0;
		cursor: pointer;
		text-decoration: underline;
		text-underline-offset: 4px;
		flex: none;
	}

	.pillars {
		display: grid;
		gap: 22px;
	}

	.kicker {
		font-size: 12px;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--ink-3);
	}

	.pillar {
		display: grid;
		gap: 5px;
		max-width: 52ch;
	}

	.pillar-title {
		font-family: var(--serif);
		font-weight: 400;
		font-size: 21px;
		line-height: 1.25;
	}

	.pillar-body {
		font-size: 16px;
		line-height: 1.6;
		color: var(--ink-2);
		margin: 0;
	}

	.never {
		display: grid;
		gap: 14px;
		border-top: 2px solid var(--rule);
		padding-top: 26px;
	}

	.never-item {
		font-size: 17px;
		color: var(--ink-2);
	}
</style>
