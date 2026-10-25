# LittleSteps

A parent-facing developmental screening aid. Parents sign up, add one or more children, and run
short milestone check-ins over time (Yes / Sometimes / Not yet / Not sure) to catch possible
developmental red flags early. It is a **screening aid, not a diagnosis** — every result points
back to "worth discussing with your pediatrician," never a diagnostic claim.

Milestone content is sourced from CDC "Learn the Signs. Act Early." and CDC/WHO growth charts (see
the in-app **Sources** page and `data/milestones.json` / `data/growth/README.md`). Flagging is
fully deterministic (`backend/rules.py`) — an LLM agent pair (`backend/agents.py`, running
`gpt-6-luna` via Portkey) only writes a short, reviewed, plain-English explanation of a result
that's already been decided; it can never add, remove, or change a flag. See `Agents.md` for the
full architecture, hard rules, and design rationale.

## Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy (SQLite), PydanticAI (model calls via Portkey)
- **Frontend:** React + Vite + TypeScript
- **Auth:** bcrypt-hashed passwords, JWT sessions

## Prerequisites

- Python 3.11+ (developed on 3.14)
- Node.js 18+ (developed on 24)
- A Portkey API key with access to the `gpt-6-luna` model (course-issued key works)

## Setup (should take well under 10 minutes)

1. **Clone and enter the project:**
   ```bash
   git clone <this-repo-url>
   cd littlesteps
   ```

2. **Configure environment variables.** Copy the example file and fill in real values:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and set:
   - `JWT_SECRET_KEY` — any random string, e.g. generate one with:
     ```bash
     python3 -c "import secrets; print(secrets.token_hex(32))"
     ```
   - `PORTKEY_API_KEY` — your Portkey API key (course-issued key, restricted to `gpt-6-luna`).

   The app looks for `.env` in this folder (and one level up) automatically — no need to export
   anything manually.

3. **Install backend dependencies and run the API** (from the project root):
   ```bash
   python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
   pip install -r requirements.txt
   python3 -m uvicorn backend.main:app --reload --port 8000
   ```
   Leave this running. It serves the API at `http://localhost:8000` and creates `data/app.db`
   (a local SQLite file) automatically on first run.

4. **Install frontend dependencies and run the dev server** (in a second terminal, from
   `frontend/`):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. **Open the app:** visit **http://localhost:5173**. The frontend proxies `/api/*` requests to
   the backend on port 8000 (see `frontend/vite.config.ts`) — no extra configuration needed.

6. Sign up with any email/password (8+ characters), add a child, and run a check-in.

## Running tests

From the project root (with dependencies installed):
```bash
python3 -m pytest tests/ -v
```
All tests run offline against an in-memory database and a simulated model (`FunctionModel`) — no
real API key or network access is required to run the test suite, and it doesn't touch
`data/app.db` or spend any tokens.

## Project layout

```
backend/        FastAPI app, auth, database models, rules engine, PydanticAI agents
frontend/       React + Vite + TypeScript app
data/           Sourced milestone and growth-chart data (see data/growth/README.md)
skills/         SKILL.md instructions for each agent (source of truth for agent behavior)
tests/          pytest suite (auth, rules, growth, agents, privacy checks)
Agents.md       Full architecture, hard rules, data sourcing, and design decisions
```

## Notes for graders

- `GET /api/analytics/summary` returns real, measured token usage (input/output tokens, model,
  fallback rate) accumulated from actual runs — this is the project's Tokenomics data source.
- The AI explanation pipeline (`backend/agents.py`) fails closed: if the safety-reviewer agent
  rejects a draft, or any error occurs, the app shows fixed, non-generated text instead. This is
  demonstrated in `tests/test_agents.py` with a simulated prompt-injection attempt, and was also
  verified against the live model with a real injected child nickname.
- `Agents.md` documents what's deliberately *not* implemented yet (e.g. vision/hearing and
  school-age behavioral screening) and why — those domains lack a properly licensed data source,
  so the app says so rather than guessing.
