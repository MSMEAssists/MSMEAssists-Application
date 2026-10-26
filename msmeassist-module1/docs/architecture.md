# MSMEAssist — Module 1 Technical Architecture
### Business Profile & Eligibility Engine

Status: **Architecture only — no implementation yet.**
Scope: Module 1 exclusively. Module 2 (scheme discovery / recommendation) is out of scope and interacts with Module 1 only through the documented API contract in `module-2-integration.md`.

---

## 1. Architecture Diagram

```
┌───────────────────────────────────────────────────────────────────────────┐
│                              CLIENT (Browser)                             │
│  React 18 + Vite SPA                                                      │
│  Pages → Layouts → Components   |  Axios client  |  Auth Context          │
└───────────────────────────────────────────┬───────────────────────────────┘
                                              │ HTTPS (JSON, JWT Bearer)
                                              ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI APPLICATION (Module 1)                    │
│                                                                             │
│  ┌────────────────────────────  API LAYER  ────────────────────────────┐ │
│  │  routers/auth.py   routers/profile.py   routers/documents.py         │ │
│  │  — request/response validation only (Pydantic schemas), no logic     │ │
│  └────────────────────────────────┬───────────────────────────────────┘ │
│                                    ▼                                      │
│  ┌─────────────────────────  SERVICE LAYER  ───────────────────────────┐ │
│  │  auth_service.py        — registration, login, token issuance        │ │
│  │  profile_service.py     — profile create/update, normalization       │ │
│  │  completeness_service.py— weighted section-completeness calculation  │ │
│  │  eligibility_service.py — derives eligibility attribute flags        │ │
│  │  document_service.py    — upload orchestration, status transitions   │ │
│  └───────┬───────────────────────┬────────────────────┬────────────────┘ │
│          ▼                       ▼                    ▼                  │
│  ┌───────────────┐   ┌────────────────────┐   ┌──────────────────────┐   │
│  │ REPOSITORY     │   │ STORAGE ADAPTER    │   │ SECURITY / CORE      │   │
│  │ LAYER          │   │ (interface)        │   │ - JWT issue/verify   │   │
│  │ user_repo.py   │   │ local_disk_driver  │   │ - password hashing   │   │
│  │ profile_repo.py│   │ s3_compatible_drv  │   │ - settings (env)     │   │
│  │ document_repo.py│  │  (swap via config) │   │ - logging            │   │
│  └───────┬────────┘   └──────────┬─────────┘   └───────────────────────┘   │
└──────────┼───────────────────────┼──────────────────────────────────────┘
           ▼                       ▼
 ┌───────────────────┐   ┌────────────────────────────┐
 │ MongoDB            │   │ Document Storage            │
 │ - users             │   │ (configurable: local disk    │
 │ - business_profiles │   │  in dev, S3 / Azure Blob /   │
 │ - documents          │   │  GCS-compatible in prod)    │
 │ - profile_audit_logs │   │  Only metadata is stored in  │
 │                      │   │  MongoDB `documents`         │
 └───────────────────────┘   └────────────────────────────┘

                     ▲
                     │  documented, versioned REST contract only
                     │  (no shared DB access, no internal imports)
┌────────────────────┴────────────────────────────────────────────┐
│                Module 2 (Scheme Discovery — separate service)    │
│         Consumes: GET /api/profile/me, /completeness, /eligibility │
└────────────────────────────────────────────────────────────────┘
```

**Key architectural decisions**

| Decision | Rationale |
|---|---|
| Layered backend (API → Service → Repository) | Keeps route handlers thin; business logic (completeness scoring, eligibility derivation) is testable in isolation from HTTP. |
| Storage behind an adapter interface | `STORAGE_BACKEND` env var switches between local disk (dev) and S3-compatible object storage (prod) without touching service code. |
| Completeness & Eligibility as dedicated services | Both are read heavily by Module 2. Isolating them lets their logic evolve (e.g., new weighting rules) without touching profile CRUD. |
| Module 2 talks HTTP only | No shared MongoDB access, no shared Python packages between modules. Enforces the "stable contract" requirement and lets Developer A and Developer B ship independently. |
| JWT stateless auth | No server-side session store needed; horizontally scalable; every service call carries its own identity. |

---

## 2. Folder Structure

### Backend (`/backend`)

