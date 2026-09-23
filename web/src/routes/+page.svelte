<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import DemoBar from '$lib/components/DemoBar.svelte';
	import BriefPanel from '$lib/components/BriefPanel.svelte';
	import KitPanel from '$lib/components/KitPanel.svelte';
	import NarrativeSheet from '$lib/components/NarrativeSheet.svelte';
	import { deserialize } from '$app/forms';
	import { KitState, type DraftInput, type DraftResult } from '$lib/state/kit.svelte';
	import type { Kit } from '$lib/types';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	async function draft(input: DraftInput): Promise<DraftResult> {
		const body = new FormData();
		body.set('brief', input.brief);
		body.set('audience', input.audience);
		body.set('sensitiveMarket', String(input.sensitiveMarket));
		for (const proof of input.proofPoints) body.append('proofPoint', proof);

		const response = await fetch('?/generate', { method: 'POST', body });

		// An action's payload is devalue-encoded, not JSON: it is a flat array
		// where objects hold indices into it. JSON.parse would hand back those
		// indices as if they were the values. deserialize rebuilds the graph.
		const result = deserialize<
			{ kit?: Kit; refusal?: DraftResult['refusal']; limit?: DraftResult['limit'] },
			{ message: string }
		>(await response.text());

		if (result.type === 'failure') {
			throw new Error(result.data?.message ?? 'The brief could not be checked just now.');
		}
		if (result.type !== 'success') {
			throw new Error('The brief could not be checked just now.');
		}

		return {
			kit: result.data?.kit ?? null,
			refusal: result.data?.refusal ?? null,
			limit: result.data?.limit ?? null
		};
	}

	const kit = new KitState({
		kit: data.kit ?? undefined,
		narrative: data.narrative ?? undefined,
		draft
	});

	$effect(() => {
		kit.initMode();
		return () => kit.destroy();
	});
</script>

<svelte:head>
	<title>Relative — one approved narrative, on-message assets</title>
	<meta
		name="description"
		content="Turn one approved brand narrative into on-message assets, with every line traced back to a proof point."
	/>
</svelte:head>

<div class="shell">
	<Header
		isDark={kit.isDark}
		modeLabel={kit.modeLabel}
		onToggleMode={() => kit.toggleMode()}
		onOpenNarrative={() => (kit.narrativeOpen = true)}
	/>

	<div class="rule"></div>

	<DemoBar current={kit.demo} onPick={(id) => kit.setDemo(id)} />

	<main>
		<BriefPanel
			brief={kit.brief}
			audience={kit.audience}
			proofInputs={kit.proofInputs}
			sensitive={kit.sensitive}
			canGenerate={kit.canGenerate}
			generateLabel={kit.generateLabel}
			generateBlockedWhy={kit.generateBlockedWhy}
			error={kit.actionError}
			onBrief={(v) => (kit.brief = v)}
			onAudience={(v) => (kit.audience = v)}
			onProof={(i, v) => (kit.proofInputs[i] = v)}
			onSensitive={(v) => {
				kit.sensitive = v;
				kit.demo = v ? 'sensitive' : 'landing';
			}}
			onGenerate={() => kit.generate()}
		/>

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

	main {
		display: flex;
		flex-wrap: wrap;
		gap: clamp(36px, 5vw, 72px);
		padding-top: clamp(28px, 4vw, 44px);
		align-items: flex-start;
	}
</style>
