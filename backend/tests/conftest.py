"""Test fixtures.

Tests run against a real Postgres (the same container as the app, but a
separate `tracker_test` database) because the schema uses Postgres-specific
features: UUID columns, a native enum, and a deferrable unique constraint.

Start the database first:  docker compose up -d
"""

import os

# Tests must NEVER run against the application database: the fixtures below
# drop and truncate tables. So rather than trusting whatever DATABASE_URL is
# already set (docker compose sets it to the live database), always derive a
# dedicated "<name>_test" database from it and force that into the environment
# before app.config is imported.
_DEFAULT_URL = "postgresql+psycopg://tracker:tracker@localhost:5433/tracker"


def _test_url(url: str) -> str:
    from sqlalchemy.engine import make_url

    parsed = make_url(url)
    name = parsed.database or "tracker"
    if not name.endswith("_test"):
        name = f"{name}_test"
    return parsed.set(database=name).render_as_string(hide_password=False)


os.environ["DATABASE_URL"] = _test_url(os.environ.get("DATABASE_URL", _DEFAULT_URL))
os.environ.setdefault("JWT_SECRET", "test-secret-not-used-anywhere-real")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app import models  # noqa: E402,F401


def _ensure_test_database() -> None:
    url = make_url(settings.database_url)
    # Refuse to touch anything that is not clearly a test database.
    assert url.database and url.database.endswith("_test"), (
        f"Refusing to run tests against {url.database!r}: "
        "the test database name must end with '_test'."
    )
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def database():
    _ensure_test_database()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_tables(database):
    """Empty every table between tests so they stay independent."""
    yield
    with engine.begin() as conn:
        tables = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def register(client):
    """Create a user and return a client-like helper already holding its token."""

    def _register(email: str = "a@example.com", password: str = "password123", plan: bool = True):
        response = client.post("/auth/signup", json={"email": email, "password": password})
        assert response.status_code == 201, response.text
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
        if plan:
            # Most tests want an account that already has the default plan.
            setup = client.post("/me/plan/setup", json={"mode": "default"}, headers=headers)
            assert setup.status_code == 201, setup.text
        return headers

    return _register
