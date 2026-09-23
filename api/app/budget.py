"""What the demo is allowed to spend, and on whose behalf.

This is a public page with no accounts, wired to a real API key. Two things
follow from that, and this module is both of them.

The first is a per-visitor allowance, so one person cannot use up the day for
everybody else. The second is a global cap in pounds, because an allowance per
visitor is no protection at all against enough visitors.

Both are counted from `claude_call`, which already records every call the
product makes with its real token usage. Deriving the spend from what was
actually billed means the cap cannot drift away from the bill the way a
separate counter would once a retry or a crash lands between them.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from hashlib import blake2b

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import tables
from app.config import get_settings

# Anthropic's list price for the model this product calls, in USD per million
# tokens. Hard-coded rather than configured: it is a fact about the model, and
# a cap computed from a number someone can typo is not a cap.
USD_PER_MTOK_IN = Decimal("3")
USD_PER_MTOK_OUT = Decimal("15")

def day_start(now: datetime) -> datetime:
    """Midnight UTC before `now`. The window both limits are counted over."""
    return datetime.combine(now.date(), time.min, tzinfo=UTC)


def resets_in(now: datetime) -> str:
    """How long until the window rolls over, in words a person can act on."""
    left = day_start(now) + timedelta(days=1) - now
    hours = int(left.total_seconds() // 3600)
    if hours >= 1:
        return f"in about {hours} hour{'s' if hours != 1 else ''}"
    minutes = max(1, int(left.total_seconds() // 60))
    return f"in about {minutes} minute{'s' if minutes != 1 else ''}"


def client_id(address: str | None) -> str:
    """A stable, non-reversible handle for one visitor.

    The address itself is never stored. A per-visitor allowance needs to
    recognise a returning visitor and nothing else, and an IP address kept in a
    database is personal data kept for no reason anyone asked for.
    """
    if not address:
        return "unknown"
    return blake2b(address.encode(), digest_size=16).hexdigest()


def cost(input_tokens: int, output_tokens: int) -> Decimal:
    return (
        Decimal(input_tokens) * USD_PER_MTOK_IN
        + Decimal(output_tokens) * USD_PER_MTOK_OUT
    ) / Decimal(1_000_000)


@dataclass
class Allowance:
    """Whether a generate may run, and what to say when it may not."""

    ok: bool
    reason: str = ""
    fix: str = ""


async def spent_today(db: AsyncSession, *, now: datetime) -> Decimal:
    """Real dollars spent since midnight UTC, from real token counts."""
    totals = (
        await db.execute(
            select(
                func.coalesce(func.sum(tables.ClaudeCall.input_tokens), 0),
                func.coalesce(func.sum(tables.ClaudeCall.output_tokens), 0),
            ).where(tables.ClaudeCall.created_at >= day_start(now))
        )
    ).one()
    return cost(totals[0], totals[1])


async def generates_today(db: AsyncSession, client: str, *, now: datetime) -> int:
    """How many kits this visitor has asked for since midnight UTC.

    Counted from the pre-flight validation call, which runs exactly once per
    generate and nowhere else. A refused brief still counts, because refusing
    it cost a call — and because otherwise the cheapest way past the limit
    would be to keep submitting briefs that get refused.
    """
    return (
        await db.scalar(
            select(func.count(func.distinct(tables.ClaudeCall.run_id))).where(
                tables.ClaudeCall.client == client,
                tables.ClaudeCall.phase == "validation",
                tables.ClaudeCall.created_at >= day_start(now),
            )
        )
        or 0
    )


async def over_cap(db: AsyncSession) -> bool:
    """Whether the day's money is gone. Every call that spends asks this."""
    settings = get_settings()
    spent = await spent_today(db, now=datetime.now(UTC))
    return spent >= Decimal(str(settings.daily_budget_usd))


async def check(db: AsyncSession, client: str) -> Allowance:
    """Decide before anything is spent. The global cap is asked first.

    Telling someone they have generations left and then refusing them on the
    global cap would be two rejections for one click. If the day's money is
    gone it is gone, and that is the only thing worth saying.
    """
    settings = get_settings()
    now = datetime.now(UTC)

    if await over_cap(db):
        return Allowance(
            ok=False,
            reason=(
                "This demo runs on a real API key with a daily spending cap, "
                f"and today's is used up. It resets {resets_in(now)}."
            ),
            fix=(
                "The kit below is last week's worked example, so you can still "
                "see what comes back. Your brief and proof points are kept."
            ),
        )

    allowed = settings.daily_generates_per_visitor
    used = await generates_today(db, client, now=now)
    if used >= allowed:
        # The number is configurable, so the sentence around it has to survive
        # every value it can be set to. Copy that reads as a placeholder reads
        # as a bug, and zero is the switch that turns generating off without
        # taking the page down, so it gets its own sentence rather than a
        # countdown to an allowance nobody has.
        if allowed == 0:
            reason = "Generating is switched off in this demo just now."
        elif allowed == 1:
            reason = (
                f"You have used your one demo generation for today. "
                f"It resets {resets_in(now)}."
            )
        else:
            reason = (
                f"You have used all {allowed} demo generations for today. "
                f"They reset {resets_in(now)}."
            )

        return Allowance(
            ok=False,
            reason=reason,
            fix=(
                "The kit below is last week's worked example, so you can still "
                "see what comes back. Your brief and proof points are kept."
            ),
        )

    return Allowance(ok=True)
