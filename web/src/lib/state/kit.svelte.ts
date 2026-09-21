import { NARRATIVE } from '$lib/data/narrative';
import {
	EXAMPLE_BRIEF,
	EXAMPLE_PROOF_INPUTS,
	EXAMPLE_PROOF_POINTS,
	EXAMPLE_REQUESTS,
	EXAMPLE_SLUG,
	exampleGroups
} from '$lib/data/example-kit';
import { buildEvidenceIndex, resolveEvidence } from '$lib/evidence';
import type {
	AssetGroup,
	AssetType,
	EvidenceRequest,
	Kit,
	Narrative,
	ProofPoint,
	ReviewState
} from '$lib/types';

export type View = 'kit' | 'refusal' | 'generating';

export type DemoState =
	| 'landing'
	| 'refusal'
	| 'generating'
	| 'edited'
	| 'sensitive'
	| 'budget'
	| 'partial'
	| 'complete';

export const DEMO_STATES: { id: DemoState; label: string }[] = [
	{ id: 'landing', label: '1 Landing' },
	{ id: 'refusal', label: '2 Refusal' },
	{ id: 'generating', label: '3 Generating' },
	{ id: 'edited', label: '4 Edited line' },
	{ id: 'sensitive', label: '5 Sensitive' },
	{ id: 'budget', label: '6 Budget spent' },
	{ id: 'partial', label: '7 Partial' },
	{ id: 'complete', label: '8 Complete' }
];

export const GENERATION_STEPS = [
	'Reading the brief',
	'Checking your proof points against the narrative',
	'Drafting the kit',
	'Checking each line, one at a time'
];

const REFUSAL_BRIEF = 'Spring enrolment push. Lead with guaranteed reading score gains in one term.';

export const REFUSAL_REASON =
	'Your brief asks for guaranteed reading score gains in one term. The proof point you supplied, the Ridgeway pilot, measured teacher prep time and did not measure reading. "Guaranteed results" is also on the never-say list.';

export const REFUSAL_FIX =
	'Drop the score claim from the brief, or add a proof point that measured reading outcomes. Then generate again.';

/** How a live kit writes changes back. Supplied by the /k/<slug> page. */
export interface Persist {
	review(assetType: AssetType, reviewState: ReviewState): Promise<Kit>;
	edit(claimId: string, body: string): Promise<Kit>;
}

export interface KitStateOptions {
	/** The kit to show. Comes from the database; falls back to the fixture. */
	kit?: Kit;
	narrative?: Narrative;
	/**
	 * A real saved kit opened at /k/<slug>. Review decisions and edits are
	 * persisted, and the demo state switcher is not shown.
	 */
	live?: boolean;
	persist?: Persist;
}

export class KitState {
	mode = $state<'light' | 'dark'>('light');
	narrativeOpen = $state(false);

	brief = $state(EXAMPLE_BRIEF);
	audience = $state('Educators');
	proofInputs = $state<string[]>([...EXAMPLE_PROOF_INPUTS]);
	sensitive = $state(false);

	view = $state<View>('kit');
	demo = $state<DemoState>('landing');
	tab = $state<AssetType>('talking_point');

	groups = $state<AssetGroup[]>(exampleGroups());
	requests = $state<EvidenceRequest[]>([...EXAMPLE_REQUESTS]);

	/** Set while a change is in flight, and cleared when the server answers. */
	saving = $state(false);
	/** Plain-language failure, shown without losing what the user typed. */
	actionError = $state<string | null>(null);

	readonly live: boolean;
	readonly slug: string;
	#narrative: Narrative;
	#proofPoints: ProofPoint[];
	#baseline: Kit | null;
	#persist: Persist | null;

	constructor(options: KitStateOptions = {}) {
		const { kit, narrative, live = false, persist } = options;

		this.live = live;
		this.#persist = persist ?? null;
		this.slug = kit?.slug ?? EXAMPLE_SLUG;
		this.#narrative = narrative ?? NARRATIVE;
		this.#proofPoints = kit?.proofPoints ?? EXAMPLE_PROOF_POINTS;
		this.#baseline = kit ?? null;

		if (kit) {
			this.brief = kit.brief;
			this.audience = kit.audience;
			this.sensitive = kit.sensitiveMarket;
			this.groups = structuredClone(kit.groups);
			this.requests = structuredClone(kit.evidenceRequests);
			this.tab = this.groups[0]?.assetType ?? 'talking_point';
			if (!live) {
				this.proofInputs = [...kit.proofPoints.map((p) => p.text), '', ''].slice(0, 3);
			}
		}
	}

