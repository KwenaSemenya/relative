"""Seeds the narrative and the worked example kit.

Run after migrations: `python -m app.seed_db`. Idempotent, so it is safe on
every deploy. The example kit becomes a real row like any other, which is what
lets the landing page and /k/<slug> read through the same path.
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import seed, tables
from app.db import engine


async def seed_narrative(db: AsyncSession) -> None:
    if await db.scalar(select(tables.Narrative.id).limit(1)):
        return

    source = seed.narrative()
    db.add(
        tables.Narrative(
            id=1,
            label=source.label,
            sensitive_reviewer=source.sensitive_reviewer,
            never_say=source.never_say,
        )
    )
    await db.flush()
    for ordinal, pillar in enumerate(source.pillars):
        db.add(
            tables.Pillar(
                id=pillar.id,
                narrative_id=1,
                ordinal=ordinal,
                title=pillar.title,
                body=pillar.body,
            )
        )


async def seed_example_kit(db: AsyncSession) -> None:
    source = seed.example_kit()
    if await db.scalar(select(tables.Kit.id).where(tables.Kit.slug == source.slug)):
        return

    kit = tables.Kit(
        id=source.slug,
        slug=source.slug,
        brief=source.brief,
        audience=source.audience,
        sensitive_market=source.sensitive_market,
    )
    db.add(kit)
    for i, p in enumerate(source.proof_points):
        db.add(
            tables.ProofPoint(kit_id=kit.id, id=p.id, ordinal=i, text=p.text)
        )
    # Claims cite proof points through a composite foreign key that SQLAlchemy
    # does not order for us, so the proof points have to land first. Child rows
    # are added directly rather than through kit.claims, because touching that
    # collection on a flushed kit would trigger a lazy load.
    await db.flush()

    for group in source.groups:
        for ordinal, claim in enumerate(group.claims):
            kind = claim.evidence.kind if claim.evidence else None
            db.add(
                tables.Claim(
                    kit_id=kit.id,
                    id=claim.id,
                    asset_type=claim.asset_type,
                    ordinal=ordinal,
                    body=claim.body,
                    pillar_id=claim.pillar_id,
                    evidence_kind=kind,
                    evidence_proof_point_id=(
                        claim.evidence.id if kind == "proof_point" else None
                    ),
                    flag_state=claim.flag_state,
                    flag_reason=claim.flag_reason,
                    review_state="pending",
                )
            )

    for i, r in enumerate(source.evidence_requests):
        db.add(
            tables.EvidenceRequest(
                kit_id=kit.id, id=r.id, ordinal=i, need=r.need, why=r.why
            )
        )


async def main() -> None:
    async with AsyncSession(engine()) as db:
        await seed_narrative(db)
        await seed_example_kit(db)
        await db.commit()
    await engine().dispose()
    print("seeded")


if __name__ == "__main__":
    asyncio.run(main())