```
backend/
├── app/
│   ├── main.py                     # FastAPI app factory, middleware, router registration
│   ├── core/
│   │   ├── config.py                # Pydantic Settings — reads env vars
│   │   ├── security.py              # JWT encode/decode, password hashing (bcrypt/argon2)
│   │   ├── logging.py               # structured logging setup
│   │   └── constants.py             # enums: BusinessType, RegistrationStatus, etc.
│   ├── api/
│   │   └── v1/
│   │       ├── deps.py              # get_current_user, get_db, pagination deps
│   │       └── routers/
│   │           ├── auth.py
│   │           ├── profile.py
│   │           └── documents.py
│   ├── schemas/                     # Pydantic request/response models
│   │   ├── auth_schema.py
│   │   ├── profile_schema.py
│   │   ├── document_schema.py
│   │   └── common_schema.py         # shared enums, pagination, error envelope
│   ├── models/                      # Mongo document models (Pydantic + BSON helpers)
│   │   ├── user_model.py
│   │   ├── profile_model.py
│   │   ├── document_model.py
│   │   └── audit_log_model.py
│   ├── services/                    # business logic — the only layer allowed to reason about rules
│   │   ├── auth_service.py
│   │   ├── profile_service.py
│   │   ├── completeness_service.py
│   │   ├── eligibility_service.py
│   │   └── document_service.py
│   ├── repositories/                # data-access only, no business rules
│   │   ├── base_repository.py
│   │   ├── user_repository.py
│   │   ├── profile_repository.py
│   │   ├── document_repository.py
│   │   └── audit_log_repository.py
│   ├── storage/                     # configurable document storage adapters
│   │   ├── base_storage.py          # abstract interface: save, get_url, delete
│   │   ├── local_storage.py
│   │   └── s3_storage.py
│   ├── db/
│   │   ├── mongo_client.py          # Motor async client, connection lifecycle
│   │   └── indexes.py               # index creation run at startup
│   └── utils/
│       ├── validators.py            # PIN code, GSTIN, PAN format checks
│       ├── formatters.py            # INR formatting, masking helpers
│       └── exceptions.py            # domain exceptions → HTTP mapping
├── tests/
│   ├── unit/                        # service-layer tests, mocked repositories
│   └── integration/                 # API tests against a test Mongo instance
├── requirements.txt
├── .env.example
└── Dockerfile
```

### Frontend (`/frontend`)

```
frontend/
├── src/
│   ├── main.jsx
│   ├── App.jsx                       # router + global providers
│   ├── routes/
│   │   └── index.jsx                 # route table (see §5)
│   ├── layouts/
│   │   ├── AuthLayout.jsx            # split-screen hero + card (Login/Register)
│   │   ├── OnboardingLayout.jsx      # topbar + wizard aside/main
│   │   └── AppLayout.jsx             # shared app chrome (post-auth)
│   ├── pages/
│   │   ├── auth/
│   │   │   ├── LoginPage.jsx
│   │   │   └── RegisterPage.jsx
│   │   ├── onboarding/
│   │   │   ├── BusinessStep.jsx
│   │   │   ├── LocationStep.jsx
│   │   │   ├── FinancialStep.jsx
│   │   │   ├── CharacteristicsStep.jsx
│   │   │   ├── RegistrationsStep.jsx
│   │   │   ├── DocumentsStep.jsx
│   │   │   └── ReviewStep.jsx
│   │   └── ProfileCompletedPage.jsx
│   ├── components/
│   │   ├── ui/                       # Button, Input, Select, Switch, Badge, Card
│   │   ├── wizard/                   # StepRail, CompletenessWidget, AiTipCard
│   │   └── documents/                # UploadZone, DocumentCard
│   ├── services/                     # Axios wrappers, one file per API resource
│   │   ├── apiClient.js              # axios instance, interceptors (JWT, 401 handling)
│   │   ├── authService.js
│   │   ├── profileService.js
│   │   └── documentService.js
│   ├── context/
│   │   ├── AuthContext.jsx           # user, token, login/logout
│   │   └── OnboardingContext.jsx     # in-progress form state across steps
│   ├── hooks/
│   │   ├── useAuth.js
│   │   ├── useProfile.js
│   │   ├── useCompleteness.js
│   │   └── useDocumentUpload.js
│   ├── utils/
│   │   ├── validators.js
│   │   ├── formatters.js             # INR formatting, masking
│   │   └── constants.js              # mirrors backend enums
│   └── assets/
├── tailwind.config.js
├── vite.config.js
├── .env.example
└── package.json
```

---

## 3. Database Schema (MongoDB)

### 3.1 `users`

| Field | Type | Required | Notes |
|---|---|---|---|
| `_id` | ObjectId | yes | primary key |
| `full_name` | string | yes | |
| `email` | string | yes | unique, lowercase-normalized |
| `mobile_number` | string | yes | unique, E.164-ish stored as string |
| `password_hash` | string | yes | bcrypt/argon2 hash, never returned in any response |
| `role` | string | yes | enum: `msme_owner` (default), `admin` |
| `is_active` | bool | yes | default `true` |
| `is_verified` | bool | no | email/mobile verification flag, default `false` |
| `created_at` | datetime | yes | |
| `updated_at` | datetime | yes | |
| `last_login_at` | datetime | no | |

