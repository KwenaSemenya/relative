"""Reads and writes, and the mapping between rows and API payloads."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import drafting, tables
from app.claude import CallRecord
from app.models import AssetGroup, Claim, EvidenceRequest, Kit, Narrative, Pillar
from app.models import ProofPoint as ProofPointModel
from app.slugs import make_slug

# Asset types in the order the design's tabs show them, with the wording the
# group's approve button uses ("Approve talking points").
GROUPS: list[tuple[str, str, str]] = [
    ("talking_point", "Talking points", "talking points"),
    ("social", "Social", "social copy"),
    ("faq", "FAQ", "the FAQ"),
]


async def get_narrative(db: AsyncSession) -> Narrative | None:
    row = await db.scalar(select(tables.Narrative).limit(1))
    if row is None:
        return None
    return Narrative(
        label=row.label,
        sensitive_reviewer=row.sensitive_reviewer,
        never_say=list(row.never_say),
        pillars=[Pillar(id=p.id, title=p.title, body=p.body) for p in row.pillars],
    )


def _claim(row: tables.Claim) -> Claim:
    evidence = None
    if row.evidence_kind == "proof_point":
        evidence = {"kind": "proof_point", "id": row.evidence_proof_point_id}
    elif row.evidence_kind == "pillar":
        evidence = {"kind": "pillar", "id": row.pillar_id}

    return Claim(
        id=row.id,
        asset_type=row.asset_type,
        body=row.body,
        pillar_id=row.pillar_id,
        evidence=evidence,
        flag_state=row.flag_state,
        flag_reason=row.flag_reason,
        edited_at=row.edited_at.isoformat() if row.edited_at else None,
    )


def _review_state(claims: list[tables.Claim]) -> str:
    """A group is only decided when every claim in it agrees.

    Review state lives on the claim, because the spec puts it there and because
    a future per-line decision needs somewhere to go. The design decides at
    group level, so the group reports the value its claims share.
    """
    states = {c.review_state for c in claims}
    return states.pop() if len(states) == 1 else "pending"


def to_kit(row: tables.Kit) -> Kit:
    by_type: dict[str, list[tables.Claim]] = {}
    for claim in row.claims:
        by_type.setdefault(claim.asset_type, []).append(claim)

    groups = [
        AssetGroup(
            asset_type=asset_type,
            title=title,
            short_name=short_name,
            review_state=_review_state(by_type[asset_type]),
            claims=[_claim(c) for c in by_type[asset_type]],
        )
        for asset_type, title, short_name in GROUPS
        if by_type.get(asset_type)
    ]

    return Kit(
        slug=row.slug,
        brief=row.brief,
        audience=row.audience,
        sensitive_market=row.sensitive_market,
        created_at=row.created_at.isoformat(),
        proof_points=[
            ProofPointModel(id=p.id, text=p.text) for p in row.proof_points
        ],
        groups=groups,
        evidence_requests=[
            EvidenceRequest(id=r.id, need=r.need, why=r.why)
            for r in row.evidence_requests
        ],
    )


def proof_point_ids(proof_texts: list[str]) -> list[tuple[str, str]]:
    """The ids a kit's proof points will have, before the kit exists.

    Drafting has to cite these ids, and drafting runs before anything is
    written, so the numbering is decided here rather than inferred later.
    """
    return [(f"pp{i + 1}", text) for i, text in enumerate(proof_texts)]


def _call_rows(
    records: list[CallRecord], *, run_id: str, kit_id: str | None
) -> list[tables.ClaudeCall]:
    return [
        tables.ClaudeCall(
            id=str(uuid.uuid4()),
            run_id=run_id,
            kit_id=kit_id,
            ordinal=i,
            phase=r.phase,
            model=r.model,
            system=r.system,
            prompt=r.prompt,
            response=r.response,
            input_tokens=r.input_tokens,
            output_tokens=r.output_tokens,
        )
        for i, r in enumerate(records)
    ]


async def log_calls(
    db: AsyncSession, records: list[CallRecord], *, run_id: str
) -> None:
    """Record calls belonging to a request that produced no kit.

    A refused brief is the case most worth being able to read back, and it
    never reaches create_kit, so it needs its own way in.
    """
    for row in _call_rows(records, run_id=run_id, kit_id=None):
        db.add(row)
    await db.commit()


async def create_kit(
    db: AsyncSession,
    brief: str,
    audience: str,
    proof_texts: list[str],
    sensitive_market: bool,
    draft: drafting.Draft,
    records: list[CallRecord],
    run_id: str,
) -> Kit:
    slug = make_slug(brief)
    kit = tables.Kit(
        id=slug,
        slug=slug,
        brief=brief,
        audience=audience,
        sensitive_market=sensitive_market,
    )
    db.add(kit)
    for i, (pp_id, text) in enumerate(proof_point_ids(proof_texts)):
        db.add(tables.ProofPoint(kit_id=kit.id, id=pp_id, ordinal=i, text=text))
    # Claims cite proof points through a composite foreign key that SQLAlchemy
    # does not order for us, so the proof points have to land first. Child rows
    # are added directly rather than through kit.claims, because touching that
    # collection on a flushed kit would trigger a lazy load.
    await db.flush()

    ordinals: dict[str, int] = {}
    for draft_claim in draft.claims:
        ordinal = ordinals.get(draft_claim.asset_type, 0)
        ordinals[draft_claim.asset_type] = ordinal + 1
        db.add(
            tables.Claim(
                kit_id=kit.id,
                id=draft_claim.id,
                asset_type=draft_claim.asset_type,
                ordinal=ordinal,
                body=draft_claim.body,
                pillar_id=draft_claim.pillar_id,
                evidence_kind=draft_claim.evidence_kind,
                evidence_proof_point_id=draft_claim.evidence_proof_point_id,
                flag_state=draft_claim.flag_state,
                flag_reason=draft_claim.flag_reason,
                review_state="pending",
            )
        )

    for i, (rid, need, why) in enumerate(draft.evidence_requests):
        db.add(
            tables.EvidenceRequest(
                kit_id=kit.id, id=rid, ordinal=i, need=need, why=why
            )
        )

    for row in _call_rows(records, run_id=run_id, kit_id=kit.id):
        db.add(row)

    await db.commit()
    created = await get_kit(db, slug)
    assert created is not None
    return created


async def get_kit(db: AsyncSession, slug: str) -> Kit | None:
    row = await db.scalar(select(tables.Kit).where(tables.Kit.slug == slug))
    return to_kit(row) if row else None


class SensitiveMarket(Exception):
    """This kit cannot be approved here, whatever the caller asked for."""


async def set_group_review(
    db: AsyncSession, slug: str, asset_type: str, review_state: str
) -> Kit | None:
    kit = (
        await db.execute(
            select(tables.Kit.id, tables.Kit.sensitive_market).where(
                tables.Kit.slug == slug
            )
        )
    ).first()
    if kit is None:
        return None
    kit_id, sensitive_market = kit

    # The button is hidden in the browser, but hiding a button is not a rule.
    # A sensitive-market kit goes to a named reviewer, so the only place that
    # can be enforced is here.
    if sensitive_market and review_state == "approved":
        raise SensitiveMarket

    await db.execute(
        update(tables.Claim)
        .where(tables.Claim.kit_id == kit_id, tables.Claim.asset_type == asset_type)
        .values(review_state=review_state)
    )
    await db.commit()
    return await get_kit(db, slug)


@dataclass
class ClaimContext:
    """What re-checking one edited line needs, without its kit around it."""

    kit_id: str
    sensitive_market: bool
    claim: drafting.DraftClaim
    proof_points: list[tuple[str, str]]


async def get_claim_context(
    db: AsyncSession, slug: str, claim_id: str, body: str
) -> ClaimContext | None:
    """The edited line, ready to be judged, and the sources it may cite.

    The claim carries the new wording rather than the stored one, because what
    needs checking is what the person just wrote.
    """
    kit_row = await db.scalar(select(tables.Kit).where(tables.Kit.slug == slug))
    if kit_row is None:
        return None

    row = next((c for c in kit_row.claims if c.id == claim_id), None)
    if row is None:
        return None

    return ClaimContext(
        kit_id=kit_row.id,
        sensitive_market=kit_row.sensitive_market,
        claim=drafting.DraftClaim(
            id=row.id,
            asset_type=row.asset_type,
            body=body,
            pillar_id=row.pillar_id,
            evidence_kind=row.evidence_kind,
            evidence_proof_point_id=row.evidence_proof_point_id,
        ),
        proof_points=[(p.id, p.text) for p in kit_row.proof_points],
    )


async def save_claim_edit(
    db: AsyncSession,
    slug: str,
    *,
    kit_id: str,
    claim: drafting.DraftClaim,
    records: list[CallRecord],
    run_id: str,
) -> Kit | None:
    """Store the new wording and whatever the re-check made of it.

    An edited line goes back to pending review. A group approved before the
    edit was approved for wording that no longer exists, and carrying that
    approval forward would put a tick next to a line nobody agreed to.
    """
    result = await db.execute(
        update(tables.Claim)
        .where(tables.Claim.kit_id == kit_id, tables.Claim.id == claim.id)
        .values(
            body=claim.body,
            flag_state=claim.flag_state,
            flag_reason=claim.flag_reason,
            review_state="pending",
            edited_at=datetime.now(UTC),
        )
    )
    if result.rowcount == 0:
        return None

    for row in _call_rows(records, run_id=run_id, kit_id=kit_id):
        db.add(row)

    await db.commit()
    return await get_kit(db, slug)
