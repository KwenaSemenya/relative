"""Turning a brief and its proof points into claims.

One Claude call writes the whole kit. Not one call per asset type, and not one
prompt per audience: the audience is a parameter inside a single prompt, so
there is exactly one place where the house voice lives and no way for the three
asset types to drift apart in what they claim.

The call is asked for the citation alongside the line, rather than being asked
to write first and attribute afterwards. A line and its evidence chosen in the
same breath is a line that had to be supportable before it could be written.

Whatever comes back is checked against the proof points and pillars this kit
actually has. A line citing something that does not exist is dropped rather
than shown, because an unverifiable citation is worse than a missing line.
"""

from dataclasses import dataclass, field

from app.claude import CallRecord, ask
from app.models import Narrative

ASSET_TYPES = ("talking_point", "social", "faq")

# Claim ids are readable and kit-scoped: t1, s2, f3. They appear in evidence
# request copy, so they have to mean something to a person reading it.
ID_PREFIX = {"talking_point": "t", "social": "s", "faq": "f"}


@dataclass
class DraftClaim:
    id: str
    asset_type: str
    body: str
    pillar_id: str | None
    evidence_kind: str | None
    evidence_proof_point_id: str | None
    flag_state: str = "clean"
    flag_reason: str | None = None


@dataclass
class Draft:
    claims: list[DraftClaim] = field(default_factory=list)
    # (id, need, why)
    evidence_requests: list[tuple[str, str, str]] = field(default_factory=list)


DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "description": "The lines that can be written and supported.",
            "items": {
                "type": "object",
                "properties": {
                    "asset_type": {
                        "type": "string",
                        "enum": list(ASSET_TYPES),
                    },
                    "body": {
                        "type": "string",
                        "description": (
                            "The line itself, ready to use. For faq, the "
                            "question and its answer in one string."
                        ),
                    },
                    "pillar_id": {
                        "type": "string",
                        "description": "The pillar this line serves.",
                    },
                    "evidence_kind": {
                        "type": "string",
                        "enum": ["proof_point", "pillar"],
                        "description": (
                            "proof_point when the line states something "
                            "specific that happened. pillar when it states "
                            "the company's position."
                        ),
                    },
                    "evidence_id": {
                        "type": "string",
                        "description": (
                            "The id of the proof point or pillar named above. "
                            "Must be one you were given."
                        ),
                    },
                },
                "required": [
                    "asset_type",
                    "body",
                    "pillar_id",
                    "evidence_kind",
                    "evidence_id",
                ],
            },
        },
        "evidence_requests": {
            "type": "array",
            "description": (
                "One per line you could not write. Empty if the proof points "
                "covered everything the brief asked for."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "need": {
                        "type": "string",
                        "description": (
                            "The evidence that would unblock it, as a thing "
                            "someone could go and find. At most 12 words."
                        ),
                    },
                    "why": {
                        "type": "string",
                        "description": (
                            "What the brief asked for, and what the proof "
                            "points measured instead. Address the reader as "
                            "'you'. Name a proof point by what it is — 'the "
                            "Ridgeway pilot' — never by its id. At most 35 "
                            "words."
                        ),
                    },
                },
                "required": ["need", "why"],
            },
        },
    },
    "required": ["claims", "evidence_requests"],
}


SYSTEM = """You write marketing copy for Kestrel Learn from an approved narrative.

You write one whole kit in one pass: talking points, social copy and an FAQ.

Every line rests on exactly one named source, and you name it as you write:

- A proof point, when the line states something specific that happened: a
  number, a result, a named study or district.
- A pillar, when the line states the company's position rather than a result.

Two rules decide whether a line may exist at all.

1. Never exceed what a proof point actually measured. A proof point about
   teacher prep time supports a claim about prep time and nothing else. Do not
   round a figure up, restate it as a percentage, or widen "six schools" into
   "schools everywhere".
2. Never write anything on the never-say list, in any wording. The rule is
   about the meaning, not the phrase: "cuts your staffing costs" is
   "Replaces teachers" wearing a different coat.

If a line the brief asks for would break either rule, do not write it. Record
an evidence request naming what would unblock it. A short kit of lines that
hold up is the correct outcome. A full kit containing one line that does not
is a failure, because a person now has to find it.

One line makes one claim: the claim its cited source supports. If you find
yourself joining two claims with "and", you have either two lines or one line
too many.

Write a kit of:

- 3 or 4 talking points. Plain statements a person can say out loud in a
  meeting. At most 30 words each.
- 2 or 3 social lines. At most 20 words each. No hashtags, no emoji, no
  exclamation marks.
- 3 FAQ entries. Each is the question and its answer in one string, at most 35
  words, like "What does it cost? One price for the whole school, however many
  pupils use it."

These are ceilings, not targets. Shorter is better everywhere. Cut any word
that is not doing work.

Write fewer lines than that when the proof points do not support more. Fewer
honest lines is not a lesser kit.

The audience sets the tone and nothing else. The same facts, worded for that
reader. Never soften a rule because of who is reading.

Write in plain British English. No marketing throat-clearing, no "unlock", no
"empower", no "seamless". Short sentences. A teacher should recognise it as
something a person wrote."""


