"""Relative API.

Reached only by the SvelteKit server over Fly private networking, so there is
no CORS layer and no public surface. Every response is camelCase to match the
types in web/src/lib/types.ts.
"""

from fastapi import FastAPI, HTTPException

from app import seed
from app.config import get_settings
from app.models import Kit, Narrative

app = FastAPI(
    title="Relative API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": get_settings().environment}


@app.get("/narrative", response_model=Narrative, response_model_by_alias=True)
def get_narrative() -> Narrative:
    return seed.narrative()


@app.get("/kits/{slug}", response_model=Kit, response_model_by_alias=True)
def get_kit(slug: str) -> Kit:
    # Phase 2 replaces this with a Postgres lookup; the example kit becomes a
    # seeded row rather than the only kit that exists.
    kit = seed.example_kit()
    if slug != kit.slug:
        raise HTTPException(status_code=404, detail="No kit at that link.")
    return kit
