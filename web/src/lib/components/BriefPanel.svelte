<script lang="ts">
	import { AUDIENCES } from '$lib/types';

	interface Props {
		brief: string;
		audience: string;
		proofInputs: string[];
		sensitive: boolean;
		canGenerate: boolean;
		generateLabel: string;
		generateBlockedWhy: string;
		onBrief: (value: string) => void;
		onAudience: (value: string) => void;
		onProof: (index: number, value: string) => void;
		onSensitive: (value: boolean) => void;
		onGenerate: () => void;
	}

	let {
		brief,
		audience,
		proofInputs,
		sensitive,
		canGenerate,
		generateLabel,
		generateBlockedWhy,
		onBrief,
		onAudience,
		onProof,
		onSensitive,
		onGenerate
	}: Props = $props();

	const placeholders = [
		'Source and what it measured',
		'Second proof point',
		'Third proof point (optional)'
	];
</script>

<section class="brief-panel">
	<div class="field">
		<label class="kicker" for="brief">Brief</label>
		<textarea
			id="brief"
			rows="4"
			value={brief}
			oninput={(e) => onBrief(e.currentTarget.value)}
			placeholder="What is this kit for?"
		></textarea>
	</div>

	<div class="field">
		<div class="kicker" id="audience-label">Audience</div>
		<div class="audience-grid" role="group" aria-labelledby="audience-label">
			{#each AUDIENCES as option (option)}
				<button
					type="button"
					class="audience"
					class:on={audience === option}
					aria-pressed={audience === option}
					onclick={() => onAudience(option)}
				>
					{option}
				</button>
			{/each}
		</div>
	</div>

	<div class="field">
		<div class="kicker" id="proofs-label">Proof points</div>
		<p class="help">
			A usable proof point names a source and what it measured. "Ridgeway pilot, 2025 — prep time"
			works. "Teachers love it" doesn't.
		</p>
		{#each proofInputs as value, i (i)}
			<input
				type="text"
				{value}
				oninput={(e) => onProof(i, e.currentTarget.value)}
				placeholder={placeholders[i]}
				aria-label={`Proof point ${i + 1}`}
			/>
		{/each}
	</div>

	<div class="sensitive">
		<label class="checkbox">
			<input
				type="checkbox"
				checked={sensitive}
				onchange={(e) => onSensitive(e.currentTarget.checked)}
			/>
			<span>Sensitive market</span>
		</label>
		<p class="help indented">
			Kits for these markets go to a named reviewer before anyone can approve them here.
		</p>
	</div>

	<div class="generate">
		{#if canGenerate}
			<button type="button" class="generate-btn" onclick={onGenerate}>Generate kit</button>
		{:else}
			<button type="button" class="generate-btn blocked" disabled aria-describedby="generate-why">
				{generateLabel}
			</button>
			{#if generateBlockedWhy}
				<p class="why" id="generate-why">{generateBlockedWhy}</p>
			{/if}
		{/if}
	</div>
</section>

<style>
	.brief-panel {
		flex: 1 1 var(--brief-basis);
		max-width: var(--brief-max);
		display: grid;
		gap: 30px;
	}

	.field {
		display: grid;
		gap: 10px;
	}

	.kicker {
		font-size: 12px;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--ink-3);
	}

	textarea {
		font-family: inherit;
		font-size: 16px;
		line-height: 1.5;
		color: var(--ink);
		background: var(--s1);
		border: 0;
		padding: 14px;
		resize: vertical;
		width: 100%;
		box-sizing: border-box;
	}

	input[type='text'] {
		font-family: inherit;
		font-size: 16px;
		color: var(--ink);
		background: var(--s1);
		border: 0;
		padding: 13px 14px;
		width: 100%;
		box-sizing: border-box;
	}

	.audience-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 6px;
	}

	.audience {
		font-family: inherit;
		font-size: 15px;
		text-align: left;
		background: var(--s1);
		color: var(--ink-2);
		border: 0;
		padding: 12px 14px;
		cursor: pointer;
		transition: background 160ms ease-out;
	}

	.audience:hover {
		background: var(--s3);
	}

	.audience.on {
		background: var(--ink);
		color: var(--bg);
	}

	.help {
		font-size: 14px;
		line-height: 1.5;
		color: var(--ink-3);
		max-width: 46ch;
		margin: 0;
	}

	.sensitive {
		display: grid;
		gap: 8px;
	}

	.checkbox {
		display: flex;
		gap: 12px;
		align-items: flex-start;
		cursor: pointer;
		font-size: 16px;
		color: var(--ink);
	}

	.checkbox input {
		width: 20px;
		height: 20px;
		margin: 0;
		accent-color: var(--ink);
	}

	.indented {
		max-width: 44ch;
		padding-left: 32px;
	}

	.generate {
		display: grid;
		gap: 10px;
	}

	.generate-btn {
		font-family: inherit;
		font-size: 17px;
		text-align: left;
		background: var(--accent);
		color: var(--accent-ink);
		border: 0;
		padding: 17px 18px;
		width: 100%;
		cursor: pointer;
		transition: background 160ms ease-out;
	}

	.generate-btn:hover {
		background: var(--accent-press);
	}

	.generate-btn.blocked {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.generate-btn.blocked:hover {
		background: var(--accent);
	}

	.why {
		font-size: 14px;
		color: var(--ink-3);
		margin: 0;
	}
</style>
