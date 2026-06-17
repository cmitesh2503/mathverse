from __future__ import annotations

import json
import os
import subprocess
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
_AUTH_MODE_ENV_VAR = "MATHVERSE_FIRESTORE_AUTH_MODE"
_REQUIRED_GCLOUD_ACCOUNT_ENV_VAR = "MATHVERSE_REQUIRED_GCLOUD_ACCOUNT"

_AUTH_MODE_ADC = "adc"
_AUTH_MODE_SERVICE_ACCOUNT = "service_account"
_AUTH_MODE_BUNDLED_SERVICE_ACCOUNT = "bundled_service_account"


def _clean_env_value(value: str | None) -> str:
    return str(value or "").strip().strip('"').strip("'")


@lru_cache(maxsize=1)
def resolve_firestore_auth_mode() -> str:
    auth_mode = _clean_env_value(os.getenv(_AUTH_MODE_ENV_VAR)).lower()
    if not auth_mode:
        for env_name in _SERVICE_ACCOUNT_ENV_VARS:
            configured_path = _clean_env_value(os.getenv(env_name))
            if configured_path and Path(configured_path).expanduser().exists():
                return _AUTH_MODE_SERVICE_ACCOUNT
        return _AUTH_MODE_ADC
    if auth_mode in {_AUTH_MODE_ADC, "google_adc", "gcloud", "application_default"}:
        return _AUTH_MODE_ADC
    if auth_mode in {_AUTH_MODE_SERVICE_ACCOUNT, "service-account", "serviceaccount"}:
        return _AUTH_MODE_SERVICE_ACCOUNT
    if auth_mode in {"bundled", "bundled-key", "bundled_service_account"}:
        return _AUTH_MODE_BUNDLED_SERVICE_ACCOUNT
    raise RuntimeError(
        f"Unsupported {_AUTH_MODE_ENV_VAR}={auth_mode!r}. "
        "Use adc, service_account, or bundled_service_account."
    )


@lru_cache(maxsize=1)
def get_firestore_service_account_path() -> str | None:
    auth_mode = resolve_firestore_auth_mode()
    if auth_mode == _AUTH_MODE_ADC:
        return None

    for env_name in _SERVICE_ACCOUNT_ENV_VARS:
        configured_path = _clean_env_value(os.getenv(env_name))
        if configured_path and Path(configured_path).expanduser().exists():
            return str(Path(configured_path).expanduser())

    if auth_mode == _AUTH_MODE_BUNDLED_SERVICE_ACCOUNT and _BUNDLED_SERVICE_ACCOUNT_PATH.exists():
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
def validate_required_gcloud_account() -> None:
    required_account = _clean_env_value(os.getenv(_REQUIRED_GCLOUD_ACCOUNT_ENV_VAR, "miteshc@gmail.com"))
    if not required_account:
        return

    executable = "gcloud.cmd" if os.name == "nt" else "gcloud"
    try:
        result = subprocess.run(
            [executable, "config", "get-value", "account"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as error:
        raise RuntimeError(
            f"{_REQUIRED_GCLOUD_ACCOUNT_ENV_VAR} is set to {required_account}, "
            "but the active gcloud account could not be verified."
        ) from error

    active_account = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    if active_account != required_account:
        raise RuntimeError(
            f"Refusing Firestore access with gcloud account {active_account or '<unknown>'}. "
            f"Expected {required_account}."
        )


@lru_cache(maxsize=1)
def get_firestore_client():
    from google.cloud import firestore

    project_id = resolve_firestore_project_id()
    service_account_path = get_firestore_service_account_path()

    if service_account_path:
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_file(service_account_path)
        return firestore.Client(project=project_id or credentials.project_id, credentials=credentials)

    if not project_id:
        raise RuntimeError(
            "FIRESTORE_PROJECT_ID or GOOGLE_CLOUD_PROJECT must be set. "
            "The backend will not infer a Firestore project from another account."
        )

    validate_required_gcloud_account()
    return firestore.Client(project=project_id)