	/** The kit as the database has it, used to reset the demo switcher. */
	#freshGroups(): AssetGroup[] {
		return this.#baseline ? structuredClone(this.#baseline.groups) : exampleGroups();
	}

	#freshRequests(): EvidenceRequest[] {
		return this.#baseline
			? structuredClone(this.#baseline.evidenceRequests)
			: [...EXAMPLE_REQUESTS];
	}

	editingId = $state<string | null>(null);
	editText = $state('');
	checkingId = $state<string | null>(null);
	justCheckedId = $state<string | null>(null);
	openEvidenceId = $state<string | null>(null);
	hoverLineId = $state<string | null>(null);

	step = $state(0);
	copied = $state(false);

	#timers: ReturnType<typeof setTimeout>[] = [];

	// ── derived ──────────────────────────────────────────────────────────────

	get isDark() {
		return this.mode === 'dark';
	}

	get modeLabel() {
		return this.isDark ? 'Switch to light mode' : 'Switch to dark mode';
	}

	get budgetSpent() {
		return this.demo === 'budget';
	}

	get generating() {
		return this.view === 'generating';
	}

	get activeGroup(): AssetGroup {
		return this.groups.find((g) => g.assetType === this.tab) ?? this.groups[0];
	}

	get decidedCount() {
		return this.groups.filter((g) => g.reviewState !== 'pending').length;
	}

	get allApproved() {
		return this.groups.every((g) => g.reviewState === 'approved');
	}

	get evidenceIndex() {
		return buildEvidenceIndex(this.#proofPoints, this.#narrative.pillars, this.groups);
	}

	get filledProofCount() {
		return this.proofInputs.filter((p) => p.trim().length > 2).length;
	}

	get canGenerate() {
		return !this.generating && !this.budgetSpent && this.filledProofCount >= 2;
	}

	get generateLabel() {
		return this.generating ? 'Generating…' : 'Generate kit';
	}

	/** Every disabled action says why it is disabled. */
	get generateBlockedWhy() {
		if (this.budgetSpent) return 'Demo generations are used up for today.';
		if (this.generating) return '';
		return 'Add at least two proof points first.';
	}

	get kitTitle() {
		return this.view === 'refusal' ? 'No kit yet' : 'Kit';
	}

	get kitMeta() {
		if (this.generating) return 'Working';
		if (this.view === 'refusal') return 'Nothing was written';
		const progress = this.allApproved ? '3 of 3 approved' : `${this.decidedCount} of 3 decided`;
		return `${this.audience} · ${progress}`;
	}

	get progressWidth() {
		return `${Math.round((this.step / GENERATION_STEPS.length) * 100)}%`;
	}

	get generationCount() {
		return this.step >= GENERATION_STEPS.length
			? 'Eight lines drafted, eight checked.'
			: 'Usually takes about four seconds.';
	}

	get steps() {
		return GENERATION_STEPS.map((label, i) => ({
			label,
			mark: this.step > i + 1 ? 'done' : this.step === i + 1 ? 'running' : 'waiting'
		}));
	}

	get tabs() {
		return this.groups.map((g) => {
			const flags = g.claims.filter((c) => c.flagState === 'flagged').length;
			return {
				assetType: g.assetType,
				label: g.title,
				on: g.assetType === this.tab,
				hasFlags: flags > 0,
				flagLabel: `${flags} flagged`,
				count: `${g.claims.length} lines`
			};
		});
	}

	get lines() {
		const index = this.evidenceIndex;
		return this.activeGroup.claims.map((claim) => {
			const editing = this.editingId === claim.id;
			const checking = this.checkingId === claim.id;
			const resolved = resolveEvidence(claim, index);
			return {
				id: claim.id,
				text: claim.body,
				reason: claim.flagReason,
				evidence: resolved?.label ?? '',
				sourceNo: resolved?.number ?? '',
				editing,
				checking,
				flagged: claim.flagState === 'flagged' && !editing && !checking,
				showMarker: !!resolved && !checking && !editing,
				justChecked: this.justCheckedId === claim.id,
				canEdit: this.activeGroup.reviewState === 'pending' && !editing && !checking,
				editRevealed: this.hoverLineId === claim.id,
				evidenceOpen: this.openEvidenceId === claim.id
			};
		});
	}

	get group() {
		const active = this.activeGroup;
		const pending = active.reviewState === 'pending';
		return {
			shortName: active.shortName,
			showApprove: pending && !this.sensitive,
			showSignoff: pending && this.sensitive,
			showReject: pending,
			decided: !pending,
			decidedLabel:
				active.reviewState === 'approved' ? 'Approved by you' : 'Rejected — not going out',
			decidedColor: active.reviewState === 'approved' ? 'var(--ok-ink)' : 'var(--ink-3)'
		};
	}

	get notice() {
		if (this.budgetSpent) {
			return {
				kicker: 'Demo limit',
				title: 'You have used all five demo generations for today.',
				body: 'The kit below is the worked example, not yours. Your brief and proof points are saved — generate again tomorrow.',
				hasLink: false,
				link: ''
			};
		}
		if (this.allApproved && this.view === 'kit') {
			return {
				kicker: 'Done',
				title: 'All three groups approved. The kit is locked and ready for HQ.',
				body: 'Nothing else is needed from you. HQ sees the approved lines, the proof point behind each one, and your edits.',
				hasLink: true,
				link: this.shareLink
			};
		}
		if (!this.live && this.demo === 'landing' && this.decidedCount === 0 && !this.justCheckedId) {
			return {
				kicker: 'Worked example',
				title: "This is last week's kit, kept here so you can see what comes back.",
				body: 'Two lines are flagged and one needs evidence. Write your own brief on the left and generate to replace it.',
				hasLink: false,
				link: ''
			};
		}
		return null;
	}

	get showNotice() {
		return !!this.notice && this.view !== 'generating';
	}

	get hasRequests() {
		return this.requests.length > 0 && this.view === 'kit';
	}

	get requestMeta() {
		return this.requests.length === 1 ? '1 gap' : `${this.requests.length} gaps`;
	}

	get copyLabel() {
		return this.copied ? 'Link copied' : 'Copy link';
	}

	/** The approved narrative, as seeded by HQ. Read-only in the product. */
	get narrative() {
		return this.#narrative;
	}

	/** The real, openable link to this kit. The link is the access control. */
	get shareLink() {
		const origin = typeof location === 'undefined' ? '' : location.origin;
		return `${origin}/k/${this.slug}`.replace(/^https?:\/\//, '');
	}

	// ── actions ──────────────────────────────────────────────────────────────

	#later(fn: () => void, ms: number) {
		this.#timers.push(setTimeout(fn, ms));
	}

	#clearTimers() {
		this.#timers.forEach(clearTimeout);
		this.#timers = [];
	}

	destroy() {
		this.#clearTimers();
	}

	initMode() {
		const attr = document.documentElement.getAttribute('data-mode');
		this.mode = attr === 'dark' ? 'dark' : 'light';
	}

	toggleMode() {
		const next = this.isDark ? 'light' : 'dark';
		this.mode = next;
		document.documentElement.setAttribute('data-mode', next);
		try {
			localStorage.setItem('relative.mode', next);
		} catch {
			// Private browsing blocks writes. The toggle still works for this visit.
		}
	}

	setDemo(name: DemoState) {
		this.#clearTimers();

		this.demo = name;
		this.editingId = null;
		this.checkingId = null;
		this.justCheckedId = null;
		this.openEvidenceId = null;
		this.copied = false;
		this.step = 0;
		this.groups = this.#freshGroups();
		this.requests = this.#freshRequests();
		this.view = 'kit';
		this.sensitive = false;
		this.tab = 'talking_point';
		this.brief = this.#baseline?.brief ?? EXAMPLE_BRIEF;

		if (name === 'refusal') {
			this.view = 'refusal';
			this.brief = REFUSAL_BRIEF;
		}

		if (name === 'generating') {
			this.view = 'generating';
			this.runProgress();
		}

		if (name === 'edited') {
			const social = this.groups[1];
			social.claims[1] = {
				...social.claims[1],
				body: 'Teachers in the Ridgeway pilot got four hours a week back. What they do with them is up to them.',
				evidence: { kind: 'proof_point', id: 'pp_ridgeway' },
				flagState: 'clean',
				flagReason: null,
				editedAt: new Date().toISOString()
			};
			this.justCheckedId = 's2';
			this.requests = [];
			this.tab = 'social';
		}

		if (name === 'sensitive') this.sensitive = true;

		if (name === 'partial') {
			this.groups[0].reviewState = 'approved';
			this.tab = 'social';
		}

		if (name === 'complete') {
			const social = this.groups[1];
			social.claims[1] = {
				...social.claims[1],
				body: 'Teachers in the Ridgeway pilot got four hours a week back.',
				evidence: { kind: 'proof_point', id: 'pp_ridgeway' },
				flagState: 'clean',
				flagReason: null,
				editedAt: new Date().toISOString()
			};
			this.groups.forEach((g) => (g.reviewState = 'approved'));
			this.requests = [];
		}
	}

	runProgress() {
		this.step = 0;
		this.#later(() => (this.step = 1), 300);
		this.#later(() => (this.step = 2), 1100);
		this.#later(() => (this.step = 3), 2100);
		this.#later(() => (this.step = 4), 3100);
	}

	generate() {
		if (this.budgetSpent) return;

		// Phase 3 replaces this with a real pre-flight validation call.
		if (/guarantee|score|test result/i.test(this.brief)) {
			this.view = 'refusal';
			this.demo = 'refusal';
			return;
		}

		this.#clearTimers();
		this.view = 'generating';
		this.demo = 'generating';
		this.groups = this.#freshGroups();
		this.requests = this.#freshRequests();
		this.editingId = null;
		this.justCheckedId = null;
		this.tab = 'talking_point';
		this.runProgress();
		this.#later(() => {
			this.view = 'kit';
			this.demo = 'landing';
		}, 3900);
	}

	setTab(assetType: AssetType) {
		this.tab = assetType;
		this.openEvidenceId = null;
	}

	startEdit(claimId: string) {
		const claim = this.activeGroup.claims.find((c) => c.id === claimId);
		if (!claim) return;
		this.editingId = claim.id;
		this.editText = claim.body;
		this.justCheckedId = null;
		this.openEvidenceId = null;
	}

	cancelEdit() {
		this.editingId = null;
	}

	saveEdit() {
		const id = this.editingId;
		if (!id) return;
		const text = this.editText;
		const group = this.activeGroup;
		const i = group.claims.findIndex((c) => c.id === id);
		if (i === -1) return;

		const previous = group.claims[i];
		group.claims[i] = { ...previous, body: text };
		this.editingId = null;
		this.checkingId = id;
		this.actionError = null;

		if (this.live && this.#persist) {
			// Phase 6 re-runs the critique pass here and updates the flag in place.
			this.#persist
				.edit(id, text)
				.then((kit) => {
					this.applyServerKit(kit);
					this.justCheckedId = id;
				})
				.catch(() => {
					group.claims[i] = previous;
					this.editText = text;
					this.editingId = id;
					this.actionError = 'That edit did not save. Your wording is still here.';
				})
				.finally(() => (this.checkingId = null));
			return;
		}

		// Phase 6 replaces this with a real single-line critique call.
		this.#later(() => {
			const j = group.claims.findIndex((c) => c.id === id);
			if (j !== -1) {
				group.claims[j] = {
					...group.claims[j],
					evidence: { kind: 'proof_point', id: 'pp_ridgeway' },
					flagState: 'clean',
					flagReason: null,
					editedAt: new Date().toISOString()
				};
			}
			this.checkingId = null;
			this.justCheckedId = id;
			if (id === 's2') this.requests = [];
		}, 1100);
	}

	setGroupReview(state: ReviewState) {
		const active = this.activeGroup;
		const i = this.groups.findIndex((g) => g.assetType === active.assetType);
		if (i === -1) return;

		const previous = this.groups[i].reviewState;
		// Answer the click immediately, then reconcile with the server.
		this.groups[i].reviewState = state;
		this.actionError = null;

		if (!this.live || !this.#persist) {
			if (state === 'approved') this.demo = 'partial';
			return;
		}

		this.saving = true;
		this.#persist
			.review(active.assetType, state)
			.then((kit) => this.applyServerKit(kit))
			.catch(() => {
				// Put the real state back rather than show a decision that did not save.
				this.groups[i].reviewState = previous;
				this.actionError = 'That decision did not save. Check your connection and try again.';
			})
			.finally(() => (this.saving = false));
	}

	/** Replaces local state with what the database actually holds. */
	applyServerKit(kit: Kit) {
		this.#baseline = kit;
		this.#proofPoints = kit.proofPoints;
		this.groups = structuredClone(kit.groups);
		this.requests = structuredClone(kit.evidenceRequests);
	}

	copyLink(link: string) {
		navigator.clipboard?.writeText(link).catch(() => {
			// Clipboard can be blocked; the link is visible next to the button.
		});
		this.copied = true;
		this.#later(() => (this.copied = false), 2000);
	}
}
