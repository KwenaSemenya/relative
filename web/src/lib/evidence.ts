import type { AssetGroup, Claim, EvidenceRef, Pillar, ProofPoint } from '$lib/types';

export interface ResolvedEvidence {
	/** The number shown in the marker chip and the popover heading. */
	number: string;
	/** The line of text shown inside the popover. */
	label: string;
}

/**
 * Evidence sources are numbered once per kit so a marker means the same thing
 * everywhere: proof points first in the order the user entered them, then any
 * pillars a claim cites, in pillar order.
 */
export function buildEvidenceIndex(
	proofPoints: ProofPoint[],
	pillars: Pillar[],
	groups: AssetGroup[]
): Map<string, ResolvedEvidence> {
	const index = new Map<string, ResolvedEvidence>();
	let n = 0;

	for (const pp of proofPoints) {
		n += 1;
		index.set(`proof_point:${pp.id}`, { number: String(n), label: pp.text });
	}

	const citedPillars = new Set<string>();
	for (const group of groups) {
		for (const claim of group.claims) {
			if (claim.evidence?.kind === 'pillar') citedPillars.add(claim.evidence.id);
		}
	}

	pillars.forEach((pillar, i) => {
		if (!citedPillars.has(pillar.id)) return;
		n += 1;
		const title = pillar.title.charAt(0).toLowerCase() + pillar.title.slice(1);
		index.set(`pillar:${pillar.id}`, {
			number: String(n),
			label: `Pillar ${i + 1} — ${title}`
		});
	});

	return index;
}

export function evidenceKey(ref: EvidenceRef): string | null {
	return ref ? `${ref.kind}:${ref.id}` : null;
}

/**
 * A re-checked line keeps its source number but says so, so the reviewer can
 * tell a freshly verified line from one that was never touched.
 */
export function resolveEvidence(
	claim: Claim,
	index: Map<string, ResolvedEvidence>
): ResolvedEvidence | null {
	const key = evidenceKey(claim.evidence);
	if (!key) return null;
	const found = index.get(key);
	if (!found) return null;
	if (!claim.editedAt) return found;
	const head = found.label.split(' — ')[0];
	return { number: found.number, label: `${head} — re-checked after your edit` };
}
