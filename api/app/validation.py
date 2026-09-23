"""Pre-flight validation.

A separate Claude call that reads the brief before anything is generated. It
answers one question: can a kit be written from this brief without breaking
the narrative? If not, the product refuses and says why, and no kit is made.

This is deliberately not the same call as generation. Asking one call to both
judge a brief and write from it lets it talk itself into writing something it
should have rejected.
"""

from app.claude import CallRecord, ask
from app.models import Narrative

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["proceed", "refuse"],
            "description": "refuse only if the brief cannot be served on narrative",
        },
        "reason": {
            "type": "string",
            "description": (
                "Empty when proceeding. When refusing: what the brief asks for, "
                "which proof point fails to support it and what it actually "
                "measured, and any never-say rule it breaks. Address the reader "
                "as 'you'. At most 50 words."
            ),
        },
        "fix": {
            "type": "string",
            "description": (
                "Empty when proceeding. When refusing: the smallest concrete "
                "change that would make this brief work, phrased as an "
                "instruction. At most 25 words. No examples, no alternatives "
                "beyond the one or two real options."
            ),
        },
    },
    "required": ["verdict", "reason", "fix"],
}

SYSTEM = """You check marketing briefs for Kestrel Learn before any copy is written.

You are the last gate before generation. Your job is to catch a brief that
cannot be served without breaking the approved narrative, so the team is told
plainly instead of being handed copy they must throw away.

There are exactly three grounds for refusing. There are no others:

1. The brief asks for something on the never-say list.
2. The brief asks for a specific factual claim, such as a number, an outcome or
   a guarantee, that none of the supplied proof points supports.
3. The brief contradicts a pillar.

Before you refuse, name which of those three it is and quote the never-say
entry or pillar you mean. If you cannot, the answer is proceed.

Do not refuse for anything else. In particular:

- Thin evidence is not a refusal. A brief with few proof points, or none, still
  produces a smaller kit whose lines rest on the pillars, plus a list of the
  evidence that was missing. That is the normal, correct outcome.
- A vague brief is not a refusal.
- A brief that merely mentions a difficult topic is not a refusal. Only what it
  asks you to claim matters.
- Who the brief is addressed to is never a ground for refusal. The selected
  audience only sets the tone of the copy. Any reader is allowed: parents,
  influencers, press, anyone. A brief aimed at someone other than the selected
  audience still proceeds.

When you refuse, write for the marketer who wrote the brief. Name the exact
phrase in their brief that is the problem. Name the proof point that fails to
support it and say what that proof point actually measured. Do not hedge, do
not apologise, and do not suggest they try rewording it vaguely. Give them the
one change that would unblock them.

Be brief. This is read on screen by someone who wants to get back to work, not
a memo. Write about their brief and their proof points, not about yourself or
what the system can and cannot do.

When you proceed, leave reason and fix empty."""


def _prompt(
    *,
    brief: str,
    audience: str,
    proof_texts: list[str],
    narrative: Narrative,
) -> str:
    pillars = "\n".join(f"- {p.title}: {p.body}" for p in narrative.pillars)
    never_say = "\n".join(f"- {n}" for n in narrative.never_say)

    if proof_texts:
        proof = "\n".join(f"{i}. {t}" for i, t in enumerate(proof_texts, start=1))
    else:
        proof = "(none supplied)"

    return f"""Approved pillars:
{pillars}

Never say:
{never_say}

Tone to write in: {audience}

The brief:
{brief}

Proof points supplied:
{proof}

Can a kit be written from this brief without breaking the narrative?"""


async def validate_inputs(
    *,
    brief: str,
    audience: str,
    proof_texts: list[str],
    narrative: Narrative,
) -> tuple[bool, str, str, CallRecord]:
    """Return (ok, reason, fix, record). A refusal is a successful call."""
    result, record = await ask(
        phase="validation",
        system=SYSTEM,
        prompt=_prompt(
            brief=brief,
            audience=audience,
            proof_texts=proof_texts,
            narrative=narrative,
        ),
        schema=VERDICT_SCHEMA,
        tool_name="record_verdict",
        max_tokens=1024,
    )

    ok = result.get("verdict") != "refuse"
    reason = (result.get("reason") or "").strip()
    fix = (result.get("fix") or "").strip()

    # A refusal with nothing to show would leave the user staring at a dead end,
    # so treat it as a failed call rather than rendering an empty page.
    if not ok and not reason:
        ok = True

    return ok, reason, fix, record