**Indexes**
- `email` — unique
- `mobile_number` — unique

**Validation rules**
- `email` matches RFC-basic email regex.
- `mobile_number` matches `^\+91[6-9]\d{9}$` (configurable per country later).
- `password_hash` is never exposed via any schema — enforced by a dedicated `UserPublic` Pydantic response model that excludes it at the type level, not just by field-filtering at runtime.

---

### 3.2 `business_profiles`

One document per user (1:1), referencing `users._id`.

| Field | Type | Required | Notes |
|---|---|---|---|
| `_id` | ObjectId | yes | |
| `user_id` | ObjectId | yes | FK → `users._id`, unique |
| `business.name` | string | yes | |
| `business.type` | string | yes | enum: `manufacturing`, `services`, `trading`, `other` |
| `business.industry` | string | yes | |
| `business.sub_sector` | string | no | |
| `business.established_date` | date | yes | |
| `business.description` | string | no | |
| `location.state` | string | yes | |
| `location.district` | string | yes | |
| `location.city` | string | yes | |
| `location.pin_code` | string | yes | 6-digit, regex-validated |
| `location.area_type` | string | yes | enum: `rural`, `urban` |
| `location.premises_type` | string | no | enum: `own`, `rented`, `industrial_estate`, `shared` |
| `financial.annual_turnover_inr` | number | yes | stored as integer paise or plain rupees (decimal128 recommended) |
| `financial.investment_inr` | number | yes | |
| `financial.employee_count` | int | yes | |
| `financial.has_existing_loan` | bool | no | |
| `financial.has_bank_finance` | bool | no | |
| `financial.profitability_status` | string | no | enum: `profitable`, `break_even`, `loss` |
| `financial.msme_classification` | string | derived | enum: `micro`, `small`, `medium` — computed server-side from turnover/investment against current Udyam thresholds, not user-editable |
| `characteristics.is_women_owned` | bool | no | default `false` |
| `characteristics.social_category` | string | no | enum: `general`, `sc`, `st`, `obc`, `other` |
| `characteristics.is_first_gen_entrepreneur` | bool | no | |
| `characteristics.is_startup_recognized` | bool | no | |
| `characteristics.is_rural_enterprise` | bool | no | |
| `characteristics.exports_currently` | bool | no | |
| `characteristics.export_intent` | bool | no | |
| `characteristics.is_tech_oriented` | bool | no | |
| `characteristics.is_sustainable` | bool | no | |
| `registrations` | array of objects | yes (array may be empty) | see sub-schema below |
| `completeness.percentage` | int | derived | 0–100, recomputed on every write by `completeness_service` |
| `completeness.sections` | object | derived | per-section boolean/percentage breakdown |
| `status` | string | yes | enum: `draft`, `submitted`, `active` |
| `created_at` | datetime | yes | |
| `updated_at` | datetime | yes | |

`registrations[]` sub-document:

| Field | Type | Required | Notes |
|---|---|---|---|
| `type` | string | yes | enum: `udyam`, `gst`, `pan`, `fssai`, `iec`, `factory_license`, `trade_license`, `pollution_noc`, `other` |
| `status` | string | yes | enum: `registered`, `not_registered`, `in_progress`, `not_applicable` |
| `identifier` | string | no | raw value stored encrypted-at-rest; **only a masked form is ever returned by the API** |
| `verified_at` | datetime | no | |

**Indexes**
- `user_id` — unique
- `location.state`, `location.district` — compound, supports future Module 2 geo filtering
- `financial.msme_classification` — supports eligibility queries
- `registrations.type` — multikey index for "who has registration X" queries

**Validation rules**
- `location.pin_code` — regex `^\d{6}$`.
- `financial.annual_turnover_inr`, `financial.investment_inr` — non-negative.
- `financial.employee_count` — non-negative integer.
- `msme_classification` is **never** accepted as client input — always server-derived to prevent spoofed eligibility.
- Identifiers (`GSTIN`, `PAN`, `Udyam number`) are format-validated via regex in `utils/validators.py` before storage.

**Relationship:** `business_profiles.user_id` → `users._id` (one-to-one, enforced by unique index).

---

### 3.3 `documents`

