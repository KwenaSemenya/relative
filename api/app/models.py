"""Pydantic mirrors of web/src/lib/types.ts.

Keep the two in step: the SvelteKit app is the only consumer of this API and it
types every response against those interfaces. Fields are snake_case in Python
and camelCase on the wire.
"""

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

AssetType = Literal["talking_point", "social", "faq"]
ReviewState = Literal["pending", "approved", "rejected"]
FlagState = Literal["clean", "flagged"]

AUDIENCES = ["Educators", "Students", "Institutions", "Influencers"]


class Wire(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Pillar(Wire):
    id: str
    title: str
    body: str


class Narrative(Wire):
    label: str
    sensitive_reviewer: str
    pillars: list[Pillar]
    never_say: list[str]


class ProofPoint(Wire):
    id: str
    text: str


class ProofPointRef(Wire):
    kind: Literal["proof_point"]
    id: str


class PillarRef(Wire):
    kind: Literal["pillar"]
    id: str


# A claim cites exactly one source. Flagged claims cite nothing — that is
# precisely why they are flagged.
EvidenceRef = Union[
    Annotated[Union[ProofPointRef, PillarRef], Field(discriminator="kind")], None
]


class Claim(Wire):
    id: str
    asset_type: AssetType
    body: str
    pillar_id: str | None
    evidence: EvidenceRef
    flag_state: FlagState
    flag_reason: str | None
    edited_at: str | None


class EvidenceRequest(Wire):
    id: str
    need: str
    why: str


class AssetGroup(Wire):
    asset_type: AssetType
    title: str
    short_name: str
    review_state: ReviewState
    claims: list[Claim]


class Kit(Wire):
    slug: str
    brief: str
    audience: str
    sensitive_market: bool
    created_at: str
    proof_points: list[ProofPoint]
    groups: list[AssetGroup]
    evidence_requests: list[EvidenceRequest]
