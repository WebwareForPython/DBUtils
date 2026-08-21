"""Fixtures for the DBUtils tests."""

import pytest

from . import mock_db


@pytest.fixture
def dbapi():
    """Get the mock DB-API 2 module."""
    mock_db.threadsafety = 2
    return mock_db


@pytest.fixture
def con_cls():
    """Get the mock connection class with the ping counter reset.

    The ping method is unavailable, and the counter is reset again
    after the test, even when the test fails.
    """
    con_cls = mock_db.Connection
    con_cls.has_ping = False
    con_cls.num_pings = 0
    yield con_cls
    con_cls.has_ping = False
    con_cls.num_pings = 0


@pytest.fixture
def ping_con_cls(con_cls):
    """Get the mock connection class with a working ping method."""
    con_cls.has_ping = True
    return con_cls


@pytest.fixture
def pinger(con_cls):  # noqa: ARG001
    """Get a check function that can be passed as ping parameter.

    The connection class does not have a ping method, so that the check
    function must be used.  It reports valid connections as alive, just
    as the ping method would do, and it records all of its calls.
    """
    def check(con):
        check.calls.append(con)
        if not con.valid:
            raise mock_db.OperationalError

    check.calls = []
    return check
