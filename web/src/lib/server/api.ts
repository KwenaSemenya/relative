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
		// The signal is spread last so a caller can extend the deadline; calls
		// that wait on Claude need far longer than a database read.
		signal: AbortSignal.timeout(10_000),
		...init,
		headers: { 'content-type': 'application/json', ...init?.headers }
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

/** A refusal is a successful call that produced no kit, on purpose. */
export interface CreateKitResult {
	kit: Kit | null;
	refusal: { reason: string; fix: string } | null;
}

export const createKit = (input: {
	brief: string;
	audience: string;
	proofPoints: string[];
	sensitiveMarket: boolean;
}) =>
	call<CreateKitResult>('/kits', {
		method: 'POST',
		body: JSON.stringify(input),
		// Pre-flight validation is a Claude call, so this outlives the default.
		signal: AbortSignal.timeout(45_000)
	});

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
