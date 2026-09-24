# Relative

Turn one approved brand narrative into on-message assets, with every line traced back to a proof point.

**Live: [relative-web.fly.dev](https://relative-web.fly.dev)** — in private testing, so it asks for a password. Ask me for one, or run it locally with the steps below.

A regional marketing team has an HQ-approved narrative and a deadline. They need talking points, social copy and an FAQ that say the same thing HQ signed off on. Relative writes that kit from a brief, cites the evidence behind each line, flags the lines that drift, and hands the decision to a person.

The demo runs against a fictional ed-tech company, Kestrel Learn. There is no sign-in: a kit lives at `/k/<slug>` and the link is the only access control.

## What it actually does

A generate is three separate Claude calls, not one prompt doing three jobs.

| Call | Sees | Job |
| --- | --- | --- |
| Validation | Brief, proof points, narrative | Decide whether there is enough here to write from. Refuse in plain words if not. |
| Drafting | Brief, audience, proof points, narrative | Write every asset type in one pass. Each line must name the proof point or pillar it rests on. |
| Critique | The finished lines, proof points, narrative | Say which lines are not supported by the source printed next to them. |

**The critique call never sees the brief.** That is the whole point of the pass, and it is enforced by structure rather than by instruction: [`critique.py`](api/app/critique.py) has no parameter a brief could arrive through. A critic who knows what was asked for starts reading for intent, and "they were clearly going for X" is how a line that overstates its evidence gets waved past. Reading cold, the only question left is whether the line holds up — which is the question a reader of the kit will ask.

The audience is withheld for the same reason. Tone is not a defence for a claim the evidence does not carry.

## The narrative is the constraint

Four pillars, seeded and not user-editable:

1. Teachers stay in charge
2. Evidence before claims
3. Runs on what schools already own
4. One price per school

Plus a never-say list: *guaranteed results, replaces teachers, raises test scores by X%, the only platform that…, pays for itself.*

A flagged line gets a reason, not a score. When a claim needs evidence nobody has supplied, the kit raises an evidence request instead of quietly dropping the line.

## The review loop

Assets are approved or rejected as a group, because that is the unit a person actually signs off. Any single line can be rewritten in place, and the edit is re-checked by the same cold critique the whole kit got — so the flag that comes back belongs to the new wording, not the sentence it replaced. Re-checks can come back still flagged, and the interface says so.

Kits marked **sensitive market** cannot be approved here at all. They go to a named reviewer first, and the API refuses the approval rather than the interface merely hiding the button.

## Cost control

This is a public page with no accounts wired to a real API key, so it has two limits: five generates per visitor and $5 a day across everyone. Both are counted from `claude_call`, the table that already records real token usage, so the cap cannot drift away from the bill the way a separate counter would once a retry or a crash lands between them. Visitors are recognised by a blake2b hash of their address; the address itself is never stored.

Hitting a limit is not an error and not a refusal. Nothing was read, so nothing is said about the brief: the worked example stays on screen, the typed brief is kept, and the notice says which limit was hit and when it lifts.

Measured cost is about $0.02 a generate. `scripts/show_spend.py` prices spend the same way the cap does.

## Stack

One tool per layer.

- **Web** — SvelteKit 2, Svelte 5 runes, Tailwind v4, `adapter-node` for SSR
- **API** — FastAPI, Pydantic v2, SQLAlchemy 2 async
- **Data** — PostgreSQL on Neon, migrated with Alembic
- **Model** — Claude Sonnet, forced tool calls for every structured response
- **Hosting** — Fly.io, `relative-web` public and `relative-api` on private networking only

## Running it

Two processes. The web server talks to the API over HTTP, so start the API first.

```bash
# API — needs RELATIVE_DATABASE_URL and RELATIVE_ANTHROPIC_API_KEY in api/.env
cd api
uv sync
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed_db
.venv/bin/uvicorn app.main:app --port 8099
```

```bash
# Web — reads RELATIVE_API_URL, defaults to http://localhost:8099
cd web
npm install
npm run dev
```

The demo switcher along the top plays eight scripted states — landing, refusal, generating, edited line, sensitive market, budget spent, partial, complete — entirely in the browser. No API calls, so you can see every state the interface has without spending anything.

## Reading back what happened

There is no HTTP endpoint for this. The kit link is the only access control this product has, and raw prompts are not something to hand out at the same URL as the copy.

```bash
cd api
.venv/bin/python scripts/show_calls.py          # recent runs
.venv/bin/python scripts/show_calls.py <slug>   # one kit, end to end
.venv/bin/python scripts/show_spend.py          # cost per day
```

`show_calls.py` with a slug also verifies the one thing the critique pass promises: that the brief never reached it.

## Data model

`narrative` holds the pillars and the never-say list. A `kit` owns its `proof_point` rows and its `claim` rows, and every claim carries the proof point or pillar it cites, its flag state and reason, and its review state. `evidence_request` records the gaps. `claude_call` logs every call with its raw response and real token usage, which is what both the audit trail and the spending cap are built on.

Claims use a composite key of `(kit_id, id)`, so an id stays readable — `t1`, `s2` — while remaining scoped to its kit.

## Deliberately not built

No auth, no accounts. No slide decks, no publishing or scheduling. No live retrieval or web search: the proof points a person supplies are the only evidence. No rich text editing, no streaming, no PDF export. No separate prompts per audience or asset type — audience is a parameter, not a fork. No narrative setup screen; the narrative is seeded, because a narrative anyone can edit is not approved.
