import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app import config  # noqa: E402
from app.warehouse import db  # noqa: E402


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    """Чистая временная БД и профиль для каждого теста."""
    db.reset_for_tests(str(tmp_path / "test.duckdb"))
    monkeypatch.setattr(config, "PROFILE_PATH", tmp_path / "profile.local.yaml")
    yield
