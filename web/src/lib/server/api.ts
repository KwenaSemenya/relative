import { env } from '$env/dynamic/private';
import type { Kit, Narrative } from '$lib/types';

/**
 * Talks to the FastAPI service. Server-only: in production the API listens on
 * Fly's private network and is not reachable from a browser, which is why
 * every call goes through a SvelteKit load function or action.
 */

const BASE = env.RELATIVE_API_URL ?? 'http://localhost:8099';

export class ApiError extends Error {
	constructor(
		readonly status: number,
		message: string
	) {
		super(message);
	}
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
	const response = await fetch(`${BASE}${path}`, {
		...init,
		headers: { 'content-type': 'application/json', ...init?.headers },
		signal: AbortSignal.timeout(10_000)
	});

	if (!response.ok) {
		const detail = await response
			.json()
			.then((b) => b?.detail)
			.catch(() => null);
		throw new ApiError(response.status, detail ?? `Request failed (${response.status}).`);
	}

	return response.json() as Promise<T>;
}

export const getNarrative = () => call<Narrative>('/narrative');

export const getKit = (slug: string) => call<Kit>(`/kits/${encodeURIComponent(slug)}`);

export const reviewGroup = (slug: string, assetType: string, reviewState: string) =>
	call<Kit>(`/kits/${encodeURIComponent(slug)}/groups/${assetType}/review`, {
		method: 'POST',
		body: JSON.stringify({ reviewState })
	});

export const editClaim = (slug: string, claimId: string, body: string) =>
	call<Kit>(`/kits/${encodeURIComponent(slug)}/claims/${encodeURIComponent(claimId)}`, {
		method: 'POST',
		body: JSON.stringify({ body })
	});
