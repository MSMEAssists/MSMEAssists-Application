def test_register_creates_user_and_returns_token(client):
    payload = {
        "full_name": "Anita Rao",
        "email": "anita.rao@meridianfab.in",
        "mobile_number": "+919845012345",
        "password": "Meridian@2026",
        "confirm_password": "Meridian@2026",
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["email"] == "anita.rao@meridianfab.in"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]
    assert body["access_token"]
    assert body["token_type"] == "bearer"


def test_register_rejects_duplicate_email(client, registered_user):
    payload = dict(registered_user["raw_payload"])
    payload["mobile_number"] = "+919845099999"  # different mobile, same email
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_register_rejects_duplicate_mobile(client, registered_user):
    payload = dict(registered_user["raw_payload"])
    payload["email"] = "someone.else@meridianfab.in"
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "MOBILE_ALREADY_EXISTS"


def test_register_rejects_password_mismatch(client):
    payload = {
        "full_name": "Test User",
        "email": "test@example.com",
        "mobile_number": "+919845012399",
        "password": "Meridian@2026",
        "confirm_password": "Different@2026",
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_register_rejects_invalid_mobile_format(client):
    payload = {
        "full_name": "Test User",
        "email": "test2@example.com",
        "mobile_number": "9845012399",
        "password": "Meridian@2026",
        "confirm_password": "Meridian@2026",
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 422


def test_login_succeeds_with_correct_credentials(client, registered_user):
    resp = client.post(
        "/api/auth/login",
        json={"email": "anita.rao@meridianfab.in", "password": "Meridian@2026"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["user"]["email"] == "anita.rao@meridianfab.in"


def test_login_fails_with_wrong_password(client, registered_user):
    resp = client.post(
        "/api/auth/login",
        json={"email": "anita.rao@meridianfab.in", "password": "WrongPassword1"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_fails_with_unknown_email(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "Meridian@2026"},
    )
    assert resp.status_code == 401


def test_get_me_requires_auth(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_get_me_returns_current_user(client, auth_headers):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "anita.rao@meridianfab.in"
    assert body["has_profile"] is False


def test_get_me_rejects_garbage_token(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401
