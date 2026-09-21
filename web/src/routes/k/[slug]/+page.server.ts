import { error, fail } from '@sveltejs/kit';
import { ApiError, editClaim, getKit, getNarrative, reviewGroup } from '$lib/server/api';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params }) => {
	try {
		const [kit, narrative] = await Promise.all([getKit(params.slug), getNarrative()]);
		return { kit, narrative };
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) {
			error(404, 'No kit at that link.');
		}
		error(503, 'The kit could not be loaded just now.');
	}
};

export const actions: Actions = {
	review: async ({ params, request }) => {
		const form = await request.formData();
		const assetType = String(form.get('assetType') ?? '');
		const reviewState = String(form.get('reviewState') ?? '');

		try {
			return { kit: await reviewGroup(params.slug, assetType, reviewState) };
		} catch (e) {
			// The decision did not save, so the page keeps showing the real state
			// rather than a decision that only exists in the browser.
			return fail(502, {
				message:
					e instanceof ApiError ? e.message : 'That decision did not save. Try again.'
			});
		}
	},

	edit: async ({ params, request }) => {
		const form = await request.formData();
		const claimId = String(form.get('claimId') ?? '');
		const body = String(form.get('body') ?? '').trim();

		if (!body) {
			return fail(422, { message: 'A line cannot be empty.', claimId, body });
		}

		try {
			return { kit: await editClaim(params.slug, claimId, body) };
		} catch (e) {
			// The user's wording is handed back so an API failure never loses it.
			return fail(502, {
				message: e instanceof ApiError ? e.message : 'That edit did not save. Try again.',
				claimId,
				body
			});
		}
	}
};
