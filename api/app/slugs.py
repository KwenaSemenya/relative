"""Kit slugs.

The slug is the access control: anyone holding the link can open the kit, and
nobody else can guess it. So the readable half is cosmetic and the random half
has to carry all the entropy. Six hex characters over a namespace this small
is not brute-forceable at any rate a rate limit would allow.
"""

import re
import secrets

# The design's worked example is "emea-spring-2f41".
_WORD = re.compile(r"[a-z]{3,12}")
_STOPWORDS = frozenset(
    """a an and are as at be by for from has have in is it its of on or that the
    this to was were will with our your their we you they how what when who""".split()
)

RANDOM_LEN = 6


def _words(brief: str, limit: int = 2) -> list[str]:
    seen: list[str] = []
    for word in _WORD.findall(brief.lower()):
        if word in _STOPWORDS or word in seen:
            continue
        seen.append(word)
        if len(seen) == limit:
            break
    return seen


def make_slug(brief: str) -> str:
    """A readable stem from the brief, plus enough randomness to be unguessable."""
    stem = "-".join(_words(brief)) or "kit"
    return f"{stem}-{secrets.token_hex(RANDOM_LEN // 2)}"
