"""Loads the seeded Kestrel Learn narrative and worked example kit.

The JSON in app/seed/ is generated from the SvelteKit fixtures so the two
cannot drift by transcription error. Phase 2 makes Postgres the source of
truth and these files become the migration seed.
"""

from functools import lru_cache
from pathlib import Path

from app.models import Kit, Narrative

SEED_DIR = Path(__file__).parent / "seed"


@lru_cache
def narrative() -> Narrative:
    return Narrative.model_validate_json((SEED_DIR / "narrative.json").read_text())


@lru_cache
def example_kit() -> Kit:
    return Kit.model_validate_json((SEED_DIR / "example-kit.json").read_text())
