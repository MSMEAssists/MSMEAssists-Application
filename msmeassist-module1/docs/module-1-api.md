# Module 1 API Reference — Business Profile & Eligibility Engine

Base URL: `{MODULE_1_API_BASE_URL}/api`
Auth: `Authorization: Bearer <JWT>` on every endpoint except `register` and `login`.
Content type: `application/json` for all endpoints except document upload (`multipart/form-data`).

All error responses share a common envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "PIN code must be 6 digits",
    "field": "location.pin_code"
  }
}
```

---

## Authentication

### `POST /api/auth/register`

**Request**
```json
{
  "full_name": "Anita Rao",
  "email": "anita.rao@meridianfab.in",
  "mobile_number": "+919845012345",
  "password": "Meridian@2026",
  "confirm_password": "Meridian@2026"
}
```

**Response `201 Created`**
```json
{
  "user": {
    "id": "665f1c2e...",
    "full_name": "Anita Rao",
    "email": "anita.rao@meridianfab.in",
    "mobile_number": "+919845012345",
    "role": "msme_owner",
    "is_verified": false,
    "created_at": "2026-08-20T09:12:00Z"
  },
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Errors**: `409 EMAIL_ALREADY_EXISTS`, `409 MOBILE_ALREADY_EXISTS`, `422 VALIDATION_ERROR` (password mismatch, weak password, invalid mobile format).

---

### `POST /api/auth/login`

**Request**
```json
{ "email": "anita.rao@meridianfab.in", "password": "Meridian@2026" }
```

**Response `200 OK`**
```json
{
  "user": { "id": "665f1c2e...", "full_name": "Anita Rao", "email": "anita.rao@meridianfab.in" },
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Errors**: `401 INVALID_CREDENTIALS`, `403 ACCOUNT_INACTIVE`.

---

### `GET /api/auth/me`

**Response `200 OK`**
```json
{
  "id": "665f1c2e...",
  "full_name": "Anita Rao",
  "email": "anita.rao@meridianfab.in",
  "mobile_number": "+919845012345",
  "role": "msme_owner",
  "is_verified": false,
  "has_profile": true,
  "created_at": "2026-08-20T09:12:00Z"
}
```
`has_profile` lets the frontend decide whether to route to onboarding or straight to the completed/dashboard state.

**Errors**: `401 UNAUTHORIZED` (missing/expired token).

---

## Profile

### `GET /api/profile/me`

Returns the full normalized profile for the authenticated user. This is also the endpoint documented for Module 2 in `module-2-integration.md` — same response shape.

**Response `200 OK`**
```json
{
  "profile_id": "6712a...",
  "status": "draft",
  "business": {
    "name": "Meridian Fabrication Works",
    "type": "manufacturing",
    "industry": "Metal & Engineering Products",
    "sub_sector": "Sheet Metal Fabrication",
    "established_date": "2019-06-12",
    "description": "Manufactures precision sheet-metal components..."
  },
  "location": {
    "state": "Telangana",
    "district": "Ranga Reddy",
    "city": "Shamshabad",
    "pin_code": "500108",
    "area_type": "urban",
    "premises_type": "own"
  },
  "financial": {
    "annual_turnover_inr": 38500000,
    "investment_inr": 9200000,
    "employee_count": 34,
    "has_existing_loan": true,
    "has_bank_finance": false,
    "profitability_status": "profitable",
    "msme_classification": "small"
  },
  "characteristics": {
    "is_women_owned": false,
    "social_category": "general",
    "is_first_gen_entrepreneur": true,
    "is_startup_recognized": false,
    "is_rural_enterprise": false,
    "exports_currently": false,
    "export_intent": true,
    "is_tech_oriented": true,
    "is_sustainable": false
  },
  "registrations": [
    { "type": "udyam", "status": "registered", "masked_identifier": "UDYAM-TS-●●-●●●●●●●" },
    { "type": "gst", "status": "registered", "masked_identifier": "36AB●●●1234C●Z●" },
    { "type": "trade_license", "status": "not_registered", "masked_identifier": null }
  ],
  "completeness": {
    "percentage": 82,
    "sections": {
      "business": true, "location": true, "financial": true,
      "characteristics": true, "registrations": false, "documents": false
    }
  },
  "updated_at": "2026-08-20T09:40:00Z"
}
```

**Errors**: `404 PROFILE_NOT_FOUND` if the user hasn't created a profile yet.

---

### `POST /api/profile/me`

Creates the initial profile (first save from Step 1). Accepts a partial payload — only `business` is required at creation time; later steps use `PUT`.

**Request**
```json
{
  "business": {
    "name": "Meridian Fabrication Works",
    "type": "manufacturing",
    "industry": "Metal & Engineering Products",
    "sub_sector": "Sheet Metal Fabrication",
    "established_date": "2019-06-12",
    "description": "Manufactures precision sheet-metal components..."
  }
}
```

**Response `201 Created`** — same shape as `GET /api/profile/me`, with `status: "draft"` and `completeness.percentage` recalculated.

**Errors**: `409 PROFILE_ALREADY_EXISTS` (use `PUT` instead), `422 VALIDATION_ERROR`.

---

### `PUT /api/profile/me`

Section-aware partial update — the frontend sends only the section(s) being edited on the current wizard step.

**Request** (example: Step 3 — Financial)
```json
{
  "financial": {
    "annual_turnover_inr": 38500000,
    "investment_inr": 9200000,
    "employee_count": 34,
    "has_existing_loan": true,
    "has_bank_finance": false,
    "profitability_status": "profitable"
  }
}
```

**Response `200 OK`** — full updated profile (same shape as `GET /api/profile/me`). `financial.msme_classification` is recomputed server-side and returned; it is rejected if sent by the client (`422 READ_ONLY_FIELD`).

**Request** (example: Step 5 — Registrations, replaces the full array)
```json
{
  "registrations": [
    { "type": "udyam", "status": "registered", "identifier": "UDYAM-TS-03-0012345" },
    { "type": "trade_license", "status": "not_registered" }
  ]
}
```
Raw `identifier` values are accepted here (write-only) and never echoed back — only `masked_identifier` appears in responses.

**Errors**: `404 PROFILE_NOT_FOUND`, `422 VALIDATION_ERROR` (e.g. invalid PIN code, negative turnover, unknown enum value).

---

### `GET /api/profile/completeness`

Lightweight resource for polling/UI badges without pulling the full profile.

**Response `200 OK`**
```json
{
  "percentage": 82,
  "sections": {
    "business": true,
    "location": true,
    "financial": true,
    "characteristics": true,
    "registrations": false,
    "documents": false
  },
  "missing": [
    { "section": "registrations", "detail": "Trade License status not set" },
    { "section": "documents", "detail": "1 document rejected — re-upload required" }
  ]
}
```

---

### `GET /api/profile/eligibility`

Returns derived eligibility **attributes** (flags/tags), not scheme recommendations — scheme matching is Module 2's job. This endpoint exists so Module 2 doesn't have to re-derive classification logic itself.

**Response `200 OK`**
```json
{
  "msme_classification": "small",
  "attributes": [
    "manufacturing_sector",
    "women_owned:false",
    "first_generation_entrepreneur",
    "export_intent",
    "technology_oriented",
    "udyam_registered",
    "gst_registered",
    "trade_license_missing"
  ],
  "computed_at": "2026-08-20T09:40:00Z"
}
```
`attributes` is an intentionally flat, additive tag list — Module 2 can filter on it without needing to understand Module 1's internal field structure. New tags can be added without breaking existing consumers.

---

## Documents

### `POST /api/profile/documents`

`multipart/form-data` with fields: `document_type` (enum), `file` (binary).

**Response `201 Created`**
```json
{
  "id": "6712b...",
  "document_type": "gst_certificate",
  "file_name": "GST_Certificate.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 1150000,
  "status": "uploaded",
  "uploaded_at": "2026-08-20T09:45:00Z"
}
```

**Errors**: `413 FILE_TOO_LARGE`, `415 UNSUPPORTED_MEDIA_TYPE` (anything outside PDF/JPG/JPEG/PNG), `422 VALIDATION_ERROR` (unknown `document_type`).

---

### `GET /api/profile/documents`

**Response `200 OK`**
```json
{
  "documents": [
    {
      "id": "6712b...",
      "document_type": "gst_certificate",
      "file_name": "GST_Certificate.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 1150000,
      "status": "pending_review",
      "rejection_reason": null,
      "uploaded_at": "2026-08-20T09:45:00Z"
    },
    {
      "id": "6712c...",
      "document_type": "trade_license",
      "file_name": "Trade_License_Old.png",
      "mime_type": "image/png",
      "size_bytes": 640000,
      "status": "rejected",
      "rejection_reason": "Document illegible",
      "uploaded_at": "2026-08-19T14:02:00Z"
    }
  ]
}
```
Note: this endpoint never returns raw `storage_key`. File retrieval (viewing/downloading the actual file) is a separate, signed-URL concern outside Module 1's core scope and can be added as `GET /api/profile/documents/{id}/download` later without changing this contract.

---

### `DELETE /api/profile/documents/{document_id}`

**Response `204 No Content`**

**Errors**: `404 DOCUMENT_NOT_FOUND`, `403 FORBIDDEN` (document belongs to another user).

---

## Status Code Conventions

| Code | Meaning |
|---|---|
| `200` | successful read/update |
| `201` | resource created |
| `204` | successful delete, no body |
| `401` | missing/invalid/expired token |
| `403` | authenticated but not authorized for this resource |
| `404` | resource not found |
| `409` | conflict (duplicate email, profile already exists) |
| `413` | upload exceeds size limit |
| `415` | unsupported file type |
| `422` | validation error (field-level detail in `error.field`) |
