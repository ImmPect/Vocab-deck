"""Сквозные механизмы: health, справочник должностей, CSRF, формат ошибок."""


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["data"]["db"] == "ok"


def test_levels(client):
    r = client.get("/api/v1/levels")
    body = r.json()
    assert r.status_code == 200
    assert body["meta"]["total_items"] == 6
    assert [lvl["min_xp"] for lvl in body["data"]] == [0, 300, 800, 1600, 3000, 5000]
    assert r.headers["Cache-Control"] == "public, max-age=3600"


def test_csrf_header_required(client):
    r = client.post("/api/v1/auth/logout", headers={"X-Requested-With": ""})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "csrf_check_failed"


def test_unknown_route_uses_error_format(client):
    r = client.get("/api/v1/nope")
    assert r.status_code == 404
    assert r.json() == {"error": {"code": "not_found", "message": "Не найдено"}}


def test_request_id_header(client):
    assert client.get("/api/v1/health").headers["X-Request-Id"]


def test_swagger_adds_csrf_header(client):
    r = client.get("/docs")
    assert r.status_code == 200
    assert "X-Requested-With" in r.text and "requestInterceptor" in r.text


def test_prod_requires_strong_secret():
    import pytest
    from app.core.config import Settings
    with pytest.raises(RuntimeError):
        Settings(env="prod", secret_key="dev-secret-change-me").check_production()
    Settings(env="prod", secret_key="x" * 40).check_production()
