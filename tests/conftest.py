from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from resurs_corrosion.main import create_app


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    database_path = tmp_path / "test.db"
    app = create_app(f"sqlite:///{database_path}", seed_demo_data=False)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def seeded_client(tmp_path: Path) -> TestClient:
    database_path = tmp_path / "seeded.db"
    app = create_app(f"sqlite:///{database_path}", seed_demo_data=True)
    with TestClient(app) as test_client:
        yield test_client
