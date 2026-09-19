<script lang="ts">
	interface Line {
		id: string;
		text: string;
		reason: string | null;
		evidence: string;
		sourceNo: string;
		editing: boolean;
		checking: boolean;
		flagged: boolean;
		showMarker: boolean;
		justChecked: boolean;
		canEdit: boolean;
		editRevealed: boolean;
		evidenceOpen: boolean;
	}

	interface Props {
		line: Line;
		editText: string;
		onHover: (id: string | null) => void;
		onStartEdit: (id: string) => void;
		onEditText: (value: string) => void;
		onSaveEdit: () => void;
		onCancelEdit: () => void;
		onEvidenceOpen: (id: string | null) => void;
		onEvidenceToggle: (id: string) => void;
	}

	let {
		line,
		editText,
		onHover,
		onStartEdit,
		onEditText,
		onSaveEdit,
		onCancelEdit,
		onEvidenceOpen,
		onEvidenceToggle
	}: Props = $props();
</script>

<div
	class="line"
	onmouseenter={() => onHover(line.id)}
	onmouseleave={() => onHover(null)}
	role="group"
>
	{#if line.editing}
		<div class="edit">
			<textarea
				rows="3"
				value={editText}
				oninput={(e) => onEditText(e.currentTarget.value)}
				aria-label="Edit this line"
			></textarea>
			<div class="edit-actions">
				<button type="button" class="save" onclick={onSaveEdit}>Save and re-check</button>
				<button type="button" class="cancel" onclick={onCancelEdit}>Cancel</button>
			</div>
		</div>
	{:else}
		<p class="text">{line.text}</p>
	{/if}

	{#if line.checking}
		<div class="checking" role="status">
			<span class="chip">·</span>
			<span>Re-checking this line against the narrative</span>
		</div>
	{/if}

	{#if line.showMarker}
		<div class="marker-row">
			<button
				type="button"
				class="marker"
				aria-expanded={line.evidenceOpen}
				aria-label={`Evidence, proof point ${line.sourceNo}`}
				onclick={() => onEvidenceToggle(line.id)}
				onmouseenter={() => onEvidenceOpen(line.id)}
				onmouseleave={() => onEvidenceOpen(null)}
				onfocus={() => onEvidenceOpen(line.id)}
				onblur={() => onEvidenceOpen(null)}
			>
				<span class="chip">{line.sourceNo}</span>
				<span class="marker-label">Evidence</span>
			</button>

			{#if line.justChecked}
				<span class="rechecked">Re-checked, on message</span>
			{/if}

			{#if line.evidenceOpen}
				<div class="popover" role="tooltip">
					<div class="popover-kicker">Proof point {line.sourceNo}</div>
					<div class="popover-body">{line.evidence}</div>
				</div>
			{/if}
		</div>
	{/if}

	{#if line.flagged}
		<div class="flag">
			<div class="flag-kicker">Flagged — off narrative</div>
			<p class="flag-reason">{line.reason}</p>
		</div>
	{/if}

	{#if line.canEdit}
		<div>
			<button
				type="button"
				class="edit-affordance"
				class:revealed={line.editRevealed}
				onclick={() => onStartEdit(line.id)}
				onfocus={() => onHover(line.id)}
			>
				Edit this line
			</button>
		</div>
	{/if}
</div>

<style>
	.line {
		display: grid;
		gap: 14px;
		padding: 26px 0;
		max-width: 74ch;
	}

	.text {
		font-size: clamp(17px, 2.2vw, 19px);
		line-height: 1.65;
		text-wrap: pretty;
		margin: 0;
	}

	.edit {
		display: grid;
		gap: 14px;
	}

	.edit textarea {
		font-family: inherit;
		font-size: 19px;
		line-height: 1.65;
		color: var(--ink);
		background: var(--s1);
		border: 0;
		padding: 14px;
		width: 100%;
		box-sizing: border-box;
		resize: vertical;
	}

	.edit-actions {
		display: flex;
		gap: 20px;
		align-items: center;
	}

	.save {
		font-family: inherit;
		font-size: 15px;
		text-align: left;
		background: var(--ink);
		color: var(--bg);
		border: 0;
		padding: 12px 20px;
		cursor: pointer;
	}

	.cancel {
		font-family: inherit;
		font-size: 15px;
		text-align: left;
		background: transparent;
		color: var(--ink-3);
		border: 0;
		padding: 12px 0;
		cursor: pointer;
		text-decoration: underline;
		text-underline-offset: 4px;
	}

	.checking {
		display: flex;
		align-items: center;
		gap: 12px;
		font-size: 14px;
		color: var(--ink-2);
		animation: recheck 900ms ease-in-out infinite;
	}

	.chip {
		width: 22px;
		height: 22px;
		display: grid;
		place-items: center;
		background: var(--s2);
		font-family: var(--serif);
		font-size: 14px;
		line-height: 1;
		color: var(--ink-2);
		flex: none;
	}

	.checking .chip {
		font-size: 13px;
	}

	.marker-row {
		position: relative;
		display: flex;
		align-items: center;
		gap: 12px;
		flex-wrap: wrap;
	}

	.marker {
		font-family: inherit;
		display: flex;
		align-items: center;
		gap: 9px;
		background: transparent;
		border: 0;
		padding: 0;
		cursor: pointer;
		color: var(--ink-3);
		transition: color 160ms ease-out;
	}

	.marker:hover {
		color: var(--ink);
	}

	.marker-label {
		font-size: 12px;
		letter-spacing: 0.12em;
		text-transform: uppercase;
	}

	.rechecked {
		font-size: 12px;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--ok-ink);
	}

	.popover {
		position: absolute;
		left: 0;
		bottom: calc(100% + 10px);
		z-index: 5;
		background: var(--s3);
		color: var(--ink);
		padding: 14px 16px;
		width: min(380px, 78vw);
		display: grid;
		gap: 4px;
	}

	.popover-kicker {
		font-size: 12px;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--ink-3);
	}

	.popover-body {
		font-size: 15px;
		line-height: 1.5;
	}

	.flag {
		background: var(--flag-bg);
		border-left: 2px solid var(--flag-mark);
		padding: 18px 20px;
		display: grid;
		gap: 7px;
		max-width: 70ch;
	}

	.flag-kicker {
		font-size: 12px;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--flag-ink);
	}

	.flag-reason {
		font-size: 16px;
		line-height: 1.6;
		color: var(--ink);
		margin: 0;
	}

	.edit-affordance {
		font-family: inherit;
		font-size: 14px;
		text-align: left;
		background: transparent;
		color: var(--ink-3);
		border: 0;
		padding: 8px 0;
		cursor: pointer;
		opacity: 0.75;
		transition:
			opacity 160ms ease-out,
			background 160ms ease-out;
	}

	.edit-affordance.revealed {
		background: var(--s2);
		color: var(--ink);
		padding: 8px 14px;
		opacity: 1;
	}
</style>
