"""The second opinion, read cold.

A separate Claude call that reads the finished lines against the narrative and
says which ones do not hold up.

It never sees the brief. That is the point of the pass, and it is enforced by
this module having no way to receive one: `critique_claims` takes claims, proof
points and the narrative, and there is no parameter a brief could arrive
through. A critic who knows what was asked for starts reading for intent, and
"they were clearly going for X" is how a line that overstates its evidence gets
waved past. Reading cold, the only question left is whether the line as written
is supported by the source printed next to it — which is exactly the question a
reader of the kit will ask.

The audience is withheld for the same reason. Tone is not a defence for a claim
the evidence does not carry.

Phase 6 re-checks a single edited line by calling this with a list of one, so
nothing here assumes it is looking at a whole kit.
"""

from dataclasses import dataclass

from app.claude import CallRecord, ask
from app.drafting import DraftClaim
from app.models import Narrative


@dataclass
class Judgement:
    claim_id: str
    flagged: bool
    reason: str | None


CRITIQUE_SCHEMA = {
    "type": "object",
    "properties": {
        "judgements": {
            "type": "array",
            "description": "Exactly one entry for every line you were given.",
            "items": {
                "type": "object",
                "properties": {
                    "claim_id": {
                        "type": "string",
                        "description": "The id of the line, exactly as given.",
                    },
                    "verdict": {
                        "type": "string",
                        "enum": ["clean", "flagged"],
                    },
                    "reason": {
                        "type": "string",
                        "description": (
                            "Empty when clean. When flagged: what the line "
                            "claims, and the rule or source it fails against, "
                            "naming the never-say entry or pillar or saying "
                            "what the proof point actually measured. Write to "
                            "the person who will fix it. At most 35 words, "
                            "and never containing an id such as pp1 or "
                            "pillar2."
                        ),
                    },
                },
                "required": ["claim_id", "verdict", "reason"],
            },
        }
    },
    "required": ["judgements"],
}


SYSTEM = """You check finished marketing copy for Kestrel Learn against an approved narrative.

You have not seen the brief these lines were written from, and you do not need
it. You are reading them the way the public will: as claims, next to the source
each one cites. The only question is whether the line as written is carried by
that source.

Flag a line on these grounds and no others:

1. It says more than its cited source supports. Widening the population,
   rounding a figure, restating a number as a percentage, turning "less prep
   time" into "better teaching", or turning a result at six schools into a
   result everywhere.
2. It breaks a never-say rule, in any wording. Judge the meaning, not the
   phrase: "runs the same timetable with fewer staff" is "Replaces teachers"
   wearing a different coat.
3. Its cited source does not support it at all, even narrowly.
4. It contradicts a pillar.

Do not flag anything else. In particular, do not flag a line for being dull,
short, oddly worded, repetitive, or for being a claim you personally cannot
verify from outside this narrative. Tone, style and length are not your
business. A line resting on a pillar is allowed to state the company's
position without a number behind it — that is what pillars are for.

Most lines should come back clean. A flag means someone has to stop and deal
with it, so a flag on a line that is actually fine costs more than it saves.
Flag only what you could defend by pointing at the exact rule or the exact gap.

When you flag, name what the line claims and name the thing it fails against:
the never-say entry, the pillar, or what the proof point actually measured.
Write it for the marketer who has to fix it. No hedging, no apology, no
suggestion to reword it vaguely.

The reason is read on screen next to the line, by someone who has never seen
these instructions. So write it as a sentence, not as a finding:

- Never mention the numbered grounds above. "Rule 2" means nothing to them.
- Never print an id. Not "pp1", not "pillar3". Name the thing in words: "the
  Ridgeway pilot", "the hardware audit", "the pillar on pricing". For a proof
  point, say what it actually measured.
- Quote the never-say entry in words when you mean one.
- One flag, one reason. If a line breaks two rules, give the more serious one
  rather than listing both.

Two sentences: what the line claims, then what it runs into. Thirty words is
plenty. This sits in a small box on screen, and a reason nobody finishes
reading is a reason that did not land.

When a line is clean, leave reason empty."""


def _prompt(
    *,
    claims: list[DraftClaim],
    proof_points: list[tuple[str, str]],
    narrative: Narrative,
) -> str:
    pillars = "\n".join(f"- {p.id}: {p.title} — {p.body}" for p in narrative.pillars)
    never_say = "\n".join(f"- {n}" for n in narrative.never_say)

    if proof_points:
        proof = "\n".join(f"- {pid}: {text}" for pid, text in proof_points)
    else:
        proof = "(none — every line here should be resting on a pillar)"

    titles = {p.id: p.title for p in narrative.pillars}
    lines = []
    for claim in claims:
        if claim.evidence_kind == "proof_point":
            cites = f"proof point {claim.evidence_proof_point_id}"
        else:
            cites = f"pillar {claim.pillar_id} ({titles.get(claim.pillar_id, '?')})"
        lines.append(f"- {claim.id} [{claim.asset_type}] cites {cites}\n  {claim.body}")

    return f"""Approved pillars:
{pillars}

Never say:
{never_say}

Proof points available to this kit:
{proof}

The lines to check:
{chr(10).join(lines)}

Judge every line."""


def _collect(result: dict, *, claim_ids: set[str]) -> dict[str, Judgement]:
    judgements: dict[str, Judgement] = {}

    for raw in result.get("judgements") or []:
        claim_id = (raw.get("claim_id") or "").strip()
        reason = (raw.get("reason") or "").strip()
        if claim_id not in claim_ids:
            continue
        # A flag with nothing to show gives the reader a red mark and no way to
        # act on it, which is worse than not flagging. Treat it as clean.
        flagged = raw.get("verdict") == "flagged" and bool(reason)
        judgements[claim_id] = Judgement(
            claim_id=claim_id,
            flagged=flagged,
            reason=reason if flagged else None,
        )

    return judgements


async def critique_claims(
    *,
    claims: list[DraftClaim],
    proof_points: list[tuple[str, str]],
    narrative: Narrative,
) -> tuple[dict[str, Judgement], CallRecord | None]:
    """Judge each claim cold. Returns judgements by claim id.

    There is deliberately no `brief` parameter. See the module docstring.

    A claim the critic said nothing about stays as it was. Silence is not a
    verdict, and inventing a clean bill of health from it would put a mark of
    approval on a line nobody read.
    """
    if not claims:
        return {}, None

    result, record = await ask(
        phase="critique",
        system=SYSTEM,
        prompt=_prompt(
            claims=claims,
            proof_points=proof_points,
            narrative=narrative,
        ),
        schema=CRITIQUE_SCHEMA,
        tool_name="record_judgements",
        max_tokens=2048,
    )

    return _collect(result, claim_ids={c.id for c in claims}), record


def apply(claims: list[DraftClaim], judgements: dict[str, Judgement]) -> None:
    """Write the verdicts onto the claims, in place."""
    for claim in claims:
        judgement = judgements.get(claim.id)
        if judgement is None:
            continue
        claim.flag_state = "flagged" if judgement.flagged else "clean"
        claim.flag_reason = judgement.reason
