"""Fixtures for the DBUtils tests."""

import pytest

from . import mock_db


@pytest.fixture
def dbapi():
    """Get the mock DB-API 2 module."""
    mock_db.threadsafety = 2
    return mock_db
