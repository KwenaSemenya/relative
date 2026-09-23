"""Exercises the critique call directly, without touching the database.

Run: .venv/bin/python scripts/check_critique.py

The lines below are written by hand rather than generated, so each one has a
known right answer. A critic is only useful if it catches the bad lines *and*
leaves the good ones alone, so the set is deliberately mostly clean: a pass
that flags everything would score as badly here as one that flags nothing.
"""

import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import seed  # noqa: E402
from app.critique import critique_claims  # noqa: E402
from app.drafting import DraftClaim  # noqa: E402

NARRATIVE = seed.narrative()

PROOF_POINTS = [
    ("pp1", "Hardware audit, 14 districts, 2025 — devices already in classrooms"),
    (
        "pp2",
        "Ridgeway pilot, 2025 — teachers reported about four hours less lesson "
        "prep a week, six schools",
    ),
]

# (claim, should_be_flagged, what the critic is being tested on)
CASES: list[tuple[DraftClaim, bool, str]] = [
    (
        DraftClaim(
            id="t1",
            asset_type="talking_point",
            body=(
                "In a 2025 pilot across six schools, teachers reported about four "
                "hours less lesson prep a week."
            ),
            pillar_id="pillar2",
            evidence_kind="proof_point",
            evidence_proof_point_id="pp2",
        ),
        False,
        "states the proof point exactly — must stay clean",
    ),
    (
        DraftClaim(
            id="t2",
            asset_type="talking_point",
            body="Teachers everywhere get four hours of their week back.",
            pillar_id="pillar2",
            evidence_kind="proof_point",
            evidence_proof_point_id="pp2",
        ),
        True,
        "widens six schools into everywhere",
    ),
    (
        DraftClaim(
            id="t3",
            asset_type="talking_point",
            body=(
                "Kestrel takes the lesson prep off your hands, so a school can run "
                "the same timetable with fewer teaching assistants."
            ),
            pillar_id="pillar1",
            evidence_kind="proof_point",
            evidence_proof_point_id="pp2",
        ),
        True,
        "never-say: Replaces teachers, in different wording",
    ),
    (
        DraftClaim(
            id="s1",
            asset_type="social",
            body="Kestrel lifts reading scores in a single term.",
            pillar_id="pillar2",
            evidence_kind="proof_point",
            evidence_proof_point_id="pp2",
        ),
        True,
        "cites prep time to claim a reading outcome",
    ),
    (
        DraftClaim(
            id="s2",
            asset_type="social",
            body="One price for the whole school. Never per pupil.",
            pillar_id="pillar4",
            evidence_kind="pillar",
            evidence_proof_point_id=None,
        ),
        False,
        "a position resting on its pillar — must stay clean",
    ),
    (
        DraftClaim(
            id="s3",
            asset_type="social",
            body="Kestrel pays for itself within a term.",
            pillar_id="pillar4",
            evidence_kind="pillar",
            evidence_proof_point_id=None,
        ),
        True,
        "never-say: Pays for itself",
    ),
    (
        DraftClaim(
            id="f1",
            asset_type="faq",
            body=(
                "Do we need new devices? No. We checked 14 districts in 2025 and "
                "Kestrel ran on what was already in classrooms."
            ),
            pillar_id="pillar3",
            evidence_kind="proof_point",
            evidence_proof_point_id="pp1",
        ),
        False,
        "states the hardware audit exactly — must stay clean",
    ),
    (
        DraftClaim(
            id="f2",
            asset_type="faq",
            body=(
                "Who approves what pupils see? A teacher does. Kestrel drafts and "
                "the teacher decides what goes to the class."
            ),
            pillar_id="pillar1",
            evidence_kind="pillar",
            evidence_proof_point_id=None,
        ),
        False,
        "restates pillar 1 — must stay clean",
    ),
    (
        DraftClaim(
            id="f3",
            asset_type="faq",
            body=(
                "How much prep time will we save? Around 20 percent of a teacher's "
                "week, guaranteed."
            ),
            pillar_id="pillar2",
            evidence_kind="proof_point",
            evidence_proof_point_id="pp2",
        ),
        True,
        "restates hours as a percentage and guarantees it",
    ),
    (
        DraftClaim(
            id="f4",
            asset_type="faq",
            body="What is Kestrel? A lesson planning tool for schools.",
            pillar_id="pillar1",
            evidence_kind="pillar",
            evidence_proof_point_id=None,
        ),
        False,
        "plain and dull, but true — must not be flagged for being boring",
    ),
]


async def main() -> None:
    claims = [c for c, _, _ in CASES]
    judgements, record = await critique_claims(
        claims=claims, proof_points=PROOF_POINTS, narrative=NARRATIVE
    )

    assert record is not None
    print(
        f"tokens {record.input_tokens}/{record.output_tokens}   "
        f"judged {len(judgements)} of {len(claims)}\n"
    )

    wrong = 0
    for claim, should_flag, what in CASES:
        judgement = judgements.get(claim.id)
        if judgement is None:
            print(f"!! [{claim.id}] no judgement came back — {what}")
            wrong += 1
            continue

        ok = judgement.flagged == should_flag
        wrong += not ok
        mark = "  " if ok else "!!"
        got = "FLAGGED" if judgement.flagged else "clean  "
        print(f"{mark} [{claim.id}] {got}  (expected {'FLAGGED' if should_flag else 'clean'})  {what}")
        print(f"      {claim.body}")
        if judgement.reason:
            print(f"      -> {judgement.reason}")
            # The reason is shown to someone who has never seen a prompt or a
            # database, so an internal id in it is a defect, not a detail.
            leaked = re.findall(r"\b(?:pp\d+|pillar\d+)\b", judgement.reason)
            if leaked:
                print(f"      !! leaks ids: {', '.join(sorted(set(leaked)))}")
                wrong += 1
            words = len(judgement.reason.split())
            if words > 35:
                print(f"      !! {words} words (ceiling 35)")
                wrong += 1
        print()

    print(f"{'=' * 60}\n{wrong} wrong of {len(CASES)}")


if __name__ == "__main__":
    asyncio.run(main())