| Field | Type | Required | Notes |
|---|---|---|---|
| `_id` | ObjectId | yes | |
| `user_id` | ObjectId | yes | FK → `users._id` |
| `profile_id` | ObjectId | yes | FK → `business_profiles._id` |
| `document_type` | string | yes | enum: `udyam_certificate`, `gst_certificate`, `pan_card`, `factory_license`, `trade_license`, `other` |
| `file_name` | string | yes | original filename |
| `mime_type` | string | yes | enum: `application/pdf`, `image/jpeg`, `image/png` |
| `size_bytes` | int | yes | max enforced at API layer (e.g., 10 MB) |
| `storage_backend` | string | yes | enum: `local`, `s3` — records which adapter stored it |
| `storage_key` | string | yes | path/key in the storage backend; never exposed raw to frontend, only via signed/served URL |
| `status` | string | yes | enum: `uploading`, `uploaded`, `pending_review`, `verified`, `rejected` |
| `rejection_reason` | string | no | populated when `status = rejected` |
| `uploaded_at` | datetime | yes | |
| `updated_at` | datetime | yes | |

**Indexes**
- `user_id` — supports "list my documents"
- `profile_id, document_type` — compound, supports "does profile have X document"

**Validation rules**
- `mime_type` restricted to PDF/JPG/JPEG/PNG at both frontend and API layer (defense in depth).
- `size_bytes` capped by `MAX_UPLOAD_SIZE_MB` env var.
- Module 1 stores and tracks status metadata only — **no verification logic is implemented here**, per scope.

**Relationships:** `documents.user_id` → `users._id`; `documents.profile_id` → `business_profiles._id` (many-to-one).

---

### 3.4 `profile_audit_logs` (optional, recommended for a government-facing product)

| Field | Type | Required | Notes |
|---|---|---|---|
| `_id` | ObjectId | yes | |
| `user_id` | ObjectId | yes | |
| `profile_id` | ObjectId | yes | |
| `action` | string | yes | enum: `created`, `updated`, `document_uploaded`, `document_deleted`, `submitted` |
| `changed_fields` | array of string | no | dot-paths of fields touched, e.g. `financial.annual_turnover_inr` |
| `previous_values` | object | no | shallow snapshot, only for changed fields |
| `actor` | string | yes | `self` or admin user id, for future admin edits |
| `ip_address` | string | no | |
| `created_at` | datetime | yes | |

**Indexes**
- `profile_id, created_at` — compound, supports chronological audit trail per profile.

**Purpose:** government-facing platforms are expected to show provenance of data changes; this collection is append-only and never mutated.

---

## 4. API List

Full request/response schemas are in **`docs/module-1-api.md`**. Summary:

**Authentication**
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`

**Profile**
- `GET /api/profile/me`
- `POST /api/profile/me` (create — first-time)
- `PUT /api/profile/me` (update — partial, section-aware)
- `GET /api/profile/completeness`
- `GET /api/profile/eligibility`

**Documents**
- `POST /api/profile/documents`
- `GET /api/profile/documents`
- `DELETE /api/profile/documents/{document_id}`

All endpoints except `register` and `login` require `Authorization: Bearer <JWT>`.

---

## 5. Frontend Route Structure

```
/                              → redirect to /login or /onboarding based on auth+profile state
/login                         → LoginPage            (AuthLayout)
/register                      → RegisterPage         (AuthLayout)

/onboarding                    → OnboardingLayout (guarded: requires auth)
  /onboarding/business          → BusinessStep          (step 1)
  /onboarding/location          → LocationStep          (step 2)
  /onboarding/financial         → FinancialStep         (step 3)
  /onboarding/characteristics   → CharacteristicsStep   (step 4)
  /onboarding/registrations     → RegistrationsStep     (step 5)
  /onboarding/documents         → DocumentsStep         (step 6)
  /onboarding/review            → ReviewStep            (step 7)

/profile/completed             → ProfileCompletedPage  (AppLayout, guarded)

