import type { Narrative } from '$lib/types';

/**
 * The Kestrel Learn narrative. HQ owns this; the product never edits it.
 * Content is transcribed verbatim from the design file.
 */
export const NARRATIVE: Narrative = {
	pillars: [
		{
			id: 'pillar1',
			title: 'Teachers stay in charge',
			body: 'Kestrel drafts; a teacher approves anything a class sees.'
		},
		{
			id: 'pillar2',
			title: 'Evidence before claims',
			body: 'Every outcome we state comes from a named study or a named district.'
		},
		{
			id: 'pillar3',
			title: 'Runs on what schools already own',
			body: 'No new hardware, no new procurement round.'
		},
		{
			id: 'pillar4',
			title: 'One price per school',
			body: 'Priced per school, never per pupil.'
		}
	],
	neverSay: [
		'Guaranteed results',
		'Replaces teachers',
		'Raises test scores by X%',
		'The only platform that…',
		'Pays for itself'
	]
};

export const NARRATIVE_LABEL = 'Kestrel Learn, FY26';

/** Named human who signs off kits aimed at a sensitive market. */
export const SENSITIVE_REVIEWER = 'Priya Raman';
