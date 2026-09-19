import type { AssetGroup, EvidenceRequest, Kit, ProofPoint } from '$lib/types';

/**
 * The worked example kit, transcribed from the design file. It carries the two
 * seeded flagged lines (a never-say violation in talking points, an unsupported
 * reading-scores claim in social) and the one evidence request they produce.
 *
 * Phase 2 moves this into Postgres as a seeded row. Until then it is the
 * fixture the landing route renders.
 */

export const EXAMPLE_SLUG = 'emea-spring-2f41';

export const EXAMPLE_PROOF_POINTS: ProofPoint[] = [
	{ id: 'pp_hardware', text: 'Hardware audit, 14 districts, 2025 — devices already in classrooms' },
	{ id: 'pp_ridgeway', text: 'Ridgeway pilot, 2025 — teacher prep time, six schools' }
];

/** What the brief panel's proof point inputs are pre-filled with. */
export const EXAMPLE_PROOF_INPUTS = [
	'Hardware audit, 14 districts, 2025',
	'Ridgeway pilot, 2025 — prep time',
	''
];

export const EXAMPLE_BRIEF =
	'Spring enrolment push for district curriculum leads. Lead on cost and teacher control.';

export function exampleGroups(): AssetGroup[] {
	return [
		{
			assetType: 'talking_point',
			title: 'Talking points',
			shortName: 'talking points',
			reviewState: 'pending',
			claims: [
				{
					id: 't1',
					assetType: 'talking_point',
					body: 'Kestrel runs on the laptops your district already owns. There is no new hardware line in the budget.',
					pillarId: 'pillar3',
					evidence: { kind: 'proof_point', id: 'pp_hardware' },
					flagState: 'clean',
					flagReason: null,
					editedAt: null
				},
				{
					id: 't2',
					assetType: 'talking_point',
					body: 'Teachers set the pace. Kestrel drafts the material and the teacher approves it before a class sees it.',
					pillarId: 'pillar1',
					evidence: { kind: 'pillar', id: 'pillar1' },
					flagState: 'clean',
					flagReason: null,
					editedAt: null
				},
				{
					id: 't3',
					assetType: 'talking_point',
					body: 'Schools in the Ridgeway pilot saved about four hours of lesson prep a week.',
					pillarId: 'pillar2',
					evidence: { kind: 'proof_point', id: 'pp_ridgeway' },
					flagState: 'clean',
					flagReason: null,
					editedAt: null
				},
				{
					id: 't4',
					assetType: 'talking_point',
					body: 'Kestrel takes the lesson prep off your hands, so a school can run the same timetable with fewer teaching assistants.',
					pillarId: 'pillar1',
					evidence: null,
					flagState: 'flagged',
					flagReason:
						'This breaks a never-say rule: it tells a school it can cut staff. Pillar 1 says Kestrel drafts and a person approves, so nothing we write may suggest it replaces someone.',
					editedAt: null
				}
			]
		},
		{
			assetType: 'social',
			title: 'Social',
			shortName: 'social copy',
			reviewState: 'pending',
			claims: [
				{
					id: 's1',
					assetType: 'social',
					body: 'Same laptops. Same teachers. Four fewer hours of prep each week.',
					pillarId: 'pillar2',
					evidence: { kind: 'proof_point', id: 'pp_ridgeway' },
					flagState: 'clean',
					flagReason: null,
					editedAt: null
				},
				{
					id: 's2',
					assetType: 'social',
					body: 'Kestrel lifts reading scores in a single term.',
					pillarId: 'pillar2',
					evidence: null,
					flagState: 'flagged',
					flagReason:
						'This claims a learning outcome we have no evidence for. Nothing in the narrative measures reading scores, and the Ridgeway pilot only measured teacher prep time.',
					editedAt: null
				}
			]
		},
		{
			assetType: 'faq',
			title: 'FAQ',
			shortName: 'the FAQ',
			reviewState: 'pending',
			claims: [
				{
					id: 'f1',
					assetType: 'faq',
					body: 'Does Kestrel replace teaching staff? No. A teacher approves everything a class sees.',
					pillarId: 'pillar1',
					evidence: { kind: 'pillar', id: 'pillar1' },
					flagState: 'clean',
					flagReason: null,
					editedAt: null
				},
				{
					id: 'f2',
					assetType: 'faq',
					body: 'What does it cost? One price for the whole school, however many pupils use it.',
					pillarId: 'pillar4',
					evidence: { kind: 'pillar', id: 'pillar4' },
					flagState: 'clean',
					flagReason: null,
					editedAt: null
				},
				{
					id: 'f3',
					assetType: 'faq',
					body: 'What does it save? Time. Teachers in the Ridgeway pilot reported about four hours less prep a week.',
					pillarId: 'pillar2',
					evidence: { kind: 'proof_point', id: 'pp_ridgeway' },
					flagState: 'clean',
					flagReason: null,
					editedAt: null
				}
			]
		}
	];
}

export const EXAMPLE_REQUESTS: EvidenceRequest[] = [
	{
		id: 'er1',
		need: 'A study that measures reading outcomes',
		why: 'Social line 2 claims a score gain. Send a study that measures reading, or the line gets cut before the kit ships.'
	}
];

export function exampleKit(): Kit {
	return {
		slug: EXAMPLE_SLUG,
		brief: EXAMPLE_BRIEF,
		audience: 'Educators',
		sensitiveMarket: false,
		createdAt: '2026-09-12T09:00:00Z',
		proofPoints: EXAMPLE_PROOF_POINTS,
		groups: exampleGroups(),
		evidenceRequests: EXAMPLE_REQUESTS
	};
}
