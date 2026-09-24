import { error, fail, redirect } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import { dev } from '$app/environment';
import { COOKIE, MAX_AGE, matches, safeNext, token } from '$lib/server/gate';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ url }) => {
	// With no password configured there is no door here to knock on, and a
	// sign-in page for a site that is not locked would be a puzzle.
	if (!env.RELATIVE_ACCESS_PASSWORD) redirect(303, safeNext(url.searchParams.get('next')));
	return { next: safeNext(url.searchParams.get('next')) };
};

export const actions: Actions = {
	default: async ({ request, cookies, url }) => {
		const password = env.RELATIVE_ACCESS_PASSWORD;
		if (!password) error(404, 'Not found.');

		const form = await request.formData();
		const given = String(form.get('password') ?? '');
		const next = safeNext(String(form.get('next') ?? '') || null);

		if (!given) {
			return fail(422, { message: 'Enter the password you were sent.', next });
		}

		if (!matches(token(given), token(password))) {
			// Deliberately says nothing about the password itself. There is one
			// word and one guesser, and "close" would be a hint.
			return fail(401, { message: 'That password is not right. Check it and try again.', next });
		}

		cookies.set(COOKIE, token(password), {
			path: '/',
			httpOnly: true,
			sameSite: 'lax',
			secure: !dev,
			maxAge: MAX_AGE
		});

		redirect(303, next);
	}
};
