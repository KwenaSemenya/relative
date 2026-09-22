"""Relative API.

Reached only by the SvelteKit server over Fly private networking, so there is
no CORS layer and no public surface. Every response is camelCase to match the
types in web/src/lib/types.ts.
"""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app import repo
from app.claude import ClaudeUnavailable
from app.config import get_settings
from app.db import session
from app.drafting import draft_claims
from app.models import Kit, Narrative, Wire
from app.validation import validate_inputs

app = FastAPI(
    title="Relative API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

Db = Annotated[AsyncSession, Depends(session)]


class CreateKit(Wire):
    brief: Annotated[str, Field(min_length=1, max_length=4000)]
    audience: Annotated[str, Field(min_length=1, max_length=64)]
    proof_points: Annotated[list[str], Field(max_length=8)] = []
    sensitive_market: bool = False


class Refusal(Wire):
    """Why nothing was written, and what would unblock it."""

    reason: str
    fix: str


class CreateKitResult(Wire):
    """Either a kit or a refusal, never both.

    A refusal is a normal answer rather than an error: the brief was read, and
    the honest response was to write nothing. The caller keeps every input.
    """

    kit: Kit | None = None
    refusal: Refusal | None = None


class GroupReview(Wire):
    review_state: str


class EditClaim(Wire):
    body: Annotated[str, Field(min_length=1, max_length=4000)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": get_settings().environment}


@app.get("/narrative", response_model=Narrative, response_model_by_alias=True)
async def get_narrative(db: Db) -> Narrative:
    narrative = await repo.get_narrative(db)
    if narrative is None:
        raise HTTPException(status_code=503, detail="The narrative is not seeded yet.")
    return narrative


@app.post(
    "/kits",
    response_model=CreateKitResult,
    response_model_by_alias=True,
)
async def create_kit(body: CreateKit, db: Db) -> CreateKitResult:
    proof_texts = [p.strip() for p in body.proof_points if p.strip()]
    brief = body.brief.strip()

    narrative = await repo.get_narrative(db)
    if narrative is None:
        raise HTTPException(status_code=503, detail="The narrative is not seeded yet.")

    # Pre-flight. Nothing is written, and no row is created, until the brief
    # has been read on its own.
    try:
        ok, reason, fix, _usage = await validate_inputs(
            brief=brief,
            audience=body.audience,
            proof_texts=proof_texts,
            narrative=narrative,
        )
    except ClaudeUnavailable:
        raise HTTPException(
            status_code=503,
            detail="The brief could not be checked just now. Nothing was lost.",
        ) from None

    if not ok:
        return CreateKitResult(refusal=Refusal(reason=reason, fix=fix))

    # Generation happens before the row exists, so a failed call leaves no
    # half-written kit behind for someone to find later.
    try:
        draft, _usage = await draft_claims(
            brief=brief,
            audience=body.audience,
            proof_points=repo.proof_point_ids(proof_texts),
            narrative=narrative,
        )
    except ClaudeUnavailable:
        raise HTTPException(
            status_code=503,
            detail="The kit could not be written just now. Nothing was lost.",
        ) from None

    # Every line was dropped for citing something this kit does not have. A kit
    # of nothing is not a kit, and saying so beats an empty page.
    if not draft.claims:
        raise HTTPException(
            status_code=502,
            detail=(
                "Nothing came back that could be traced to your proof points. "
                "Nothing you typed was lost — try generating again."
            ),
        )

    kit = await repo.create_kit(
        db,
        brief=brief,
        audience=body.audience,
        proof_texts=proof_texts,
        sensitive_market=body.sensitive_market,
        draft=draft,
    )
    return CreateKitResult(kit=kit)


@app.get("/kits/{slug}", response_model=Kit, response_model_by_alias=True)
async def get_kit(slug: str, db: Db) -> Kit:
    kit = await repo.get_kit(db, slug)
    if kit is None:
        raise HTTPException(status_code=404, detail="No kit at that link.")
    return kit


@app.post(
    "/kits/{slug}/groups/{asset_type}/review",
    response_model=Kit,
    response_model_by_alias=True,
)
async def review_group(
    slug: str, asset_type: str, body: GroupReview, db: Db
) -> Kit:
    if body.review_state not in {"pending", "approved", "rejected"}:
        raise HTTPException(status_code=422, detail="Unknown review state.")

    kit = await repo.set_group_review(db, slug, asset_type, body.review_state)
    if kit is None:
        raise HTTPException(status_code=404, detail="No kit at that link.")
    return kit


@app.post(
    "/kits/{slug}/claims/{claim_id}",
    response_model=Kit,
    response_model_by_alias=True,
)
async def edit_claim(slug: str, claim_id: str, body: EditClaim, db: Db) -> Kit:
    # Phase 6 re-runs the critique pass on this line alone and updates its flag
    # state before returning.
    kit = await repo.edit_claim(db, slug, claim_id, body.body.strip())
    if kit is None:
        raise HTTPException(status_code=404, detail="No kit or claim at that link.")
    return kit