def _prompt(
    *,
    brief: str,
    audience: str,
    proof_points: list[tuple[str, str]],
    narrative: Narrative,
) -> str:
    pillars = "\n".join(f"- {p.id}: {p.title} — {p.body}" for p in narrative.pillars)
    never_say = "\n".join(f"- {n}" for n in narrative.never_say)

    if proof_points:
        proof = "\n".join(f"- {pid}: {text}" for pid, text in proof_points)
    else:
        # A kit with no proof points is legitimate: every line then rests on a
        # pillar, and anything specific becomes an evidence request.
        proof = "(none supplied — you may only cite pillars)"

    return f"""Approved pillars:
{pillars}

Never say:
{never_say}

Proof points you may cite:
{proof}

Tone to write in: {audience}

The brief:
{brief}

Write the kit."""


def _collect(
    result: dict,
    *,
    proof_ids: set[str],
    pillar_ids: set[str],
) -> Draft:
    """Keep only what this kit can actually stand behind."""
    claims: list[DraftClaim] = []
    counts = dict.fromkeys(ASSET_TYPES, 0)

    for raw in result.get("claims") or []:
        # The schema is a forced tool call, not a guarantee. A malformed entry
        # is one line lost, which this function is already built to survive.
        if not isinstance(raw, dict):
            continue
        asset_type = raw.get("asset_type")
        body = (raw.get("body") or "").strip()
        kind = raw.get("evidence_kind")
        evidence_id = (raw.get("evidence_id") or "").strip()
        pillar_id = (raw.get("pillar_id") or "").strip()

        if asset_type not in ASSET_TYPES or not body:
            continue
        # A citation naming something this kit does not have cannot be shown
        # next to the line, and a line the reader cannot check is the thing
        # this product exists to prevent.
        if kind == "proof_point" and evidence_id not in proof_ids:
            continue
        if kind == "pillar" and evidence_id not in pillar_ids:
            continue
        if kind not in {"proof_point", "pillar"}:
            continue

        counts[asset_type] += 1
        claims.append(
            DraftClaim(
                id=f"{ID_PREFIX[asset_type]}{counts[asset_type]}",
                asset_type=asset_type,
                body=body,
                pillar_id=pillar_id if pillar_id in pillar_ids else None,
                evidence_kind=kind,
                evidence_proof_point_id=evidence_id if kind == "proof_point" else None,
            )
        )

    requests: list[tuple[str, str, str]] = []
    for i, raw in enumerate(result.get("evidence_requests") or [], start=1):
        need = (raw.get("need") or "").strip()
        why = (raw.get("why") or "").strip()
        if need and why:
            requests.append((f"er{i}", need, why))

    return Draft(claims=claims, evidence_requests=requests)


async def draft_claims(
    *,
    brief: str,
    audience: str,
    proof_points: list[tuple[str, str]],
    narrative: Narrative,
) -> tuple[Draft, CallRecord]:
    """Write the kit. `proof_points` is [(id, text)] with the kit's real ids."""
    result, record = await ask(
        phase="drafting",
        system=SYSTEM,
        prompt=_prompt(
            brief=brief,
            audience=audience,
            proof_points=proof_points,
            narrative=narrative,
        ),
        schema=DRAFT_SCHEMA,
        tool_name="record_kit",
        max_tokens=4096,
    )

    draft = _collect(
        result,
        proof_ids={pid for pid, _ in proof_points},
        pillar_ids={p.id for p in narrative.pillars},
    )
    return draft, record
