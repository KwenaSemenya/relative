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
from app.config import get_settings
from app.db import session
from app.models import Kit, Narrative, Wire

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
    "/kits", response_model=Kit, response_model_by_alias=True, status_code=201
)
async def create_kit(body: CreateKit, db: Db) -> Kit:
    proof_texts = [p.strip() for p in body.proof_points if p.strip()]
    return await repo.create_kit(
        db,
        brief=body.brief.strip(),
        audience=body.audience,
        proof_texts=proof_texts,
        sensitive_market=body.sensitive_market,
    )


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
