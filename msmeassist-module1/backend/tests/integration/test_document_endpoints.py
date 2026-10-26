import io

BUSINESS_PAYLOAD = {
    "business": {
        "name": "Meridian Fabrication Works",
        "type": "manufacturing",
        "industry": "Metal & Engineering Products",
        "established_date": "2019-06-12",
    }
}


def _pdf_file(name="GST_Certificate.pdf"):
    return (name, io.BytesIO(b"%PDF-1.4 fake pdf content"), "application/pdf")


def test_upload_requires_profile_to_exist(client, auth_headers):
    resp = client.post(
        "/api/profile/documents",
        data={"document_type": "gst_certificate"},
        files={"file": _pdf_file()},
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "PROFILE_NOT_FOUND"


def test_upload_document_success(client, auth_headers):
    client.post("/api/profile/me", json=BUSINESS_PAYLOAD, headers=auth_headers)
    resp = client.post(
        "/api/profile/documents",
        data={"document_type": "gst_certificate"},
        files={"file": _pdf_file()},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["file_name"] == "GST_Certificate.pdf"
    assert body["status"] == "uploaded"
    assert body["mime_type"] == "application/pdf"


def test_upload_rejects_unsupported_mime_type(client, auth_headers):
    client.post("/api/profile/me", json=BUSINESS_PAYLOAD, headers=auth_headers)
    resp = client.post(
        "/api/profile/documents",
        data={"document_type": "gst_certificate"},
        files={"file": ("virus.exe", io.BytesIO(b"not a real doc"), "application/x-msdownload")},
        headers=auth_headers,
    )
    assert resp.status_code == 415
    assert resp.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_upload_rejects_oversized_file(client, auth_headers, monkeypatch):
    client.post("/api/profile/me", json=BUSINESS_PAYLOAD, headers=auth_headers)
    from app.core import config as config_module

    config_module.get_settings.cache_clear()
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "0")  # anything non-empty counts as "too large"
    config_module.get_settings.cache_clear()

    resp = client.post(
        "/api/profile/documents",
        data={"document_type": "gst_certificate"},
        files={"file": _pdf_file()},
        headers=auth_headers,
    )
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "FILE_TOO_LARGE"
    config_module.get_settings.cache_clear()


def test_list_documents_returns_uploaded_files(client, auth_headers):
    client.post("/api/profile/me", json=BUSINESS_PAYLOAD, headers=auth_headers)
    client.post(
        "/api/profile/documents",
        data={"document_type": "gst_certificate"},
        files={"file": _pdf_file("GST_Certificate.pdf")},
        headers=auth_headers,
    )
    client.post(
        "/api/profile/documents",
        data={"document_type": "udyam_certificate"},
        files={"file": _pdf_file("Udyam_Certificate.pdf")},
        headers=auth_headers,
    )
    resp = client.get("/api/profile/documents", headers=auth_headers)
    assert resp.status_code == 200
    docs = resp.json()["documents"]
    assert len(docs) == 2
    names = {d["file_name"] for d in docs}
    assert names == {"GST_Certificate.pdf", "Udyam_Certificate.pdf"}


def test_document_upload_updates_profile_completeness(client, auth_headers):
    client.post("/api/profile/me", json=BUSINESS_PAYLOAD, headers=auth_headers)
    before = client.get("/api/profile/completeness", headers=auth_headers).json()
    assert before["sections"]["documents"] is False

    client.post(
        "/api/profile/documents",
        data={"document_type": "gst_certificate"},
        files={"file": _pdf_file()},
        headers=auth_headers,
    )

    after = client.get("/api/profile/completeness", headers=auth_headers).json()
    assert after["sections"]["documents"] is True
    assert after["percentage"] > before["percentage"]


def test_delete_document_removes_it_and_recomputes_completeness(client, auth_headers):
    client.post("/api/profile/me", json=BUSINESS_PAYLOAD, headers=auth_headers)
    upload_resp = client.post(
        "/api/profile/documents",
        data={"document_type": "gst_certificate"},
        files={"file": _pdf_file()},
        headers=auth_headers,
    )
    document_id = upload_resp.json()["id"]

    delete_resp = client.delete(f"/api/profile/documents/{document_id}", headers=auth_headers)
    assert delete_resp.status_code == 204

    list_resp = client.get("/api/profile/documents", headers=auth_headers)
    assert list_resp.json()["documents"] == []

    completeness = client.get("/api/profile/completeness", headers=auth_headers).json()
    assert completeness["sections"]["documents"] is False


def test_delete_nonexistent_document_returns_404(client, auth_headers):
    client.post("/api/profile/me", json=BUSINESS_PAYLOAD, headers=auth_headers)
    resp = client.delete("/api/profile/documents/665f1c2ecb2e2e2e2e2e2e2e", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


def test_document_endpoints_require_auth(client):
    resp = client.get("/api/profile/documents")
    assert resp.status_code == 401


def test_user_cannot_delete_another_users_document(client, auth_headers):
    client.post("/api/profile/me", json=BUSINESS_PAYLOAD, headers=auth_headers)
    upload_resp = client.post(
        "/api/profile/documents",
        data={"document_type": "gst_certificate"},
        files={"file": _pdf_file()},
        headers=auth_headers,
    )
    document_id = upload_resp.json()["id"]

    other_payload = {
        "full_name": "Ramesh Iyer",
        "email": "ramesh.iyer@otherbiz.in",
        "mobile_number": "+919845098765",
        "password": "OtherBiz@2026",
        "confirm_password": "OtherBiz@2026",
    }
    register_resp = client.post("/api/auth/register", json=other_payload)
    other_headers = {"Authorization": f"Bearer {register_resp.json()['access_token']}"}

    resp = client.delete(f"/api/profile/documents/{document_id}", headers=other_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
