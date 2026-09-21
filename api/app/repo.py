"""Reads and writes, and the mapping between rows and API payloads."""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import drafting, seed, tables
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


async def create_kit(
    db: AsyncSession,
    brief: str,
    audience: str,
    proof_texts: list[str],
    sensitive_market: bool,
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
    supplied = set()
    for i, text in enumerate(proof_texts):
        pp_id = f"pp{i + 1}"
        supplied.add(pp_id)
        db.add(tables.ProofPoint(kit_id=kit.id, id=pp_id, ordinal=i, text=text))
    # Claims cite proof points through a composite foreign key that SQLAlchemy
    # does not order for us, so the proof points have to land first. Child rows
    # are added directly rather than through kit.claims, because touching that
    # collection on a flushed kit would trigger a lazy load.
    await db.flush()

    draft = drafting.draft_claims(brief, audience, proof_texts)

    # The draft cites proof points by the id the worked example uses. Map those
    # onto the ids this kit actually has, positionally.
    template_ids = [p.id for p in seed.example_kit().proof_points]
    remap = {
        old: f"pp{i + 1}"
        for i, old in enumerate(template_ids)
        if f"pp{i + 1}" in supplied
    }

    requests = list(draft.evidence_requests)
    ordinals: dict[str, int] = {}

    for draft_claim in draft.claims:
        cited = draft_claim.evidence_proof_point_id
        if draft_claim.evidence_kind == "proof_point":
            cited = remap.get(cited or "")
            if cited is None:
                # The proof point this line leaned on was never supplied, so the
                # line does not get written. The gap is recorded instead.
                requests.append(
                    (
                        f"er_{draft_claim.id}",
                        "A proof point for this line",
                        f"A {draft_claim.asset_type.replace('_', ' ')} line needed"
                        " support that no proof point covers, so it was not written.",
                    )
                )
                continue

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
                evidence_proof_point_id=cited,
                flag_state=draft_claim.flag_state,
                flag_reason=draft_claim.flag_reason,
                review_state="pending",
            )
        )

    for i, (rid, need, why) in enumerate(requests):
        db.add(
            tables.EvidenceRequest(
                kit_id=kit.id, id=rid, ordinal=i, need=need, why=why
            )
        )

    await db.commit()
    created = await get_kit(db, slug)
    assert created is not None
    return created


async def get_kit(db: AsyncSession, slug: str) -> Kit | None:
    row = await db.scalar(select(tables.Kit).where(tables.Kit.slug == slug))
    return to_kit(row) if row else None


async def set_group_review(
    db: AsyncSession, slug: str, asset_type: str, review_state: str
) -> Kit | None:
    kit_id = await db.scalar(select(tables.Kit.id).where(tables.Kit.slug == slug))
    if kit_id is None:
        return None

    await db.execute(
        update(tables.Claim)
        .where(tables.Claim.kit_id == kit_id, tables.Claim.asset_type == asset_type)
        .values(review_state=review_state)
    )
    await db.commit()
    return await get_kit(db, slug)


async def edit_claim(
    db: AsyncSession, slug: str, claim_id: str, body: str
) -> Kit | None:
    kit_id = await db.scalar(select(tables.Kit.id).where(tables.Kit.slug == slug))
    if kit_id is None:
        return None

    result = await db.execute(
        update(tables.Claim)
        .where(tables.Claim.kit_id == kit_id, tables.Claim.id == claim_id)
        .values(body=body, edited_at=datetime.now(UTC))
    )
    if result.rowcount == 0:
        return None
    await db.commit()
    return await get_kit(db, slug)
