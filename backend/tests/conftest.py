import pytest

from app.db.session import engine


@pytest.fixture(autouse=True)
def dispose_database_engine():
    yield
    engine.dispose()