*                               → NotFoundPage
```

**Route guards**
- `RequireAuth` wrapper — redirects to `/login` if no valid token.
- `RequireProfileDraft` — onboarding routes redirect to `/profile/completed` if `status === "active"` and completeness is already ≥ the platform's minimum threshold, unless the user explicitly clicks "Edit" from Review.
- Step order is enforced client-side by `OnboardingContext` (can't jump to `documents` before `business` on first run), but direct navigation to any step is allowed once a profile exists, since the mockup's step-rail supports free navigation.

---

## 6. Module 2 Integration Contract

See **`docs/module-2-integration.md`** for the full, versioned response contract. Summary of the guarantee:

- Module 2 is given **one stable read contract**: `GET /api/profile/me` (plus `/completeness` and `/eligibility` as focused sub-resources).
- The response is a **normalized DTO**, not a raw Mongo document — internal field names, storage details, and identifiers are never leaked.
- Contract changes are additive-only within a version (`v1`); breaking changes require a `v2` route.

---

## 7. Git Collaboration Strategy

**Repository shape:** a single monorepo is acceptable *if* module boundaries are enforced by folder + API, not by convention alone:

```
msmeassist/
├── module-1/            # Developer A owns this — backend + frontend for Module 1
│   ├── backend/
│   └── frontend/
├── module-2/             # Developer B owns this — separate service, own repo checkout
├── docs/                 # shared contracts — CODEOWNERS-protected, changes need both approvals
├── docker-compose.yml     # spins up module-1 backend + mongo (+ module-2 later)
└── README.md
```

If preferred as **two repositories** instead (`msmeassist-module-1`, `msmeassist-module-2`), the contract in `docs/module-2-integration.md` is published as a versioned markdown file (and later an OpenAPI spec) that Module 2's repo pins a copy of — either approach preserves the "no shared internals" requirement.

**Branching model**
- `main` — always deployable.
- `module-1/*` — Developer A's feature branches (e.g. `module-1/documents-upload`).
- `module-2/*` — Developer B's feature branches.
- `docs/*` — contract changes, require sign-off from whoever owns the *consuming* side (Module 2 dev approves Module 1 contract changes and vice versa).

**Rules**
- Developer B never imports Module 1 Python packages, never connects to Module 1's MongoDB directly, and never reads Module 1's `.env`. All interaction is HTTP calls to `MODULE_1_API_BASE_URL`.
- A `CODEOWNERS` file marks `docs/module-1-api.md` and `docs/module-2-integration.md` as requiring review from both developers before merge — this is the actual mechanism that keeps the contract honest over time.
- CI runs Module 1's own test suite on `module-1/**` changes only; a separate contract test (see below) runs whenever `docs/module-2-integration.md` or the profile schemas change.

**Contract testing (recommended, to implement alongside the API):** a lightweight test that hits `GET /api/profile/me` against a seeded test profile and asserts the response matches the JSON Schema published in `module-2-integration.md`. This is what actually prevents Module 1 from silently breaking Module 2.

---

## 8. Environment Variables

See `/backend/.env.example` and `/frontend/.env.example` for the literal files. Summary of what's configurable and why:

**Backend**
| Variable | Purpose |
|---|---|
| `APP_ENV` | `development` \| `staging` \| `production` |
| `MONGO_URI` | Mongo connection string |
| `MONGO_DB_NAME` | database name, separate per environment |
| `JWT_SECRET_KEY` | signing key, rotated per environment |
| `JWT_ALGORITHM` | e.g. `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | access token lifetime |
| `PASSWORD_HASH_SCHEME` | `bcrypt` \| `argon2` |
| `STORAGE_BACKEND` | `local` \| `s3` — selects the storage adapter |
| `STORAGE_LOCAL_PATH` | disk path, used when `STORAGE_BACKEND=local` |
| `S3_BUCKET_NAME`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_ENDPOINT_URL` | used when `STORAGE_BACKEND=s3`; `S3_ENDPOINT_URL` allows any S3-compatible provider |
| `MAX_UPLOAD_SIZE_MB` | document upload cap |
| `ALLOWED_ORIGINS` | CORS allow-list for the frontend origin(s) |
| `MODULE_2_ALLOWED` | (optional) toggles whether the API is reachable by an external module in this environment |

**Frontend**
| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Module 1 backend base URL |
| `VITE_APP_ENV` | environment label for UI banners (e.g., "staging") |

---

## 9. Development Workflow

1. **Clone & install**
   ```
   git clone <repo-url> && cd msmeassist/module-1
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```
2. **Run MongoDB** locally (Docker: `docker run -p 27017:27017 mongo:7`) or point `MONGO_URI` at a hosted instance.
3. **Backend**
   ```
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```
4. **Frontend**
   ```
   cd frontend
   npm install
   npm run dev
   ```
5. **Verify**: open the Vite dev server URL; register a test account; walk through the 7-step wizard; confirm `GET /api/profile/completeness` updates as fields are filled.
6. **Tests**: `pytest` for backend (`tests/unit` runs without Mongo; `tests/integration` needs a test database, configured via `MONGO_DB_NAME=msmeassist_test`).
7. **Before opening a PR**: if the change touches `schemas/profile_schema.py` or any field in `business_profiles`, update `docs/module-1-api.md` and `docs/module-2-integration.md` in the same PR — CI contract tests will fail otherwise.

Full run instructions also live in the top-level `README.md`.
