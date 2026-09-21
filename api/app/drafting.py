"""Turning a brief and its proof points into claims.

Phase 4 replaces the body of `draft_claims` with a single Claude call that
returns a cited proof point and a pillar per claim. Everything around it — the
persistence, the slug, the evidence requests — is already in its final shape,
so only this function changes.

Until then it returns the seeded worked example, which is honest about being a
placeholder rather than pretending to have read the brief.
"""

from dataclasses import dataclass, field

from app import seed


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
    evidence_requests: list[tuple[str, str, str]] = field(default_factory=list)


def draft_claims(brief: str, audience: str, proof_points: list[str]) -> Draft:
    example = seed.example_kit()

    claims: list[DraftClaim] = []
    for group in example.groups:
        for claim in group.claims:
            evidence_kind = claim.evidence.kind if claim.evidence else None
            claims.append(
                DraftClaim(
                    id=claim.id,
                    asset_type=claim.asset_type,
                    body=claim.body,
                    pillar_id=claim.pillar_id,
                    evidence_kind=evidence_kind,
                    evidence_proof_point_id=(
                        claim.evidence.id if evidence_kind == "proof_point" else None
                    ),
                    flag_state=claim.flag_state,
                    flag_reason=claim.flag_reason,
                )
            )

    return Draft(
        claims=claims,
        evidence_requests=[(r.id, r.need, r.why) for r in example.evidence_requests],
    )
