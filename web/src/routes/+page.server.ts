import { EXAMPLE_SLUG } from '$lib/data/example-kit';
import { getKit, getNarrative } from '$lib/server/api';
import type { PageServerLoad } from './$types';

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
