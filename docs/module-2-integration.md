# Module 2 Integration Contract

This document is the **only** thing Module 2 (Government Service Intelligence / scheme recommendation) is allowed to depend on. Module 2 must never:

- connect to Module 1's MongoDB instance directly,
- import Module 1's Python packages or internal models,
- assume knowledge of Module 1's internal field names, storage layout, or ID formats beyond what's documented here.

Module 2 talks to Module 1 exclusively over HTTP, using the endpoints below.

---

## Why a contract document instead of just "read the code"

Developer A (Module 1) and Developer B (Module 2) can work in parallel and ship independently as long as this file is accurate. Any change to the shape of these responses is a breaking change to Module 2 and must be:

1. proposed as a diff to this file,
2. reviewed by whoever owns Module 2 at the time,
3. released as `v1` (additive/compatible) or `v2` (breaking) — see versioning below.

---

## Authentication for service-to-service calls

Module 2 acts on behalf of a signed-in user. It should forward the same user JWT it received from the frontend (or, in a server-to-server topology, hold a service credential issued by Module 1 with a `module2_reader` scope). Two supported patterns:

**Pattern A — user-context passthrough (recommended for MVP)**
The frontend calls Module 2 with the user's JWT; Module 2 forwards `Authorization: Bearer <token>` to Module 1 unchanged. Module 1 authenticates and scopes the response to that user, exactly as it would for its own frontend.

**Pattern B — service credential (for backend-to-backend batch jobs)**
Module 1 issues a long-lived service token scoped to `role: service_reader` that can query `/api/profile/{user_id}` (an admin-scoped variant) for batch scheme-matching jobs. Not required for MVP; documented here so the seam exists if needed later.

---

## Primary endpoint: `GET /api/profile/me`

Same response Module 1's own frontend consumes — Module 2 gets the identical normalized DTO, not a stripped-down or module-specific version. This guarantees the contract can't silently drift between "what the frontend sees" and "what Module 2 sees."

### Response schema (v1)

```json
{
  "profile_id": "string",
  "status": "draft | submitted | active",
  "business": {
    "name": "string",
    "type": "manufacturing | services | trading | other",
    "industry": "string",
    "sub_sector": "string | null",
    "established_date": "YYYY-MM-DD",
    "description": "string | null"
  },
  "location": {
    "state": "string",
    "district": "string",
    "city": "string",
    "pin_code": "string (6 digits)",
    "area_type": "rural | urban",
    "premises_type": "own | rented | industrial_estate | shared | null"
  },
  "financial": {
    "annual_turnover_inr": "number",
    "investment_inr": "number",
    "employee_count": "integer",
    "has_existing_loan": "boolean | null",
    "has_bank_finance": "boolean | null",
    "profitability_status": "profitable | break_even | loss | null",
    "msme_classification": "micro | small | medium"
  },
  "characteristics": {
    "is_women_owned": "boolean",
    "social_category": "general | sc | st | obc | other",
    "is_first_gen_entrepreneur": "boolean",
    "is_startup_recognized": "boolean",
    "is_rural_enterprise": "boolean",
    "exports_currently": "boolean",
    "export_intent": "boolean",
    "is_tech_oriented": "boolean",
    "is_sustainable": "boolean"
  },
  "registrations": [
    {
      "type": "udyam | gst | pan | fssai | iec | factory_license | trade_license | pollution_noc | other",
      "status": "registered | not_registered | in_progress | not_applicable",
      "masked_identifier": "string | null"
    }
  ],
  "completeness": {
    "percentage": "integer 0-100",
    "sections": { "business": "boolean", "location": "boolean", "financial": "boolean", "characteristics": "boolean", "registrations": "boolean", "documents": "boolean" }
  },
  "updated_at": "ISO-8601 datetime"
}
```

**Field guarantees**
- `profile_id` is an opaque string. Module 2 must not assume it is a MongoDB ObjectId, parse it, or use it to construct its own database queries.
- Enum fields (`business.type`, `financial.msme_classification`, `registrations[].status`, etc.) are closed sets. New values are only ever **added**, never renamed or removed, within `v1`.
- `registrations[].masked_identifier` is the only identifier form ever exposed outside Module 1 — raw identifiers (GSTIN, PAN, Udyam number) never leave Module 1's boundary.
- `financial.msme_classification` is always server-derived and trustworthy — Module 2 should treat it as ground truth rather than recomputing it from turnover/investment.

---

## Supporting endpoints

### `GET /api/profile/completeness`
Use when Module 2 only needs to gate a feature on completeness (e.g., "don't show scheme matches until profile is 100%") without pulling the full profile.

### `GET /api/profile/eligibility`
Returns the flat `attributes[]` tag array described in `module-1-api.md`. This is the **preferred** way for Module 2 to filter/match schemes — it avoids Module 2 having to re-derive eligibility logic (e.g., MSME classification thresholds, "what counts as export intent") from raw profile fields. New tags are additive; Module 2 should ignore unrecognized tags rather than erroring on them.

---

## Versioning policy

- All Module 1 routes are namespaced `/api/...` today; if a breaking change to the profile response is ever needed, it ships as `/api/v2/profile/me` while `/api/profile/me` (implicitly v1) continues to serve the old shape for a documented deprecation window.
- Additive changes (new optional field, new enum value, new tag in `attributes[]`) do **not** require a version bump — Module 2 must be built to tolerate unknown fields and unknown enum/tag values without failing.
- Removing or renaming a field is always a breaking change, never done silently.

## Contract testing

Module 1's CI includes a test that snapshots the JSON Schema of `GET /api/profile/me` against the schema documented in this file. If a PR changes the response shape without updating this document, the test fails the build. This is the actual enforcement mechanism — the document is not just a description, it's a checked artifact.

## What Module 2 explicitly does NOT get

- Direct MongoDB access or connection string.
- Any Module 1 internal package import.
- Raw document files or storage keys (`documents` collection is entirely internal to Module 1; if Module 2 ever needs to know *whether* a document exists, that's exposed via `completeness.sections.documents`, not via the documents API).
- Any endpoint for writing to a profile — Module 2 is read-only with respect to Module 1's data.
