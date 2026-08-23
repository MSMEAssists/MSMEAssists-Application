# MSMEAssist — Module 1: Business Profile & Eligibility Engine

Part of *An Agentic AI-Powered Intelligent Decision Support Framework for Government Service Intelligence and Sustainable MSME Growth*.

This repository contains **Module 1 only**: user auth, the 7-step business profile onboarding wizard, the completeness/eligibility engine, and document metadata management. Module 2 (government scheme discovery) is a separate service that consumes Module 1 exclusively through the REST contract documented in `docs/module-2-integration.md`.

> **Implementation status:** both the Module 1 **backend** (51 passing tests) and **frontend** are implemented and wired together against the real API — no mock data. Module 2 is out of scope entirely; only a placeholder route (`/schemes`) exists so the "Discover Government Schemes" button has somewhere to go. See `docs/module-2-integration.md` for the contract Module 2 will eventually consume.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite, Tailwind CSS, React Router, Axios, React Icons, Framer Motion |
| Backend | FastAPI, Python 3.11+, Pydantic, Motor (async PyMongo) |
| Database | MongoDB |
| Auth | JWT, hashed passwords (bcrypt/argon2) |
| Storage | Configurable adapter — local disk (dev) or S3-compatible (prod) |

---

## Repository layout

```
module-1/
├── backend/            # FastAPI app — see docs/architecture.md §2
├── frontend/            # React + Vite app
├── docs/
│   ├── architecture.md         # full system design: diagram, schema, routes, workflow
│   ├── module-1-api.md          # request/response schema for every endpoint
│   └── module-2-integration.md  # the stable contract Module 2 consumes
├── .env.example                 # backend env vars template
└── README.md
```

## Documentation index

- **`docs/architecture.md`** — architecture diagram, folder structure, database schema, frontend routes, Git strategy, environment variables, and dev workflow.
- **`docs/module-1-api.md`** — full API reference for `/api/auth/*`, `/api/profile/*`, `/api/profile/documents/*`.
- **`docs/module-2-integration.md`** — the contract Module 2 is built against. Read this before touching any profile schema.

---

## Getting started — backend

```bash
git clone <repo-url>
cd msmeassist/module-1/backend

cp .env.example .env          # then edit JWT_SECRET_KEY at minimum
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

MongoDB: run locally via `docker run -p 27017:27017 mongo:7`, or point `MONGO_URI` in `.env` at a hosted instance.

Once running:
- Interactive API docs (Swagger UI): `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Raw OpenAPI schema: `http://localhost:8000/openapi.json`
- Health check: `http://localhost:8000/health`

### Running tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```

Tests need **no real MongoDB** — `tests/conftest.py` wires every integration test to an in-memory Mongo (`mongomock-motor`) and an isolated temp directory for document storage, so the suite is fully self-contained. 51 tests currently pass: 26 unit tests (completeness engine, eligibility engine, masking/formatting, validators) and 25 integration tests covering every endpoint's success and error paths, including cross-user isolation (`test_profile_is_isolated_per_user`, `test_user_cannot_delete_another_users_document`) and the read-only `msme_classification` field guard.

## Getting started — frontend

```bash
cd msmeassist/module-1/frontend
cp .env.example .env          # VITE_API_BASE_URL defaults to http://localhost:8000/api
npm install
npm run dev
```

Runs at `http://localhost:5173` by default. The backend must be running first (see above) — the frontend makes real calls to it for every core flow (register, login, profile CRUD, document upload); nothing is mocked.

### What's implemented

- **Auth**: Login, Registration, JWT persisted in `localStorage`, protected routes that redirect to `/login` and back.
- **7-step onboarding wizard**: Business → Location → Financial → Characteristics → Registrations → Documents → Review, each step reading from and writing to the real `GET/POST/PUT /api/profile/me` endpoints.
- **Save draft / resume later**: every step's "Continue" and "Save & Exit" persist to the backend immediately (no local-only draft state). On next login, `/` (`RootRedirect`) fetches the real profile and routes the user to their first incomplete step, or straight to the completed state if they already finished.
- **Live profile completeness**: the sidebar widget and Review step both read `completeness` straight off the API response — nothing is computed client-side.
- **Document upload**: drag-and-drop, real `multipart/form-data` upload with progress, backed by `POST/GET/DELETE /api/profile/documents`.
- **Completed state**: reads the real completeness percentage, section counts, and document count.
- **Module 2 boundary respected**: "Discover Government Schemes →" only navigates to a `/schemes` placeholder page — no scheme logic, no Module 2 code.

Responsive down to mobile: the onboarding two-column layout collapses to a single column below `lg`, the auth split-screen collapses below `md`, and all forms/cards reflow to single-column below `sm`.

---

## Working across modules

Developer A owns `module-1/`. Developer B owns `module-2/` (separate folder or separate repo — see `docs/architecture.md` §7). The only shared surface is `docs/module-1-api.md` and `docs/module-2-integration.md`; both are `CODEOWNERS`-protected and require sign-off from both developers before merging a change that touches the profile response shape.

## Scope boundary for this module

Module 1 handles: authentication, business profile CRUD, completeness scoring, eligibility attribute derivation, and document upload/status metadata.

Module 1 does **not** handle: document content verification, scheme matching/recommendation, or any RAG/retrieval logic — those are Module 2's responsibility and are intentionally kept out of this codebase.
