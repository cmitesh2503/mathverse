from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

FIRESTORE_TIMEOUT_SECONDS = 10

_PROJECT_ENV_VARS = (
    "FIRESTORE_PROJECT_ID",
    "GOOGLE_CLOUD_PROJECT",
    "GCLOUD_PROJECT",
    "PROJECT_ID",
)
_SERVICE_ACCOUNT_ENV_VARS = (
    "GOOGLE_APPLICATION_CREDENTIALS",
    "FIREBASE_SERVICE_ACCOUNT_PATH",
)
_BUNDLED_SERVICE_ACCOUNT_PATH = Path(__file__).with_name("firebase_key.json")


def _clean_env_value(value: str | None) -> str:
    return str(value or "").strip().strip('"').strip("'")


@lru_cache(maxsize=1)
def get_firestore_service_account_path() -> str | None:
    for env_name in _SERVICE_ACCOUNT_ENV_VARS:
        configured_path = _clean_env_value(os.getenv(env_name))
        if configured_path and Path(configured_path).expanduser().exists():
            return str(Path(configured_path).expanduser())

    if _BUNDLED_SERVICE_ACCOUNT_PATH.exists():
        return str(_BUNDLED_SERVICE_ACCOUNT_PATH)

    return None


@lru_cache(maxsize=4)
def _read_service_account_json(path: str) -> dict[str, Any]:
    try:
        with Path(path).expanduser().open("r", encoding="utf-8") as file:
            parsed = json.load(file)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


@lru_cache(maxsize=1)
def resolve_firestore_project_id() -> str | None:
    for env_name in _PROJECT_ENV_VARS:
        project_id = _clean_env_value(os.getenv(env_name))
        if project_id:
            return project_id

    service_account_path = get_firestore_service_account_path()
    if service_account_path:
        project_id = _clean_env_value(_read_service_account_json(service_account_path).get("project_id"))
        if project_id:
            return project_id

    return None


@lru_cache(maxsize=1)
def get_firestore_client():
    from google.cloud import firestore

    project_id = resolve_firestore_project_id()
    service_account_path = get_firestore_service_account_path()

    if service_account_path:
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_file(service_account_path)
        return firestore.Client(project=project_id or credentials.project_id, credentials=credentials)

    if project_id:
        return firestore.Client(project=project_id)

    return firestore.Client()
