/**
 * A shared password in front of the whole site, for the field-test window.
 *
 * This is not the product's access control and has nothing to do with kits:
 * inside the app a kit link is still the only thing that opens a kit. This is a
 * lock on the front door of a demo that is not ready for the open internet yet,
 * and removing it is a matter of clearing one environment variable.
 *
 * Unset `RELATIVE_ACCESS_PASSWORD` and the gate disappears entirely, which is
 * how this comes off when the demo goes public.
 */
import { createHash, timingSafeEqual } from 'node:crypto';

export const COOKIE = 'relative_access';

/** Thirty days. Long enough that a tester signs in once for the whole test. */
export const MAX_AGE = 60 * 60 * 24 * 30;

/**
 * What the cookie holds. A hash rather than the password itself, so a cookie
 * read off a shared machine does not hand over the word that opens every other
 * session. Changing the password invalidates every cookie already issued,
 * which is the behaviour you want from the only lock there is.
 */
export function token(password: string): string {
	return createHash('sha256').update(`relative:${password}`).digest('hex');
}

/** Compared in constant time, so a wrong guess takes as long as a right one. */
export function matches(held: string, expected: string): boolean {
	const a = Buffer.from(held);
	const b = Buffer.from(expected);
	return a.length === b.length && timingSafeEqual(a, b);
}

/**
 * Where to send someone after they sign in.
 *
 * Only ever a path on this site. The destination arrives in a query parameter,
 * so without this an emailed link could park somebody else's URL there and use
 * our sign-in page to launch it.
 */
export function safeNext(raw: string | null): string {
	if (!raw || !raw.startsWith('/') || raw.startsWith('//')) return '/';
	return raw;
}
