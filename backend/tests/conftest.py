"""Shared pytest fixtures.

Owner: M1.  Used by ``test_api.py`` (M1) and by the end-to-end tests (M5).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
EXAMPLES_DIR = REPO_ROOT / "examples"
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


@pytest.fixture(scope="session")
def client() -> TestClient:
    """A FastAPI test client bound to the real app (with lifespan)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def examples_dir() -> Path:
    """Absolute path of the repository ``examples/`` folder."""
    return EXAMPLES_DIR


@pytest.fixture(scope="session")
def golden_dir() -> Path:
    """Absolute path of ``backend/tests/golden/``."""
    return GOLDEN_DIR


@pytest.fixture
def example_code():
    """``example_code("basic.asm")`` -> the file's text."""

    def load(name: str) -> str:
        return (EXAMPLES_DIR / name).read_text(encoding="utf-8")

    return load


@pytest.fixture
def golden_results() -> dict:
    """Contents of ``tests/golden/expected_results.json`` (empty until M5 fills it)."""
    path = GOLDEN_DIR / "expected_results.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:  # pragma: no cover - malformed golden file
        return {}
