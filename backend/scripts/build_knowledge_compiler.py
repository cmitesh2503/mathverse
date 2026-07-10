from __future__ import annotations

import os
import shutil
from pathlib import Path


ZIP_SAFE_TIMESTAMP = 315532800
BACKEND_DIR = Path(__file__).resolve().parents[1]
APP_DIR = BACKEND_DIR / "app"
INFRASTRUCTURE_DIR = BACKEND_DIR / "infrastructure"
FUNCTION_DIR = INFRASTRUCTURE_DIR / "cloud_function_knowledge_compiler"
DEPLOYMENT_DIR = INFRASTRUCTURE_DIR / "deployment"
REQUIREMENTS_FILE = FUNCTION_DIR / "requirements.txt"

IGNORE_PATTERNS = (
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".env",
    "credentials",
    "firebase_key*",
    "*.pem",
    "*.key",
)


def _require_path(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Required path does not exist: {path}")


def _remove_previous_deployment() -> None:
    deployment_path = DEPLOYMENT_DIR.resolve()
    infrastructure_path = INFRASTRUCTURE_DIR.resolve()

    if deployment_path == infrastructure_path:
        raise RuntimeError("Refusing to delete the infrastructure directory.")

    if infrastructure_path not in deployment_path.parents:
        raise RuntimeError(
            f"Refusing to delete a path outside infrastructure: {deployment_path}"
        )

    if DEPLOYMENT_DIR.exists():
        shutil.rmtree(DEPLOYMENT_DIR)


def _copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(*IGNORE_PATTERNS),
        copy_function=shutil.copy2,
    )


def _normalize_directory_metadata(root: Path) -> None:
    for directory in sorted(
        (path for path in root.rglob("*") if path.is_dir()),
        reverse=True,
    ):
        os.utime(
            directory,
            (ZIP_SAFE_TIMESTAMP, ZIP_SAFE_TIMESTAMP),
        )

    os.utime(
        root,
        (ZIP_SAFE_TIMESTAMP, ZIP_SAFE_TIMESTAMP),
    )


def build_deployment() -> Path:
    _require_path(APP_DIR)
    _require_path(FUNCTION_DIR)
    _require_path(FUNCTION_DIR / "main.py")
    _require_path(FUNCTION_DIR / "compiler.py")
    _require_path(REQUIREMENTS_FILE)

    _remove_previous_deployment()

    DEPLOYMENT_DIR.mkdir(parents=True)

    _copy_tree(
        APP_DIR,
        DEPLOYMENT_DIR / "app",
    )

    function_target = (
        DEPLOYMENT_DIR
        / "infrastructure"
        / "cloud_function_knowledge_compiler"
    )

    function_target.parent.mkdir(parents=True)

    _copy_tree(
        FUNCTION_DIR,
        function_target,
    )

    shutil.copy2(
        REQUIREMENTS_FILE,
        DEPLOYMENT_DIR / "requirements.txt",
    )

    _normalize_directory_metadata(DEPLOYMENT_DIR)

    return DEPLOYMENT_DIR


if __name__ == "__main__":
    deployment_dir = build_deployment()
    print(f"Knowledge compiler deployment built: {deployment_dir}")
