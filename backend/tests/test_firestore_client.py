import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import firestore_client


def _clear_firestore_client_caches():
    firestore_client.get_firestore_service_account_path.cache_clear()
    firestore_client._read_service_account_json.cache_clear()
    firestore_client.resolve_firestore_project_id.cache_clear()
    firestore_client.get_firestore_client.cache_clear()


def test_firestore_project_id_prefers_explicit_env(monkeypatch, tmp_path):
    monkeypatch.setenv("FIRESTORE_PROJECT_ID", "env-project")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCLOUD_PROJECT", raising=False)
    monkeypatch.delenv("PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT_PATH", raising=False)
    monkeypatch.setattr(firestore_client, "_BUNDLED_SERVICE_ACCOUNT_PATH", tmp_path / "missing.json")
    _clear_firestore_client_caches()

    assert firestore_client.resolve_firestore_project_id() == "env-project"


def test_firestore_project_id_falls_back_to_service_account(monkeypatch, tmp_path):
    service_account = tmp_path / "firebase_key.json"
    service_account.write_text(json.dumps({"project_id": "service-account-project"}), encoding="utf-8")
    for env_name in (
        "FIRESTORE_PROJECT_ID",
        "GOOGLE_CLOUD_PROJECT",
        "GCLOUD_PROJECT",
        "PROJECT_ID",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ):
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_PATH", str(service_account))
    monkeypatch.setattr(firestore_client, "_BUNDLED_SERVICE_ACCOUNT_PATH", tmp_path / "missing.json")
    _clear_firestore_client_caches()

    assert firestore_client.get_firestore_service_account_path() == str(service_account)
    assert firestore_client.resolve_firestore_project_id() == "service-account-project"
