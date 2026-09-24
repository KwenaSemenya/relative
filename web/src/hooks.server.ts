import { redirect, type Handle } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import { COOKIE, matches, token } from '$lib/server/gate';

/**
 * Holds the door for everything except the sign-in page itself.
 *
 * Read from the environment on every request rather than at import time, so
 * lifting the gate is a secret change and a restart, not a redeploy.
 */
export const handle: Handle = async ({ event, resolve }) => {
	const password = env.RELATIVE_ACCESS_PASSWORD;

	// No password configured means no gate. That is the open state the demo
	// ends up in, and it is the default so local development is never blocked.
	if (!password) return resolve(event);

	if (event.url.pathname === '/enter') return resolve(event);

	if (!matches(event.cookies.get(COOKIE) ?? '', token(password))) {
		// Carry where they were headed, so a shared kit link still lands on the
		// kit after signing in rather than dumping them on the front page.
		const next = event.url.pathname + event.url.search;
		redirect(303, `/enter?next=${encodeURIComponent(next)}`);
	}

	return resolve(event);
};
