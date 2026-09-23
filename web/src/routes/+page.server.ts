import { fail } from '@sveltejs/kit';
import { EXAMPLE_SLUG } from '$lib/data/example-kit';
import { ApiError, createKit, getKit, getNarrative } from '$lib/server/api';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
	// The landing page is the worked example, read through the same path as any
	// other kit. If the API is unreachable the page still renders from the
	// bundled fixture rather than showing nothing; Phase 7 makes that visible
	// to the reader.
	try {
		const [kit, narrative] = await Promise.all([getKit(EXAMPLE_SLUG), getNarrative()]);
		return { kit, narrative };
	} catch {
		return { kit: null, narrative: null };
	}
};

export const actions: Actions = {
	generate: async ({ request, getClientAddress }) => {
		const form = await request.formData();
		const brief = String(form.get('brief') ?? '').trim();
		const audience = String(form.get('audience') ?? 'Educators');
		const sensitiveMarket = form.get('sensitiveMarket') === 'true';
		const proofPoints = form
			.getAll('proofPoint')
			.map((p) => String(p).trim())
			.filter(Boolean);

		if (!brief) {
			return fail(422, { message: 'Write a brief first.' });
		}

		try {
			const result = await createKit(
				{ brief, audience, proofPoints, sensitiveMarket },
				getClientAddress()
			);

			// A refusal is a real answer, not a failure: the brief was read and
			// the honest outcome was to write nothing. The page keeps every input.
			if (result.refusal) {
				return { refusal: result.refusal };
			}

			// A limit is not a failure either. The demo had nothing left to spend,
			// which is a fact about the demo rather than about the brief, so it is
			// said plainly and the worked example stays on screen.
			if (result.limit) {
				return { limit: result.limit };
			}

			return { kit: result.kit };
		} catch (e) {
			return fail(502, {
				message:
					e instanceof ApiError
						? e.message
						: 'The brief could not be checked just now. Nothing you typed was lost.'
			});
		}
	}
};
