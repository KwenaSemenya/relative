<script lang="ts">
	import ClaimLine from './ClaimLine.svelte';
	import { SENSITIVE_REVIEWER } from '$lib/data/narrative';
	import { REFUSAL_FIX, REFUSAL_REASON, type KitState } from '$lib/state/kit.svelte';

	interface Props {
		kit: KitState;
	}

	let { kit }: Props = $props();
</script>

<section class="kit-panel">
	<div class="kit-head">
		<h2 class="kit-title">{kit.kitTitle}</h2>
		<div class="kit-meta">{kit.kitMeta}</div>
	</div>

	{#if kit.showNotice && kit.notice}
		{@const notice = kit.notice}
		<div class="notice">
			<div class="kicker">{notice.kicker}</div>
			<div class="notice-title">{notice.title}</div>
			<p class="notice-body">{notice.body}</p>
			{#if notice.hasLink}
				<div class="link-row">
					<span class="link">{notice.link}</span>
					<button type="button" class="copy" onclick={() => kit.copyLink(notice.link)}>
						{kit.copyLabel}
					</button>
				</div>
			{/if}
		</div>
	{/if}

	{#if kit.view === 'refusal'}
		<div class="refusal">
			<div class="refusal-card">
				<div class="kicker flag-kicker">Not generated</div>
				<div class="refusal-title">A proof point contradicts the brief, so nothing was written.</div>
				<p class="refusal-reason">{REFUSAL_REASON}</p>
			</div>
			<div class="fix">
				<div class="kicker">How to fix it</div>
				<p class="fix-body">{REFUSAL_FIX}</p>
				<p class="fix-note">Everything you typed is still in the brief panel.</p>
			</div>
		</div>
	{/if}

	{#if kit.generating}
		<div class="generating" role="status" aria-live="polite">
			<div class="track">
				<div class="fill" style:width={kit.progressWidth}></div>
			</div>
			{#each kit.steps as step (step.label)}
				<div class="step">
					<span class="step-mark">{step.mark}</span>
					<span>{step.label}</span>
				</div>
			{/each}
			<p class="step-note">{kit.generationCount}</p>
		</div>
	{/if}

	{#if kit.view === 'kit'}
		<div class="kit-body">
			<div class="tabs" role="tablist" aria-label="Asset types">
				{#each kit.tabs as tab (tab.assetType)}
					<button
						type="button"
						role="tab"
						class="tab"
						class:on={tab.on}
						aria-selected={tab.on}
						onclick={() => kit.setTab(tab.assetType)}
					>
						<span class="tab-label">{tab.label}</span>
						{#if tab.hasFlags}
							<span class="tab-flags">{tab.flagLabel}</span>
						{:else}
							<span class="tab-count">{tab.count}</span>
						{/if}
					</button>
				{/each}
			</div>

			<div class="lines">
				{#each kit.lines as line (line.id)}
					<ClaimLine
						{line}
						editText={kit.editText}
						onHover={(id) => (kit.hoverLineId = id)}
						onStartEdit={(id) => kit.startEdit(id)}
						onEditText={(v) => (kit.editText = v)}
						onSaveEdit={() => kit.saveEdit()}
						onCancelEdit={() => kit.cancelEdit()}
						onEvidenceOpen={(id) => (kit.openEvidenceId = id)}
						onEvidenceToggle={(id) =>
							(kit.openEvidenceId = kit.openEvidenceId === id ? null : id)}
					/>
				{/each}
			</div>

			<div class="group-actions">
				{#if kit.group.showApprove}
					<button type="button" class="approve" onclick={() => kit.setGroupReview('approved')}>
						Approve {kit.group.shortName}
					</button>
				{/if}

				{#if kit.group.showSignoff}
					<div class="signoff">
						<button type="button" class="approve blocked" disabled aria-describedby="signoff-why">
							Requires human sign-off
						</button>
						<p class="signoff-why" id="signoff-why">
							Sensitive market: {SENSITIVE_REVIEWER} reviews this kit before anyone approves it.
						</p>
					</div>
				{/if}

				{#if kit.group.showReject}
					<button type="button" class="reject" onclick={() => kit.setGroupReview('rejected')}>
						Reject
					</button>
				{/if}

				{#if kit.group.decided}
					<div class="decided">
						<span class="decided-label" style:color={kit.group.decidedColor}>
							{kit.group.decidedLabel}
						</span>
						<button type="button" class="undo" onclick={() => kit.setGroupReview('pending')}>
							Undo
						</button>
					</div>
				{/if}
			</div>

			{#if kit.hasRequests}
				<div class="requests">
					<div class="requests-head">
						<h3 class="requests-title">Evidence requests</h3>
						<div class="requests-meta">{kit.requestMeta}</div>
					</div>
					{#each kit.requests as request (request.id)}
						<div class="request">
							<div class="request-need">{request.need}</div>
							<p class="request-why">{request.why}</p>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
</section>

<style>
	.kit-panel {
		flex: 5 1 var(--kit-basis);
		display: grid;
		gap: 40px;
		min-width: 0;
	}

	.kit-head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 24px;
		flex-wrap: wrap;
	}

	.kit-title {
		font-family: var(--serif);
		font-weight: 400;
		font-size: clamp(32px, 8vw, 46px);
		line-height: 1.05;
		letter-spacing: -0.02em;
		margin: 0;
	}

	.kit-meta {
		font-size: 15px;
		color: var(--ink-3);
	}

	.kicker {
		font-size: 12px;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--ink-3);
	}

	/* — notice — */
	.notice {
		background: var(--s1);
		padding: 26px 28px;
		display: grid;
		gap: 10px;
		max-width: 76ch;
	}

	.notice-title {
		font-family: var(--serif);
		font-weight: 400;
		font-size: clamp(20px, 5vw, 24px);
		line-height: 1.3;
		max-width: 60ch;
	}

	.notice-body {
		font-size: 16px;
		line-height: 1.6;
		color: var(--ink-2);
		max-width: 68ch;
		margin: 0;
	}

	.link-row {
		display: flex;
		gap: 14px;
		align-items: center;
		flex-wrap: wrap;
		padding-top: 10px;
	}

	.link {
		font-size: 15px;
		color: var(--ink-2);
		background: var(--s3);
		padding: 10px 13px;
	}

	.copy {
		font-family: inherit;
		font-size: 15px;
		text-align: left;
		background: transparent;
		color: var(--ink);
		border: 0;
		border-bottom: 1px solid var(--line);
		padding: 8px 0;
		cursor: pointer;
	}

	/* — refusal — */
	.refusal {
		display: grid;
		gap: 30px;
		max-width: 72ch;
	}

	.refusal-card {
		background: var(--flag-bg);
		padding: 28px 30px;
		display: grid;
		gap: 12px;
		border-left: 2px solid var(--flag-mark);
	}

	.flag-kicker {
		color: var(--flag-ink);
	}

	.refusal-title {
		font-family: var(--serif);
		font-weight: 400;
		font-size: clamp(22px, 5.5vw, 28px);
		line-height: 1.25;
		color: var(--ink);
		max-width: 44ch;
	}

	.refusal-reason {
		font-size: 16px;
		line-height: 1.6;
		color: var(--ink-2);
		margin: 0;
	}

	.fix {
		display: grid;
		gap: 10px;
	}

	.fix-body {
		font-size: 18px;
		line-height: 1.6;
		color: var(--ink);
		margin: 0;
	}

	.fix-note {
		font-size: 15px;
		color: var(--ink-3);
		margin: 0;
	}

	/* — generating — */
	.generating {
		display: grid;
		gap: 24px;
		max-width: 56ch;
	}

	.track {
		height: 2px;
		background: var(--s3);
	}

	.fill {
		height: 2px;
		background: var(--ink);
		transition: width 240ms ease-out;
	}

	.step {
		display: flex;
		gap: 18px;
		align-items: baseline;
		font-size: 16px;
		color: var(--ink);
	}

	.step-mark {
		font-size: 13px;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--ink-3);
		min-width: 78px;
	}

	.step-note {
		font-size: 15px;
		color: var(--ink-3);
		margin: 0;
	}

	/* — kit — */
	.kit-body {
		display: grid;
		gap: 40px;
	}

	.tabs {
		display: flex;
		gap: 4px;
		flex-wrap: nowrap;
		overflow-x: auto;
		padding-bottom: 2px;
	}

	.tab {
		font-family: inherit;
		font-size: 15px;
		text-align: left;
		display: flex;
		align-items: center;
		gap: 12px;
		background: var(--s1);
		color: var(--ink-2);
		border: 0;
		padding: 13px 18px;
		cursor: pointer;
		transition: background 160ms ease-out;
	}

	.tab:hover {
		background: var(--s3);
	}

	.tab.on {
		background: var(--ink);
		color: var(--bg);
	}

	.tab.on:hover {
		background: var(--ink);
	}

	.tab-label {
		white-space: nowrap;
	}

	.tab-flags {
		font-size: 13px;
		color: var(--flag-ink);
		background: var(--flag-bg);
		padding: 1px 7px;
		white-space: nowrap;
	}

	.tab-count {
		font-size: 13px;
		color: var(--ink-3);
		white-space: nowrap;
	}

	.tab.on .tab-count {
		color: inherit;
		opacity: 0.55;
	}

	.lines {
		display: grid;
		gap: 8px;
	}

	/* — group actions — */
	.group-actions {
		display: flex;
		gap: 22px;
		align-items: center;
		flex-wrap: wrap;
	}

	.approve {
		font-family: inherit;
		font-size: 16px;
		text-align: left;
		background: var(--ink);
		color: var(--bg);
		border: 0;
		padding: 14px 26px;
		cursor: pointer;
		transition: opacity 160ms ease-out;
	}

	.approve:hover {
		opacity: 0.85;
	}

	.approve.blocked {
		background: var(--s2);
		color: var(--ink);
		opacity: 0.45;
		cursor: not-allowed;
	}

	.approve.blocked:hover {
		opacity: 0.45;
	}

	.signoff {
		display: grid;
		gap: 6px;
	}

	.signoff-why {
		font-size: 14px;
		color: var(--ink-3);
		margin: 0;
	}

	.reject {
		font-family: inherit;
		font-size: 16px;
		text-align: left;
		background: transparent;
		color: var(--ink-3);
		border: 0;
		padding: 14px 0;
		cursor: pointer;
		text-decoration: underline;
		text-underline-offset: 5px;
		transition: color 160ms ease-out;
	}

	.reject:hover {
		color: var(--ink);
	}

	.decided {
		display: flex;
		gap: 20px;
		align-items: center;
		flex-wrap: wrap;
	}

	.decided-label {
		font-size: 16px;
	}

	.undo {
		font-family: inherit;
		font-size: 15px;
		text-align: left;
		background: transparent;
		color: var(--ink-3);
		border: 0;
		padding: 8px 0;
		cursor: pointer;
		text-decoration: underline;
		text-underline-offset: 5px;
	}

	/* — evidence requests — */
	.requests {
		display: grid;
		gap: 18px;
		padding-top: 28px;
		max-width: 74ch;
	}

	.requests-head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 16px;
		border-top: 2px solid var(--rule);
		padding-top: 20px;
	}

	.requests-title {
		font-family: var(--serif);
		font-weight: 400;
		font-size: 26px;
		letter-spacing: -0.01em;
		margin: 0;
	}

	.requests-meta {
		font-size: 14px;
		color: var(--ink-3);
	}

	.request {
		display: grid;
		gap: 7px;
		background: var(--s1);
		padding: 20px 22px;
	}

	.request-need {
		font-size: 17px;
		color: var(--ink);
	}

	.request-why {
		font-size: 15px;
		line-height: 1.6;
		color: var(--ink-2);
		margin: 0;
	}
</style>
