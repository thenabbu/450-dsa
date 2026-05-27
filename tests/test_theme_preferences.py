import mongomock

import app as app_module
import app.auth.routes as auth_routes
from app.config import TestingConfig
from conftest import build_test_app, login_test_user


def create_test_app(monkeypatch):
    test_db = mongomock.MongoClient().db

    monkeypatch.setattr(app_module, "db", test_db)
    monkeypatch.setattr(auth_routes, "db", test_db)
    monkeypatch.setattr(app_module.mongo, "init_app", lambda flask_app, **kwargs: None)
    monkeypatch.setattr(app_module.oauth, "register", lambda *args, **kwargs: None)

    flask_app = app_module.create_app(config_class=TestingConfig)
    flask_app._db_initialized = True

    return flask_app, test_db


def test_theme_preferences_returns_defaults_for_legacy_user(monkeypatch):
    flask_app, test_db = build_test_app(monkeypatch)
    user_id = test_db.user.insert_one(
        {
            "name": "Theme User",
            "email": "theme@example.com",
            "is_admin": False,
            "progress": {},
        }
    ).inserted_id

    client = flask_app.test_client()
    login_test_user(client, user_id)
    response = client.get("/theme_preferences")

    assert response.status_code == 200
    assert response.get_json() == {
        "theme_accent": "#ba5912",
        "theme_density": "comfortable",
        "theme_chart_palette": "default",
        "theme_preferences_customized": False,
    }


def test_theme_preferences_can_be_updated(monkeypatch):
    flask_app, test_db = build_test_app(monkeypatch)
    user_id = test_db.user.insert_one(
        {
            "name": "Theme User",
            "email": "theme@example.com",
            "is_admin": False,
            "progress": {},
        }
    ).inserted_id

    client = flask_app.test_client()
    login_test_user(client, user_id)
    response = client.post(
        "/theme_preferences",
        json={
            "theme_accent": "#2563EB",
            "theme_density": "compact",
            "theme_chart_palette": "colorblind",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["theme_accent"] == "#2563eb"
    assert payload["theme_preferences_customized"] is True
    user_doc = test_db.user.find_one({"_id": user_id})
    assert user_doc["theme_accent"] == "#2563eb"
    assert user_doc["theme_density"] == "compact"
    assert user_doc["theme_chart_palette"] == "colorblind"
    assert "theme_preferences_updated_at" in user_doc


def test_theme_preferences_rejects_invalid_values(monkeypatch):
    flask_app, test_db = build_test_app(monkeypatch)
    user_id = test_db.user.insert_one(
        {
            "name": "Theme User",
            "email": "theme@example.com",
            "is_admin": False,
            "progress": {},
        }
    ).inserted_id

    client = flask_app.test_client()
    login_test_user(client, user_id)
    response = client.post(
        "/theme_preferences",
        json={
            "theme_accent": "blue",
            "theme_density": "tiny",
            "theme_chart_palette": "unknown",
        },
    )

    assert response.status_code == 400
    errors = response.get_json()["errors"]
    assert set(errors) == {"theme_accent", "theme_density", "theme_chart_palette"}
