"""Exercises the generation call directly, without touching the database.

Run: .venv/bin/python scripts/check_drafting.py

Checks the two things Phase 4 promises: every line cites a source this kit
actually has, and a line that cannot be supported becomes an evidence request
instead of being written anyway.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import seed  # noqa: E402
from app.drafting import draft_claims  # noqa: E402

NARRATIVE = seed.narrative()
PILLARS = {p.id: p.title for p in NARRATIVE.pillars}

HARDWARE = "Hardware audit, 14 districts, 2025 — devices already in classrooms"
RIDGEWAY = (
    "Ridgeway pilot, 2025 — teachers reported about four hours less lesson "
    "prep a week, six schools"
)

CASES: list[tuple[str, str, str, list[str]]] = [
    (
        "full evidence",
        "Spring enrolment push for district curriculum leads. Lead on cost and "
        "teacher control.",
        "Institutions",
        [HARDWARE, RIDGEWAY],
    ),
    (
        "one proof point",
        "Back to school campaign. Focus on what teachers get back.",
        "Educators",
        [RIDGEWAY],
    ),
    (
        "no proof points",
        "Short campaign introducing Kestrel to schools that have never heard of us.",
        "Educators",
        [],
    ),
    (
        "brief reaches past the evidence",
        "Campaign for parents about how Kestrel improves their child's reading.",
        "Influencers",
        [RIDGEWAY],
    ),
    (
        "tone only",
        "Explain what Kestrel is and how it is priced.",
        "Students",
        [HARDWARE],
    ),
]

WORD_CEILING = {"talking_point": 30, "social": 20, "faq": 35}


async def run_case(name: str, brief: str, audience: str, proofs: list[str]) -> int:
    ids = [(f"pp{i + 1}", t) for i, t in enumerate(proofs)]
    valid_proof = {pid for pid, _ in ids}
    draft, usage = await draft_claims(
        brief=brief, audience=audience, proof_points=ids, narrative=NARRATIVE
    )

    problems = []
    by_type: dict[str, int] = {}
    longest: dict[str, int] = {}

    for c in draft.claims:
        by_type[c.asset_type] = by_type.get(c.asset_type, 0) + 1
        words = len(c.body.split())
        longest[c.asset_type] = max(longest.get(c.asset_type, 0), words)

        if c.evidence_kind == "proof_point" and c.evidence_proof_point_id not in valid_proof:
            problems.append(f"{c.id} cites unknown proof point")
        if c.pillar_id not in PILLARS:
            problems.append(f"{c.id} has no valid pillar")
        if words > WORD_CEILING[c.asset_type]:
            problems.append(f"{c.id} is {words} words (ceiling {WORD_CEILING[c.asset_type]})")
        # No proof points supplied means nothing specific can be cited.
        if not proofs and c.evidence_kind == "proof_point":
            problems.append(f"{c.id} cites a proof point that was never supplied")

    print(f"\n=== {name}  [{audience}]")
    print(f"    {brief}")
    print(
        f"    proof points: {len(proofs)}  ->  "
        f"claims {dict(sorted(by_type.items()))}  "
        f"requests {len(draft.evidence_requests)}  "
        f"tokens {usage['input_tokens']}/{usage['output_tokens']}"
    )
    print(f"    longest line by type: {dict(sorted(longest.items()))}")

    for c in draft.claims:
        src = c.evidence_proof_point_id or c.evidence_kind
        print(f"    [{c.id}] ({src}) {c.body}")
    for rid, need, why in draft.evidence_requests:
        print(f"    [{rid}] NEED {need}\n          WHY  {why}")

    for p in problems:
        print(f"    !! {p}")
    return len(problems)


async def main() -> None:
    results = await asyncio.gather(*(run_case(*c) for c in CASES))
    total = sum(results)
    print(f"\n{'=' * 60}\n{total} problems across {len(CASES)} cases")


if __name__ == "__main__":
    asyncio.run(main())
