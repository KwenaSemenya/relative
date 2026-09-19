export type AssetType = 'talking_point' | 'social' | 'faq';
export type ReviewState = 'pending' | 'approved' | 'rejected';
export type FlagState = 'clean' | 'flagged';

/** HQ-owned and read-only. Seeded, never edited in the product. */
export interface Pillar {
	id: string;
	title: string;
	body: string;
}

export interface Narrative {
	pillars: Pillar[];
	neverSay: string[];
}

/** Evidence entered by the user for one kit. */
export interface ProofPoint {
	id: string;
	text: string;
}

/**
 * A claim cites exactly one evidence source. Usually a proof point; for claims
 * that restate approved positioning rather than assert a fact, the pillar is
 * the source. Flagged claims cite nothing — that is why they are flagged.
 */
export type EvidenceRef =
	| { kind: 'proof_point'; id: string }
	| { kind: 'pillar'; id: string }
	| null;

export interface Claim {
	id: string;
	assetType: AssetType;
	body: string;
	/** Which pillar this claim is meant to serve. Always recorded. */
	pillarId: string | null;
	evidence: EvidenceRef;
	flagState: FlagState;
	flagReason: string | null;
	editedAt: string | null;
}

/** A claim the model wanted to make but no proof point could support. */
export interface EvidenceRequest {
	id: string;
	need: string;
	why: string;
}

/** Claims are reviewed in groups of one asset type. */
export interface AssetGroup {
	assetType: AssetType;
	title: string;
	/** Used in "Approve talking points". */
	shortName: string;
	reviewState: ReviewState;
	claims: Claim[];
}

export interface Kit {
	slug: string;
	brief: string;
	audience: string;
	sensitiveMarket: boolean;
	createdAt: string;
	proofPoints: ProofPoint[];
	groups: AssetGroup[];
	evidenceRequests: EvidenceRequest[];
}

export const AUDIENCES = ['Educators', 'Students', 'Institutions', 'Influencers'] as const;
export type Audience = (typeof AUDIENCES)[number];
