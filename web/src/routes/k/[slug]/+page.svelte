<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import KitPanel from '$lib/components/KitPanel.svelte';
	import NarrativeSheet from '$lib/components/NarrativeSheet.svelte';
	import { KitState, type Persist } from '$lib/state/kit.svelte';
	import type { AssetType, Kit, ReviewState } from '$lib/types';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	async function post(action: string, fields: Record<string, string>): Promise<Kit> {
		const body = new FormData();
		for (const [k, v] of Object.entries(fields)) body.set(k, v);

		const response = await fetch(`?/${action}`, { method: 'POST', body });
		const result = await response.json();
		// SvelteKit wraps action results; a failure has no kit to apply.
		const parsed = JSON.parse(result.data ?? 'null');
		const returned = Array.isArray(parsed) ? parsed[0]?.kit : parsed?.kit;
		if (result.type !== 'success' || !returned) throw new Error('save failed');
		return returned as Kit;
	}

	const persist: Persist = {
		review: (assetType: AssetType, reviewState: ReviewState) =>
			post('review', { assetType, reviewState }),
		edit: (claimId: string, body: string) => post('edit', { claimId, body })
	};

	const kit = new KitState({
		kit: data.kit,
		narrative: data.narrative,
		live: true,
		persist
	});

	$effect(() => {
		kit.initMode();
		return () => kit.destroy();
	});
</script>

<svelte:head>
	<title>{data.kit.audience} kit — Relative</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="shell">
	<Header
		isDark={kit.isDark}
		modeLabel={kit.modeLabel}
		onToggleMode={() => kit.toggleMode()}
		onOpenNarrative={() => (kit.narrativeOpen = true)}
	/>

	<div class="rule"></div>

	<div class="brief-strip">
		<div class="kicker">The brief this came from</div>
		<p class="brief-text">{data.kit.brief}</p>
		<div class="facts">
			<span>{data.kit.audience}</span>
			<span>·</span>
			<span>{data.kit.proofPoints.length} proof points</span>
			{#if data.kit.sensitiveMarket}
				<span>·</span>
				<span>Sensitive market</span>
			{/if}
		</div>
	</div>

	{#if kit.actionError}
		<p class="action-error" role="alert">{kit.actionError}</p>
	{/if}

	<main>
		<KitPanel {kit} />
	</main>
</div>

{#if kit.narrativeOpen}
	<NarrativeSheet narrative={kit.narrative} onClose={() => (kit.narrativeOpen = false)} />
{/if}

<style>
	.shell {
		background: var(--bg);
		color: var(--ink);
		font-family: var(--sans);
		font-weight: 400;
		font-size: 17px;
		line-height: 1.5;
		min-height: 100vh;
		padding: clamp(20px, 4vw, 36px) clamp(16px, 3.5vw, 44px) 72px;
		box-sizing: border-box;
	}

	.rule {
		height: 2px;
		background: var(--rule);
	}

	/* The brief panel is not editable on a shared kit, so the brief is shown as
	   context instead. The design has no component for this; it reuses the
	   kicker and body type already defined there. */
	.brief-strip {
		display: grid;
		gap: 8px;
		max-width: 74ch;
		padding-top: clamp(24px, 4vw, 36px);
	}

	.kicker {
		font-size: 12px;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--ink-3);
	}

	.brief-text {
		font-size: clamp(18px, 2.4vw, 21px);
		line-height: 1.55;
		margin: 0;
		text-wrap: pretty;
	}

	.facts {
		display: flex;
		gap: 8px;
		flex-wrap: wrap;
		font-size: 15px;
		color: var(--ink-3);
	}

	.action-error {
		background: var(--flag-bg);
		border-left: 2px solid var(--flag-mark);
		color: var(--ink);
		font-size: 16px;
		padding: 14px 18px;
		margin: 24px 0 0;
		max-width: 70ch;
	}

	main {
		padding-top: clamp(28px, 4vw, 44px);
	}
</style>
