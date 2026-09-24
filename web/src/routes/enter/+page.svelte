<script lang="ts">
	import { enhance } from '$app/forms';
	import type { ActionData, PageData } from './$types';

	let { data, form }: { data: PageData; form: ActionData } = $props();

	let submitting = $state(false);
</script>

<svelte:head>
	<title>Relative — enter</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="shell">
	<div class="card">
		<h1>relative</h1>
		<p class="blurb">
			This demo is still in testing, so it is behind a password for now. If you were sent one,
			enter it below.
		</p>

		<form
			method="POST"
			use:enhance={() => {
				submitting = true;
				return async ({ update }) => {
					await update();
					submitting = false;
				};
			}}
		>
			<input type="hidden" name="next" value={form?.next ?? data.next} />

			<label class="kicker" for="password">PASSWORD</label>
			<!-- svelte-ignore a11y_autofocus -->
			<input
				id="password"
				name="password"
				type="password"
				autocomplete="current-password"
				autofocus
				aria-describedby={form?.message ? 'gate-error' : undefined}
			/>

			{#if form?.message}
				<p class="error" id="gate-error" role="alert">{form.message}</p>
			{/if}

			<button type="submit" disabled={submitting}>
				{submitting ? 'Checking…' : 'Enter'}
			</button>
		</form>
	</div>
</div>

<style>
	.shell {
		background: var(--bg);
		color: var(--ink);
		font-family: var(--sans);
		font-size: 17px;
		line-height: 1.5;
		min-height: 100vh;
		display: grid;
		place-items: center;
		padding: 24px;
		box-sizing: border-box;
	}

	.card {
		width: 100%;
		max-width: 360px;
	}

	h1 {
		font-family: var(--serif);
		font-size: 34px;
		font-weight: 400;
		letter-spacing: -0.01em;
		margin: 0;
	}

	.blurb {
		color: var(--ink-2);
		font-size: 15px;
		margin: 10px 0 28px;
	}

	form {
		display: grid;
		gap: 10px;
	}

	.kicker {
		font-size: 12px;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--ink-3);
	}

	input[type='password'] {
		font-family: inherit;
		font-size: 16px;
		color: var(--ink);
		background: var(--s1);
		border: 0;
		padding: 13px 14px;
		width: 100%;
		box-sizing: border-box;
	}

	.error {
		color: var(--flag-ink);
		background: var(--flag-bg);
		font-size: 14px;
		padding: 10px 12px;
		margin: 0;
	}

	button {
		font-family: inherit;
		font-size: 17px;
		text-align: left;
		background: var(--accent);
		color: var(--accent-ink);
		border: 0;
		padding: 17px 18px;
		width: 100%;
		cursor: pointer;
		margin-top: 8px;
		transition: background 160ms ease-out;
	}

	button:hover {
		background: var(--accent-press);
	}

	button:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	button:disabled:hover {
		background: var(--accent);
	}
</style>
