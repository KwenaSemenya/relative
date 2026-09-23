"""Relative API.

Reached only by the SvelteKit server over Fly private networking, so there is
no CORS layer and no public surface. Every response is camelCase to match the
types in web/src/lib/types.ts.
"""

import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app import budget, critique, repo
from app.claude import CallRecord, ClaudeUnavailable
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

# The API sits on Fly's private network, so every request arrives from the
# SvelteKit server and the socket address is always the same one. The visitor's
# address is whatever SvelteKit resolved and forwarded, and it is hashed on
# arrival rather than stored.
Visitor = Annotated[str | None, Header(alias="x-visitor-address")]


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
    """A kit, a refusal, or a limit. Exactly one of the three.

    A refusal is a normal answer rather than an error: the brief was read, and
    the honest response was to write nothing. A limit is not even that — the
    brief was never read, because the demo had nothing left to spend on it.
    Both keep every input the caller typed.
    """

    kit: Kit | None = None
    refusal: Refusal | None = None
    limit: Refusal | None = None


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
async def create_kit(
    body: CreateKit, db: Db, x_visitor_address: Visitor = None
) -> CreateKitResult:
    proof_texts = [p.strip() for p in body.proof_points if p.strip()]
    brief = body.brief.strip()
    proof_points = repo.proof_point_ids(proof_texts)

    # Every call this request makes is collected under one id, so the three of
    # them can be read back together afterwards.
    run_id = str(uuid.uuid4())
    client = budget.client_id(x_visitor_address)
    records: list[CallRecord] = []

    # Asked before the brief is even read, because the cheapest call is the one
    # not made. A limit is not a refusal: nothing was judged, so nothing is
    # said about the brief.
    allowance = await budget.check(db, client)
    if not allowance.ok:
        return CreateKitResult(
            limit=Refusal(reason=allowance.reason, fix=allowance.fix)
        )

    narrative = await repo.get_narrative(db)
    if narrative is None:
        raise HTTPException(status_code=503, detail="The narrative is not seeded yet.")

    # Pre-flight. Nothing is written, and no row is created, until the brief
    # has been read on its own.
    try:
        ok, reason, fix, record = await validate_inputs(
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
    records.append(record)

    if not ok:
        await repo.log_calls(db, records, run_id=run_id, client=client)
        return CreateKitResult(refusal=Refusal(reason=reason, fix=fix))

    # Generation happens before the row exists, so a failed call leaves no
    # half-written kit behind for someone to find later.
    try:
        draft, record = await draft_claims(
            brief=brief,
            audience=body.audience,
            proof_points=proof_points,
            narrative=narrative,
        )
    except ClaudeUnavailable:
        await repo.log_calls(db, records, run_id=run_id, client=client)
        raise HTTPException(
            status_code=503,
            detail="The kit could not be written just now. Nothing was lost.",
        ) from None
    records.append(record)

    # Every line was dropped for citing something this kit does not have. A kit
    # of nothing is not a kit, and saying so beats an empty page.
    if not draft.claims:
        await repo.log_calls(db, records, run_id=run_id, client=client)
        raise HTTPException(
            status_code=502,
            detail=(
                "Nothing came back that could be traced to your proof points. "
                "Nothing you typed was lost — try generating again."
            ),
        )

    # The critique reads the lines without the brief, so it cannot be argued
    # into approving a line by what was asked for. A critique that fails to run
    # is not a reason to lose the kit: the lines are still saved, unflagged,
    # and a kit nobody second-guessed is better than no kit at all.
    try:
        judgements, record = await critique.critique_claims(
            claims=draft.claims,
            proof_points=proof_points,
            narrative=narrative,
        )
        critique.apply(draft.claims, judgements)
        if record:
            records.append(record)
    except ClaudeUnavailable:
        pass

    kit = await repo.create_kit(
        db,
        brief=brief,
        audience=body.audience,
        proof_texts=proof_texts,
        sensitive_market=body.sensitive_market,
        draft=draft,
        records=records,
        run_id=run_id,
        client=client,
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

    try:
        kit = await repo.set_group_review(db, slug, asset_type, body.review_state)
    except repo.SensitiveMarket:
        raise HTTPException(
            status_code=409,
            detail=(
                "This kit is for a sensitive market, so it goes to a named "
                "reviewer before anyone approves it here."
            ),
        ) from None

    if kit is None:
        raise HTTPException(status_code=404, detail="No kit at that link.")
    return kit


@app.post(
    "/kits/{slug}/claims/{claim_id}",
    response_model=Kit,
    response_model_by_alias=True,
)
async def edit_claim(
    slug: str, claim_id: str, body: EditClaim, db: Db, x_visitor_address: Visitor = None
) -> Kit:
    """Re-check one edited line on its own.

    The critique runs over a list of one. It is the same call, the same cold
    context and the same rules as the whole kit got, because an edited line
    that only had to pass a laxer check would be the easiest way to get an
    off-narrative claim into an approved kit.

    An edit is charged against the day's money but not against anyone's five
    generations. Someone fixing a line the critic caught is the product doing
    its job, and charging them for it would push them towards leaving the flag
    on the page instead.
    """
    narrative = await repo.get_narrative(db)
    if narrative is None:
        raise HTTPException(status_code=503, detail="The narrative is not seeded yet.")

    client = budget.client_id(x_visitor_address)
    if await budget.over_cap(db):
        raise HTTPException(
            status_code=429,
            detail=(
                "This demo's daily spending cap is used up, so that line could "
                "not be re-checked. Your wording is still here."
            ),
        )

    context = await repo.get_claim_context(db, slug, claim_id, body.body.strip())
    if context is None:
        raise HTTPException(status_code=404, detail="No kit or claim at that link.")

    run_id = str(uuid.uuid4())
    records: list[CallRecord] = []

    try:
        judgements, record = await critique.critique_claims(
            claims=[context.claim],
            proof_points=context.proof_points,
            narrative=narrative,
        )
    except ClaudeUnavailable:
        # Saving the new wording with the old line's flag would attach a
        # verdict to a sentence that never earned it. Better to keep what the
        # person typed in the box and say the check could not run.
        raise HTTPException(
            status_code=503,
            detail="That line could not be re-checked just now. Your wording is still here.",
        ) from None

    critique.apply([context.claim], judgements)
    if record:
        records.append(record)

    kit = await repo.save_claim_edit(
        db,
        slug,
        kit_id=context.kit_id,
        claim=context.claim,
        records=records,
        run_id=run_id,
        client=client,
    )
    if kit is None:
        raise HTTPException(status_code=404, detail="No kit or claim at that link.")
    return kit
