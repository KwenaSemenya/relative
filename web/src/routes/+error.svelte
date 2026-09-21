<script lang="ts">
	import { page } from '$app/state';

	// A wrong link is the most likely way to land here, so the page names that
	// plainly and gives one obvious way forward rather than an error code alone.
	const isMissing = $derived(page.status === 404);

	const title = $derived(
		isMissing ? 'No kit at that link.' : 'That did not load.'
	);

	const body = $derived(
		isMissing
			? 'The link may be mistyped, or the kit may have been removed. Links are long on purpose, so check it copied in full.'
			: (page.error?.message ?? 'Something went wrong at our end. Nothing you did caused it.')
	);
</script>

<svelte:head>
	<title>{title} — Relative</title>
</svelte:head>

<div class="shell">
	<div class="card">
		<div class="kicker">{page.status}</div>
		<h1>{title}</h1>
		<p>{body}</p>
		<a href="/">Go to the worked example</a>
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
		padding: clamp(20px, 4vw, 36px) clamp(16px, 3.5vw, 44px);
		box-sizing: border-box;
		display: grid;
		place-items: center;
	}

	.card {
		display: grid;
		gap: 14px;
		max-width: 52ch;
	}

	.kicker {
		font-size: 12px;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--ink-3);
	}

	h1 {
		font-family: var(--serif);
		font-weight: 400;
		font-size: clamp(30px, 7vw, 42px);
		line-height: 1.1;
		letter-spacing: -0.02em;
		margin: 0;
	}

	p {
		font-size: 17px;
		line-height: 1.6;
		color: var(--ink-2);
		margin: 0;
	}

	a {
		font-size: 16px;
		color: var(--ink);
		justify-self: start;
		padding: 10px 0;
		text-underline-offset: 5px;
	}
</style>
