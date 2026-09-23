"""What this demo has actually cost, per day.

Run: .venv/bin/python scripts/show_spend.py [days]

Priced from the tokens that were really billed, using the same function the
cap is enforced with, so the figure here and the figure that stops a generate
can never disagree. If this says the cap is spent, the page says so too.

Today's row is the live one — it is what `budget.check` is reading.
"""

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app import budget, tables  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import session  # noqa: E402


async def report(db: AsyncSession, days: int) -> None:
    settings = get_settings()
    day = func.date_trunc("day", tables.ClaudeCall.created_at).label("day")

    rows = (
        await db.execute(
            select(
                day,
                func.count(func.distinct(tables.ClaudeCall.run_id)),
                func.count(func.distinct(tables.ClaudeCall.client)),
                func.sum(tables.ClaudeCall.input_tokens),
                func.sum(tables.ClaudeCall.output_tokens),
            )
            .group_by(day)
            .order_by(day.desc())
            .limit(days)
        )
    ).all()

    if not rows:
        print("Nothing spent yet.")
        return

    print(
        f"cap ${settings.daily_budget_usd:.2f} a day, "
        f"{settings.daily_generates_per_visitor} generates a visitor\n"
    )
    print(f"{'day':<12}{'runs':>6}{'visitors':>10}{'in':>10}{'out':>8}{'cost':>10}")

    for date, runs, visitors, tokens_in, tokens_out in rows:
        spend = budget.cost(tokens_in or 0, tokens_out or 0)
        print(
            f"{date:%Y-%m-%d}  {runs:>6}{visitors:>10}"
            f"{tokens_in or 0:>10}{tokens_out or 0:>8}{f'${spend:.4f}':>10}"
        )

    today = await budget.spent_today(db, now=datetime.now(UTC))
    left = max(budget.Decimal(0), budget.Decimal(str(settings.daily_budget_usd)) - today)
    print(f"\ntoday ${today:.4f} spent, ${left:.4f} left")


async def main() -> None:
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    async for db in session():
        await report(db, days)


if __name__ == "__main__":
    asyncio.run(main())
