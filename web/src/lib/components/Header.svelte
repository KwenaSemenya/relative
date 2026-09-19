<script lang="ts">
	import { NARRATIVE_LABEL } from '$lib/data/narrative';

	interface Props {
		isDark: boolean;
		modeLabel: string;
		onToggleMode: () => void;
		onOpenNarrative: () => void;
	}

	let { isDark, modeLabel, onToggleMode, onOpenNarrative }: Props = $props();
</script>

<header>
	<div class="lockup">
		<h1 class="wordmark">relative</h1>
		<p class="standfirst">
			Turn one approved brand narrative into on-message assets, with every line traced back to a
			proof point.
		</p>
	</div>

	<div class="controls">
		<button type="button" class="narrative-link" onclick={onOpenNarrative}>
			Approved narrative — {NARRATIVE_LABEL}
		</button>

		<button
			type="button"
			class="mode-toggle"
			onclick={onToggleMode}
			aria-label={modeLabel}
			title={modeLabel}
		>
			{#if isDark}
				<svg
					width="18"
					height="18"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
					stroke-linecap="round"
					aria-hidden="true"
				>
					<circle cx="12" cy="12" r="4" />
					<path
						d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"
					/>
				</svg>
			{:else}
				<svg
					width="18"
					height="18"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"
				>
					<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
				</svg>
			{/if}
		</button>
	</div>
</header>

<style>
	header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 48px;
		flex-wrap: wrap;
		padding-bottom: 28px;
	}

	.lockup {
		display: grid;
		gap: 8px;
		max-width: 62ch;
	}

	.wordmark {
		font-family: var(--serif);
		font-weight: 400;
		font-size: clamp(28px, 7vw, 34px);
		line-height: 1;
		letter-spacing: -0.025em;
		margin: 0;
	}

	.standfirst {
		font-size: 17px;
		line-height: 1.5;
		color: var(--ink-2);
		max-width: 58ch;
		text-wrap: pretty;
		margin: 0;
	}

	.controls {
		display: flex;
		align-items: center;
		gap: 20px;
		flex-wrap: wrap;
	}

	.narrative-link {
		font-family: inherit;
		font-size: 15px;
		text-align: left;
		color: var(--ink-2);
		background: transparent;
		border: 0;
		border-bottom: 1px solid var(--line);
		padding: 6px 0;
		cursor: pointer;
		transition: color 160ms ease-out;
	}

	.narrative-link:hover {
		color: var(--ink);
	}

	.mode-toggle {
		width: 40px;
		height: 40px;
		display: grid;
		place-items: center;
		background: transparent;
		border: 0;
		color: var(--ink-3);
		cursor: pointer;
		padding: 0;
		transition: color 160ms ease-out;
	}

	.mode-toggle:hover {
		color: var(--ink);
	}

	.mode-toggle svg {
		display: block;
	}
</style>
