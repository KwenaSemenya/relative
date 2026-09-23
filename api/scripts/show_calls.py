"""Reads back the Claude calls behind a kit.

Run: .venv/bin/python scripts/show_calls.py [slug]

With no slug, lists the most recent runs. With a slug, prints every call that
produced that kit, and checks the one thing the critique pass promises: that
the brief never reached it.

There is no HTTP endpoint for this. The kit link is the only access control
this product has, and raw prompts are not something to hand out at the same
URL as the copy.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app import tables  # noqa: E402
from app.db import session  # noqa: E402


async def recent(db: AsyncSession) -> None:
    rows = (
        await db.scalars(
            select(tables.ClaudeCall)
            .order_by(tables.ClaudeCall.created_at.desc())
            .limit(30)
        )
    ).all()

    if not rows:
        print("No calls logged yet.")
        return

    for row in rows:
        kit = row.kit_id or "(no kit — refused or failed)"
        print(
            f"{row.created_at:%Y-%m-%d %H:%M}  {row.phase:<10}  "
            f"{row.input_tokens:>6}/{row.output_tokens:<5}  {kit}"
        )


async def for_kit(db: AsyncSession, slug: str) -> None:
    kit = await db.scalar(select(tables.Kit).where(tables.Kit.slug == slug))
    if kit is None:
        print(f"No kit at {slug}.")
        return

    rows = (
        await db.scalars(
            select(tables.ClaudeCall)
            .where(tables.ClaudeCall.kit_id == kit.id)
            .order_by(tables.ClaudeCall.run_id, tables.ClaudeCall.ordinal)
        )
    ).all()

    print(f"kit   {slug}")
    print(f"brief {kit.brief}\n")

    for row in rows:
        print("=" * 72)
        print(
            f"{row.phase}   {row.model}   "
            f"{row.input_tokens} in / {row.output_tokens} out   "
            f"{row.created_at:%Y-%m-%d %H:%M:%S}"
        )
        print(f"--- prompt ---\n{row.prompt}")
        print(f"--- response ---\n{json.dumps(row.response, indent=2)}\n")

    # The critique is only worth having if it really did read cold, and the
    # logged prompt is the only place that can be checked after the fact.
    critique = [r for r in rows if r.phase == "critique"]
    if not critique:
        print("No critique call was logged for this kit.")
        return

    leaked = [r for r in critique if kit.brief.lower() in r.prompt.lower()]
    print("=" * 72)
    if leaked:
        print("!! The brief appears in the critique prompt. It read warm.")
    else:
        print("ok  The critique prompt does not contain the brief.")


async def main() -> None:
    # session() is the FastAPI dependency generator. Iterating it once yields a
    # session and then lets it close on the way out.
    async for db in session():
        if len(sys.argv) > 1:
            await for_kit(db, sys.argv[1])
        else:
            await recent(db)


if __name__ == "__main__":
    asyncio.run(main())
