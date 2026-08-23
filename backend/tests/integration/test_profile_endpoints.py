BUSINESS_PAYLOAD = {
    "business": {
        "name": "Meridian Fabrication Works",
        "type": "manufacturing",
        "industry": "Metal & Engineering Products",
        "sub_sector": "Sheet Metal Fabrication",
        "established_date": "2019-06-12",
        "description": "Manufactures precision sheet-metal components.",
    }
}


def test_get_profile_before_creation_returns_404(client, auth_headers):
    resp = client.get("/api/profile/me", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "PROFILE_NOT_FOUND"


def test_create_profile_requires_auth(client):
    resp = client.post("/api/profile/me", json=BUSINESS_PAYLOAD)
    assert resp.status_code == 401


def test_create_profile_with_business_only(client, auth_headers):
    resp = client.post("/api/profile/me", json=BUSINESS_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["business"]["name"] == "Meridian Fabrication Works"
    assert body["status"] == "draft"
    assert body["completeness"]["sections"]["business"] is True
    assert body["completeness"]["sections"]["location"] is False
    assert body["completeness"]["percentage"] == 17


def test_create_profile_twice_returns_409(client, auth_headers):
    client.post("/api/profile/me", json=BUSINESS_PAYLOAD, headers=auth_headers)
    resp = client.post("/api/profile/me", json=BUSINESS_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "PROFILE_ALREADY_EXISTS"


def test_update_profile_before_creation_returns_404(client, auth_headers):
    resp = client.put(
        "/api/profile/me",
        json={"location": {"state": "Telangana", "district": "Ranga Reddy", "city": "Shamshabad",
                            "pin_code": "500108", "area_type": "urban"}},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_full_wizard_flow_reaches_100_percent(client, auth_headers):
    client.post("/api/profile/me", json=BUSINESS_PAYLOAD, headers=auth_headers)

    location_resp = client.put(
        "/api/profile/me",
        json={"location": {"state": "Telangana", "district": "Ranga Reddy", "city": "Shamshabad",
                            "pin_code": "500108", "area_type": "urban", "premises_type": "own"}},
        headers=auth_headers,
    )
    assert location_resp.status_code == 200
    assert location_resp.json()["completeness"]["sections"]["location"] is True

    financial_resp = client.put(
        "/api/profile/me",
        json={"financial": {"annual_turnover_inr": 38500000, "investment_inr": 9200000,
                             "employee_count": 34, "has_existing_loan": True,
                             "has_bank_finance": False, "profitability_status": "profitable"}},
        headers=auth_headers,
    )
    assert financial_resp.status_code == 200
    # ₹92L investment / ₹3.85Cr turnover both fall within the micro band
    assert financial_resp.json()["financial"]["msme_classification"] == "micro"

    client.put(
        "/api/profile/me",
        json={"characteristics": {"is_first_gen_entrepreneur": True, "export_intent": True,
                                   "is_tech_oriented": True}},
        headers=auth_headers,
    )
    client.put(
        "/api/profile/me",
        json={"registrations": [
            {"type": "udyam", "status": "registered", "identifier": "UDYAM-TS-03-0012345"},
            {"type": "gst", "status": "registered", "identifier": "36AABCU9603R1ZM"},
        ]},
        headers=auth_headers,
    )

    final = client.get("/api/profile/me", headers=auth_headers)
    body = final.json()
    sections = body["completeness"]["sections"]
    assert sections["business"] and sections["location"] and sections["financial"]
    assert sections["characteristics"] and sections["registrations"]
    assert sections["documents"] is False  # no documents uploaded yet
    assert body["completeness"]["percentage"] == 83  # 5 of 6 sections

    # Raw identifiers must never be echoed back — only masked form
    reg_by_type = {r["type"]: r for r in body["registrations"]}
    assert reg_by_type["udyam"]["masked_identifier"] != "UDYAM-TS-03-0012345"
    assert "●" in reg_by_type["udyam"]["masked_identifier"]


def test_update_rejects_client_supplied_msme_classification(client, auth_headers):
    client.post("/api/profile/me", json=BUSINESS_PAYLOAD, headers=auth_headers)
    resp = client.put(
        "/api/profile/me",
        json={"financial": {"annual_turnover_inr": 1000, "investment_inr": 1000,
                             "employee_count": 1, "msme_classification": "medium"}},
        headers=auth_headers,
    )
    # extra="forbid" on FinancialSectionIn rejects the unknown/read-only field
    assert resp.status_code == 422


def test_get_completeness_lists_missing_sections(client, auth_headers):
    client.post("/api/profile/me", json=BUSINESS_PAYLOAD, headers=auth_headers)
    resp = client.get("/api/profile/completeness", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["percentage"] == 17
    missing_sections = {m["section"] for m in body["missing"]}
    assert "location" in missing_sections
    assert "documents" in missing_sections


def test_get_eligibility_reflects_profile_state(client, auth_headers):
    client.post("/api/profile/me", json=BUSINESS_PAYLOAD, headers=auth_headers)
    client.put(
        "/api/profile/me",
        json={"financial": {"annual_turnover_inr": 38500000, "investment_inr": 9200000, "employee_count": 34}},
        headers=auth_headers,
    )
    resp = client.get("/api/profile/eligibility", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["msme_classification"] == "micro"
    assert "manufacturing_sector" in body["attributes"]


def test_get_eligibility_before_profile_created_returns_404(client, auth_headers):
    resp = client.get("/api/profile/eligibility", headers=auth_headers)
    assert resp.status_code == 404


def test_invalid_pin_code_is_rejected(client, auth_headers):
    client.post("/api/profile/me", json=BUSINESS_PAYLOAD, headers=auth_headers)
    resp = client.put(
        "/api/profile/me",
        json={"location": {"state": "Telangana", "district": "Ranga Reddy", "city": "Shamshabad",
                            "pin_code": "12", "area_type": "urban"}},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_profile_is_isolated_per_user(client, auth_headers):
    """A second, independently registered user must not see the first user's profile."""
    client.post("/api/profile/me", json=BUSINESS_PAYLOAD, headers=auth_headers)

    other_payload = {
        "full_name": "Ramesh Iyer",
        "email": "ramesh.iyer@otherbiz.in",
        "mobile_number": "+919845098765",
        "password": "OtherBiz@2026",
        "confirm_password": "OtherBiz@2026",
    }
    register_resp = client.post("/api/auth/register", json=other_payload)
    other_headers = {"Authorization": f"Bearer {register_resp.json()['access_token']}"}

    resp = client.get("/api/profile/me", headers=other_headers)
    assert resp.status_code == 404
