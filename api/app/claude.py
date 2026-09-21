"""The Claude client.

Every call in the product goes through `ask`. It takes a JSON schema and
returns parsed JSON, because each caller needs a specific shape rather than
prose: a verdict here, a set of grounded claims in Phase 4, a per-claim
judgement in Phase 5. The schema is enforced by a forced tool call, which is
more reliable than asking for JSON in the prompt and parsing what comes back.
"""

from functools import lru_cache
from typing import Any

from anthropic import APIError, AsyncAnthropic

from app.config import get_settings


class ClaudeUnavailable(Exception):
    """Claude could not be reached, or answered with something unusable.

    Callers turn this into a plain message. It never means the user's input
    was wrong — that is a refusal, which is a successful call.
    """


@lru_cache
def client() -> AsyncAnthropic:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise ClaudeUnavailable("No Claude API key is configured.")
    return AsyncAnthropic(api_key=settings.anthropic_api_key, max_retries=2)


async def ask(
    *,
    system: str,
    prompt: str,
    schema: dict[str, Any],
    tool_name: str,
    max_tokens: int = 2048,
) -> tuple[dict[str, Any], dict[str, int]]:
    """Return the model's structured answer and its token usage.

    Usage comes back so Phase 7 can bill against the daily cap without
    re-deriving it, and so calls can be logged with their real cost.
    """
    settings = get_settings()

    try:
        message = await client().messages.create(
            model=settings.claude_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            tools=[
                {
                    "name": tool_name,
                    "description": "Return the result in this exact shape.",
                    "input_schema": schema,
                }
            ],
            # Forcing the tool is what makes the shape a guarantee rather than
            # a request. Without it the model may answer in prose instead.
            tool_choice={"type": "tool", "name": tool_name},
        )
    except APIError as e:
        raise ClaudeUnavailable(str(e)) from e

    for block in message.content:
        if block.type == "tool_use" and block.name == tool_name:
            usage = {
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
            }
            return dict(block.input), usage

    raise ClaudeUnavailable("Claude did not return the expected result.")
