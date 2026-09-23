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

export interface DraftInput {
	brief: string;
	audience: string;
	proofPoints: string[];
	sensitiveMarket: boolean;
}

/** Exactly one of the three is set. A limit means the brief was never read. */
export interface DraftResult {
	kit: Kit | null;
	refusal: { reason: string; fix: string } | null;
	limit: { reason: string; fix: string } | null;
}

/** Runs pre-flight validation and, if it passes, creates the kit. */
export type Draft = (input: DraftInput) => Promise<DraftResult>;

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
	/**
	 * Supplied by the landing page. Without it the demo switcher runs its
	 * scripted timings instead of calling the server.
	 */
	draft?: Draft;
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

	/**
	 * Why the last brief was refused. Seeded with the worked example so the
	 * demo switcher still shows it; a real generate replaces both.
	 */
	refusalReason = $state(REFUSAL_REASON);
	refusalFix = $state(REFUSAL_FIX);
	/**
	 * Set when the demo has nothing left to spend. Its wording comes from the
	 * server, which is the only thing that knows which limit was hit and when
	 * it lifts, so the page never guesses at a number or a time.
	 */
	limit = $state<{ reason: string; fix: string } | null>(null);
	/** True once this session generated its own kit, so the page stops
	 * describing what is on screen as last week's worked example. */
	generated = $state(false);

	readonly live: boolean;
	/** Changes when a generate replaces the kit, which is what the share link
	 * is built from. */
	slug = $state('');
	#narrative: Narrative;
	#proofPoints: ProofPoint[];
	#baseline: Kit | null;
	#persist: Persist | null;
	#draft: Draft | null;

	constructor(options: KitStateOptions = {}) {
		const { kit, narrative, live = false, persist, draft } = options;

		this.live = live;
		this.#persist = persist ?? null;
		this.#draft = draft ?? null;
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

	/** True when there is nothing left to generate with, demo or real. */
	get budgetSpent() {
		return this.demo === 'budget' || !!this.limit;
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
		if (this.limit) return this.limit.reason;
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

	/** The line under the progress bar.
	 *
	 * A real generate is three Claude calls and takes about half a minute, so
	 * it says so. Quoting the demo's four seconds to someone who is waiting
	 * thirty makes the product look broken rather than fast.
	 */
	get generationCount() {
		if (this.step < GENERATION_STEPS.length) {
			return this.live
				? 'Usually takes about half a minute.'
				: 'Usually takes about four seconds.';
		}
		return this.live
			? 'Every line is being checked against the narrative.'
			: 'Eight lines drafted, eight checked.';
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
			const flagged = claim.flagState === 'flagged' && !editing && !checking;
			return {
				id: claim.id,
				text: claim.body,
				reason: claim.flagReason,
				evidence: resolved?.label ?? '',
				sourceNo: resolved?.number ?? '',
				editing,
				checking,
				flagged,
				showMarker: !!resolved && !checking && !editing,
				justChecked: this.justCheckedId === claim.id,
				// The same check that clears a line can also catch one, so this
				// reports the verdict rather than assuming the edit fixed it.
				recheckLabel: flagged ? 'Re-checked — still flagged' : 'Re-checked, on message',
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
				// The server says which limit was hit and when it lifts. Only the
				// scripted demo state, which has no server behind it, falls back.
				title: this.limit?.reason ?? 'You have used all five demo generations for today.',
				body:
					this.limit?.fix ??
					'The kit below is the worked example, not yours. Your brief and proof points are saved — generate again tomorrow.',
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
		if (this.generated && this.view === 'kit' && this.decidedCount === 0) {
			return {
				kicker: 'Your kit',
				title: 'Written from your brief. This link opens it anywhere.',
				body: 'Every line names the proof point behind it. Approve, edit or reject each group — the link keeps whatever you decide.',
				hasLink: true,
				link: this.shareLink
			};
		}
		if (
			!this.live &&
			!this.generated &&
			this.demo === 'landing' &&
			this.decidedCount === 0 &&
			!this.justCheckedId
		) {
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

	/** What went wrong, in the server's words where it had any.
	 *
	 * The API explains refusals it makes on purpose — a sensitive market going
	 * to a named reviewer, a line that could not be re-checked — and those read
	 * better than anything this layer could guess from a failed promise.
	 */
	#why(e: unknown, fallback: string) {
		return e instanceof Error && e.message ? e.message : fallback;
	}

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
		this.actionError = null;
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
			// The scripted brief needs the scripted reason beside it. A live
			// refusal left over from a real generate would describe a brief the
			// panel is no longer showing.
			this.refusalReason = REFUSAL_REASON;
			this.refusalFix = REFUSAL_FIX;
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

	/** Milliseconds at which each step starts running.
	 *
	 * The demo runs the design's scripted pace. A real generate is three Claude
	 * calls and takes around half a minute, so it gets its own pacing measured
	 * from actual runs: validation, then the long drafting call, then the
	 * critique. Reusing the scripted timings would park a full progress bar in
	 * front of someone for another twenty seconds, which reads as a hang.
	 */
	static DEMO_PACE = [300, 1100, 2100, 3100];
	static LIVE_PACE = [300, 3000, 6500, 24000];

	runProgress(pace: number[] = KitState.DEMO_PACE) {
		this.step = 0;
		pace.forEach((at, i) => this.#later(() => (this.step = i + 1), at));
	}

	async generate() {
		if (this.budgetSpent || this.generating) return;

		// The progress bar starts before the call so the click is acknowledged
		// immediately, rather than after Claude has finished reading the brief.
		this.#clearTimers();
		this.actionError = null;
		this.view = 'generating';
		this.demo = 'generating';
		this.editingId = null;
		this.justCheckedId = null;
		this.runProgress(this.#draft ? KitState.LIVE_PACE : KitState.DEMO_PACE);

		if (!this.#draft) {
			// No server to call: the demo switcher runs the scripted timings.
			this.groups = this.#freshGroups();
			this.requests = this.#freshRequests();
			this.tab = 'talking_point';
			this.#later(() => {
				this.view = 'kit';
				this.demo = 'landing';
			}, 3900);
			return;
		}

		try {
			const result = await this.#draft({
				brief: this.brief,
				audience: this.audience,
				proofPoints: this.proofInputs.map((p) => p.trim()).filter(Boolean),
				sensitiveMarket: this.sensitive
			});

			this.#clearTimers();

			if (result.limit) {
				// Nothing was read and nothing was spent. The worked example stays
				// on screen so the page is still worth looking at, and the notice
				// above it says why it is not theirs.
				this.limit = result.limit;
				this.view = 'kit';
				this.demo = 'landing';
				return;
			}

			if (result.refusal) {
				// Nothing was written and nothing is cleared. Every input stays
				// exactly where the user left it.
				this.refusalReason = result.refusal.reason;
				this.refusalFix = result.refusal.fix;
				this.view = 'refusal';
				this.demo = 'refusal';
				return;
			}

			if (result.kit) {
				this.applyServerKit(result.kit);
				this.generated = true;
				this.tab = 'talking_point';
				this.view = 'kit';
				this.demo = 'landing';
			}
		} catch (e) {
			// The brief could not be checked. That is not a refusal, so the page
			// says so plainly and keeps the user where they were.
			this.#clearTimers();
			this.view = 'kit';
			this.demo = 'landing';
			this.actionError =
				e instanceof Error && e.message
					? e.message
					: 'The brief could not be checked just now. Nothing you typed was lost.';
		}
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
			// The server re-checks this one line with the same cold critique the
			// whole kit got, so the flag that comes back belongs to the new
			// wording rather than the sentence it replaced.
			this.#persist
				.edit(id, text)
				.then((kit) => {
					this.applyServerKit(kit);
					this.justCheckedId = id;
				})
				.catch((e) => {
					// Put the line back and reopen the box with what was typed. An
					// edit that failed to save must not look like one that did.
					group.claims[i] = previous;
					this.editText = text;
					this.editingId = id;
					this.actionError = this.#why(e, 'That edit did not save. Your wording is still here.');
				})
				.finally(() => (this.checkingId = null));
			return;
		}

		// The demo switcher has no server to call, so it plays the design's
		// scripted outcome for this one line at the design's pace.
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
		// A decision and its undo are one click apart, so a second click landing
		// mid-flight would have two writes racing to say what the group is.
		if (this.saving) return;

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
			.catch((e) => {
				// Put the real state back rather than show a decision that did not save.
				this.groups[i].reviewState = previous;
				this.actionError = this.#why(
					e,
					'That decision did not save. Check your connection and try again.'
				);
			})
			.finally(() => (this.saving = false));
	}

	/** Replaces local state with what the database actually holds. */
	applyServerKit(kit: Kit) {
		this.#baseline = kit;
		this.#proofPoints = kit.proofPoints;
		this.groups = structuredClone(kit.groups);
		this.requests = structuredClone(kit.evidenceRequests);
		// The slug travels with the kit: after a generate this is a different
		// kit, and the share link has to point at it rather than the example.
		this.slug = kit.slug;
	}

	copyLink(link: string) {
		navigator.clipboard?.writeText(link).catch(() => {
			// Clipboard can be blocked; the link is visible next to the button.
		});
		this.copied = true;
		this.#later(() => (this.copied = false), 2000);
	}
}
