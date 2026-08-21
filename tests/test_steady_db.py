"""Test the SteadyDB module.

Note:
We do not test any real DB-API 2 module, but we just
mock the basic DB-API 2 connection functionality.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke
"""

import pytest

from dbutils.steady_db import (
    InvalidCursorError,
    SteadyDBConnection,
    SteadyDBCursor,
)
from dbutils.steady_db import connect as steady_db_connect

from . import mock_db as dbapi


def test_version():
    """Check that the module and class versions are in sync."""
    from dbutils import __version__, steady_db
    assert steady_db.__version__ == __version__
    assert steady_db.SteadyDBConnection.version == __version__


def test_mocked_connection():
    """Check that the mocked DB-API 2 connection behaves as expected."""
    db = dbapi.connect(
        'SteadyDBTestDB', user='SteadyDBTestUser')
    assert hasattr(db, 'database')
    assert db.database == 'SteadyDBTestDB'
    assert hasattr(db, 'user')
    assert db.user == 'SteadyDBTestUser'
    assert hasattr(db, 'cursor')
    assert hasattr(db, 'close')
    assert hasattr(db, 'open_cursors')
    assert hasattr(db, 'num_uses')
    assert hasattr(db, 'num_queries')
    assert hasattr(db, 'session')
    assert hasattr(db, 'valid')
    assert db.valid
    # cursors are counted while they are open,
    # no matter whether they are closed explicitly or garbage collected
    assert db.open_cursors == 0
    for _i in range(3):
        cursor = db.cursor()
        assert db.open_cursors == 1
        cursor.close()
        assert db.open_cursors == 0
    cursor = []
    for i in range(3):
        cursor.append(db.cursor())
        assert db.open_cursors == i + 1
    del cursor
    assert db.open_cursors == 0
    cursor = db.cursor()
    assert hasattr(cursor, 'execute')
    assert hasattr(cursor, 'fetchone')
    assert hasattr(cursor, 'callproc')
    assert hasattr(cursor, 'close')
    assert hasattr(cursor, 'valid')
    assert cursor.valid
    assert db.open_cursors == 1
    # queries and procedure calls both count as uses,
    # but only the queries are counted as queries
    for i in range(3):
        assert db.num_uses == i
        assert db.num_queries == i
        cursor.execute(f'select test{i}')
        assert cursor.fetchone() == f'test{i}'
    assert cursor.valid
    assert db.open_cursors == 1
    for _i in range(4):
        cursor.callproc('test')
    cursor.close()
    assert not cursor.valid
    assert db.open_cursors == 0
    assert db.num_uses == 7
    assert db.num_queries == 3
    # a closed cursor cannot be used or closed again
    with pytest.raises(dbapi.InternalError):
        cursor.close()
    with pytest.raises(dbapi.InternalError):
        cursor.execute('select test')
    # closing the connection resets the counters,
    # and the connection cannot be used or closed again either
    assert db.valid
    db.close()
    assert not db.valid
    assert db.num_uses == 0
    assert db.num_queries == 0
    with pytest.raises(dbapi.InternalError):
        db.close()
    with pytest.raises(dbapi.InternalError):
        db.cursor()


def test_mocked_connection_ping(con_cls):
    """Check that the mocked DB-API 2 connection can be pinged."""
    db = dbapi.connect(
        'SteadyDBTestDB', user='SteadyDBTestUser')
    # every attempt to ping is counted, even when there is no ping method
    assert not con_cls.has_ping
    assert con_cls.num_pings == 0
    with pytest.raises(AttributeError):
        db.ping()
    assert con_cls.num_pings == 1
    con_cls.has_ping = True
    assert db.ping() is None
    assert con_cls.num_pings == 2
    # pinging a closed connection reports it as broken
    db.close()
    with pytest.raises(dbapi.OperationalError):
        db.ping()
    assert con_cls.num_pings == 3


def test_broken_connection():
    """Check that errors when opening connection or cursor are reported."""
    with pytest.raises(TypeError):
        SteadyDBConnection(None)
    with pytest.raises(TypeError):
        SteadyDBCursor(None)
    db = steady_db_connect(dbapi, database='ok')
    for _i in range(3):
        db.close()
    del db
    with pytest.raises(dbapi.OperationalError):
        steady_db_connect(dbapi, database='error')
    db = steady_db_connect(dbapi, database='ok')
    cursor = db.cursor()
    for _i in range(3):
        cursor.close()
    cursor = db.cursor('ok')
    for _i in range(3):
        cursor.close()
    with pytest.raises(dbapi.OperationalError):
        db.cursor('error')


@pytest.mark.parametrize("closeable", [False, True])
def test_close(closeable):
    """Check that closing is only allowed when the connection is closeable."""
    db = steady_db_connect(dbapi, closeable=closeable)
    assert db._con.valid
    db.close()
    assert closeable ^ db._con.valid
    db.close()
    assert closeable ^ db._con.valid
    db._close()
    assert not db._con.valid
    db._close()
    assert not db._con.valid


def test_connection():
    """Check that the connection wraps the DB-API 2 connection."""
    db = steady_db_connect(
        dbapi, 0, None, None, None, True, None,
        'SteadyDBTestDB', user='SteadyDBTestUser')
    assert isinstance(db, SteadyDBConnection)
    assert hasattr(db, '_con')
    assert hasattr(db, '_usage')
    assert db._usage == 0
    assert hasattr(db._con, 'valid')
    assert db._con.valid
    assert hasattr(db._con, 'cursor')
    assert hasattr(db._con, 'close')
    assert hasattr(db._con, 'open_cursors')
    assert hasattr(db._con, 'num_uses')
    assert hasattr(db._con, 'num_queries')
    assert hasattr(db._con, 'session')
    assert hasattr(db._con, 'database')
    assert db._con.database == 'SteadyDBTestDB'
    assert hasattr(db._con, 'user')
    assert db._con.user == 'SteadyDBTestUser'
    assert hasattr(db, 'cursor')
    assert hasattr(db, 'close')
    # cursors created through the wrapper are counted like the mocked ones
    assert db._con.open_cursors == 0
    for _i in range(3):
        cursor = db.cursor()
        assert db._con.open_cursors == 1
        cursor.close()
        assert db._con.open_cursors == 0
    cursor = []
    for i in range(3):
        cursor.append(db.cursor())
        assert db._con.open_cursors == i + 1
    del cursor
    assert db._con.open_cursors == 0
    cursor = db.cursor()
    assert hasattr(cursor, 'execute')
    assert hasattr(cursor, 'fetchone')
    assert hasattr(cursor, 'callproc')
    assert hasattr(cursor, 'close')
    assert hasattr(cursor, 'valid')
    assert cursor.valid
    assert db._con.open_cursors == 1
    # the wrapper keeps its own usage count next to the mocked counters
    for i in range(3):
        assert db._usage == i
        assert db._con.num_uses == i
        assert db._con.num_queries == i
        cursor.execute(f'select test{i}')
        assert cursor.fetchone() == f'test{i}'
    assert cursor.valid
    assert db._con.open_cursors == 1
    for _i in range(4):
        cursor.callproc('test')
    cursor.close()
    assert not cursor.valid
    assert db._con.open_cursors == 0
    assert db._usage == 7
    assert db._con.num_uses == 7
    assert db._con.num_queries == 3
    # unlike the mocked cursor, the wrapped one can be closed and used again
    cursor.close()
    cursor.execute('select test8')
    assert cursor.valid
    assert db._con.open_cursors == 1
    assert cursor.fetchone() == 'test8'
    assert db._usage == 8
    assert db._con.num_uses == 8
    assert db._con.num_queries == 4


def test_connection_close():
    """Check that closing the connection closes the DB-API 2 connection."""
    db = steady_db_connect(
        dbapi, 0, None, None, None, True, None,
        'SteadyDBTestDB', user='SteadyDBTestUser')
    cursor = db.cursor()
    cursor.execute('select test')
    assert db._usage == 1
    assert db._con.valid
    # the underlying connection is closed, but the wrapper keeps its
    # usage count and can be closed again without an error
    db.close()
    assert not db._con.valid
    assert db._con.open_cursors == 0
    assert db._usage == 1
    assert db._con.num_uses == 0
    assert db._con.num_queries == 0
    with pytest.raises(dbapi.InternalError):
        db._con.close()
    db.close()
    with pytest.raises(dbapi.InternalError):
        db._con.cursor()


def test_connection_reopen():
    """Check that the DB-API 2 connection is transparently reopened."""
    db = steady_db_connect(
        dbapi, 0, None, None, None, True, None,
        'SteadyDBTestDB', user='SteadyDBTestUser')
    db.close()
    # asking for a cursor reopens the underlying connection
    cursor = db.cursor()
    assert db._con.valid
    cursor.execute('select test11')
    assert cursor.fetchone() == 'test11'
    cursor.execute('select test12')
    assert cursor.fetchone() == 'test12'
    cursor.callproc('test')
    assert db._usage == 3
    assert db._con.num_uses == 3
    assert db._con.num_queries == 2
    # a second cursor works on the same reopened connection
    cursor2 = db.cursor()
    assert db._con.open_cursors == 2
    cursor2.execute('select test13')
    assert cursor2.fetchone() == 'test13'
    assert db._con.num_queries == 3
    db.close()
    assert db._con.open_cursors == 0
    assert db._con.num_queries == 0


def test_connection_reopen_when_broken():
    """Check that a broken connection or cursor is transparently replaced."""
    db = steady_db_connect(
        dbapi, 0, None, None, None, True, None,
        'SteadyDBTestDB', user='SteadyDBTestUser')
    cursor = db.cursor()
    assert cursor.valid
    cursor.callproc('test')
    # invalidating the underlying cursor makes the wrapper get a new one
    cursor._cursor.valid = False
    assert not cursor.valid
    with pytest.raises(dbapi.InternalError):
        cursor._cursor.callproc('test')
    cursor.callproc('test')
    assert cursor.valid
    cursor._cursor.callproc('test')
    assert db._usage == 2
    assert db._con.num_uses == 3
    # invalidating the connection as well makes it reconnect,
    # which resets the usage count of the wrapper too
    db._con.valid = cursor._cursor.valid = False
    cursor.callproc('test')
    assert cursor.valid
    assert db._usage == 1
    assert db._con.num_uses == 1
    # the session is passed on to the underlying connection as usual
    cursor.execute('set this')
    db.commit()
    cursor.execute('set that')
    db.rollback()
    assert db._con.session == ['this', 'commit', 'that', 'rollback']


def test_connection_context_handler():
    """Check that the context handler commits or rolls back."""
    db = steady_db_connect(
        dbapi, 0, None, None, None, True, None,
        'SteadyDBTestDB', user='SteadyDBTestUser')
    assert db._con.session == []
    with db as con:
        con.cursor().execute('select test')
    assert db._con.session == ['commit']
    try:
        with db as con:
            con.cursor().execute('error')
    except dbapi.ProgrammingError:
        error = True
    else:
        error = False
    assert error
    assert db._con.session == ['commit', 'rollback']


def test_cursor_context_handler():
    """Check that the cursor is closed by the context handler."""
    db = steady_db_connect(
        dbapi, 0, None, None, None, True, None,
        'SteadyDBTestDB', user='SteadyDBTestUser')
    assert db._con.open_cursors == 0
    with db.cursor() as cursor:
        assert db._con.open_cursors == 1
        cursor.execute('select test')
        assert cursor.fetchone() == 'test'
    assert db._con.open_cursors == 0


def test_cursor_as_iterator_provided():
    """Check that an iterator provided by the cursor is used."""
    db = steady_db_connect(
        dbapi, 0, None, None, None, True, None,
        'SteadyDBTestDB', user='SteadyDBTestUser')
    assert db._con.open_cursors == 0
    cursor = db.cursor()
    assert db._con.open_cursors == 1
    cursor.execute('select test')
    _cursor = cursor._cursor
    try:
        assert not hasattr(_cursor, 'iter')
        _cursor.__iter__ = lambda: ['test-iter']
        assert list(iter(cursor)) == ['test']
    finally:
        del _cursor.__iter__
    cursor.close()
    assert db._con.open_cursors == 0


def test_cursor_as_iterator_created():
    """Check that an iterator is created when the cursor has none."""
    db = steady_db_connect(
        dbapi, 0, None, None, None, True, None,
        'SteadyDBTestDB', user='SteadyDBTestUser')
    assert db._con.open_cursors == 0
    cursor = db.cursor()
    assert db._con.open_cursors == 1
    cursor.execute('select test')
    assert list(iter(cursor)) == ['test']
    cursor.close()
    assert db._con.open_cursors == 0


def test_connection_creator_function():
    """Check that a creator function can be used instead of a module."""
    db1 = steady_db_connect(
        dbapi, 0, None, None, None, True, None,
        'SteadyDBTestDB', user='SteadyDBTestUser')
    db2 = steady_db_connect(
        dbapi.connect, 0, None, None, None, True, None,
        'SteadyDBTestDB', user='SteadyDBTestUser')
    assert db1.dbapi() == db2.dbapi()
    assert db1.threadsafety() == db2.threadsafety()
    assert db1._creator == db2._creator
    assert db1._args == db2._args
    assert db1._kwargs == db2._kwargs
    db2.close()
    db1.close()


def creator_of_this_module(*args, **kwargs):
    """Create a mocked connection from inside this test module."""
    return dbapi.connect(*args, **kwargs)


def test_connection_creator_function_of_other_module():
    """Check that the DB-API 2 module is determined via the connection."""
    db = steady_db_connect(creator_of_this_module, database='ok')
    # the module cannot be derived from a creator function defined here,
    # but it is found via the module of the connection that it returns
    assert db.dbapi() is dbapi
    assert db.threadsafety() == dbapi.threadsafety
    assert db._failures == (
        dbapi.OperationalError, dbapi.InterfaceError, dbapi.InternalError)
    # the failover mechanism works just as with a module as creator
    db.close()
    cursor = db.cursor()
    cursor.execute('select test')
    assert cursor.fetchone() == 'test'


def test_connection_creator_class():
    """Check that the connection class itself can be used as creator."""
    db = steady_db_connect(dbapi.Connection, database='ok')
    # the module of the creator provides a connect() function, but it is
    # a different one, so the module is determined via the connection
    assert db.dbapi() is dbapi
    assert db.threadsafety() == dbapi.threadsafety
    cursor = db.cursor()
    cursor.execute('select test')
    assert cursor.fetchone() == 'test'


class CreatorWithDbapi:
    """A creator module that points to the real DB-API 2 module."""

    dbapi = dbapi
    connect = staticmethod(dbapi.connect)


def test_connection_creator_with_dbapi():
    """Check that a creator can name its DB-API 2 module explicitly."""
    db = steady_db_connect(CreatorWithDbapi, database='ok')
    assert db.dbapi() is dbapi
    assert db.threadsafety() == dbapi.threadsafety
    cursor = db.cursor()
    cursor.execute('select test')
    assert cursor.fetchone() == 'test'


class ConnectionWithErrorsOnly:
    """A connection that reveals its module only via its error classes."""

    OperationalError = dbapi.OperationalError
    InterfaceError = dbapi.InterfaceError
    InternalError = dbapi.InternalError

    def close(self):
        """Close the connection."""


def creator_of_hidden_module():
    """Create a connection that hides the module it belongs to."""
    return ConnectionWithErrorsOnly()


def test_connection_module_found_via_error_class():
    """Check that the DB-API 2 module is found via the error classes."""
    db = steady_db_connect(creator_of_hidden_module)
    # the module of the connection itself does not provide connect(),
    # but the module of its error classes does
    assert db.dbapi() is dbapi
    assert db.threadsafety() == dbapi.threadsafety


def test_connection_with_unknown_threadsafety(monkeypatch):
    """Check that an undeterminable threadsafety is reported as zero."""
    monkeypatch.delattr(dbapi, 'threadsafety')
    db = steady_db_connect(creator_of_this_module, database='ok')
    assert db.dbapi() is dbapi
    assert db.threadsafety() == 0


def unknown_error_cls(name):
    """Create an error class belonging to an unimportable module."""
    return type(name, (Exception,), {'__module__': 'unknown_db_module'})


class UnknownConnection:
    """A connection that cannot be traced back to a DB-API 2 module.

    Neither this test module nor the module claimed by the error
    classes provides a connect() function, so there is no way to
    determine the DB-API 2 module from such a connection.
    """

    threadsafety = 3

    OperationalError = unknown_error_cls('OperationalError')
    InterfaceError = unknown_error_cls('InterfaceError')
    InternalError = unknown_error_cls('InternalError')

    def close(self):
        """Close the connection."""


class NamelessConnection:
    """A connection that does not tell anything about its module."""

    def close(self):
        """Close the connection."""


def creator_of_unknown_module():
    """Create a connection with an undeterminable DB-API 2 module."""
    return UnknownConnection()


def creator_with_failures():
    """Create such a connection, but make the failures known."""
    return UnknownConnection()


creator_with_failures.OperationalError = (
    UnknownConnection.OperationalError)
creator_with_failures.InterfaceError = (
    UnknownConnection.InterfaceError)
creator_with_failures.InternalError = (
    UnknownConnection.InternalError)


def test_connection_with_unknown_module():
    """Check the fallbacks when the DB-API 2 module cannot be determined."""
    db = steady_db_connect(creator_of_unknown_module)
    with pytest.raises(AttributeError):
        db.dbapi()
    # the threadsafety and the failures are taken from the connection
    assert db.threadsafety() == 3
    assert db._failures == (
        UnknownConnection.OperationalError,
        UnknownConnection.InterfaceError,
        UnknownConnection.InternalError)


def test_connection_with_failures_of_creator():
    """Check that the failures can also be taken from the creator."""
    db = steady_db_connect(creator_with_failures)
    assert db._failures == (
        UnknownConnection.OperationalError,
        UnknownConnection.InterfaceError,
        UnknownConnection.InternalError)


def test_connection_with_undeterminable_failures():
    """Check that undeterminable failures are reported as an error."""
    with pytest.raises(AttributeError, match='failure exceptions'):
        steady_db_connect(NamelessConnection)


def test_connection_with_undeterminable_threadsafety():
    """Check that an undeterminable threadsafety is reported as an error."""
    db = steady_db_connect(NamelessConnection, failures=dbapi.InternalError)
    with pytest.raises(AttributeError, match='threadsafety'):
        db.threadsafety()


def test_connection_maxusage():
    """Check that the connection is reset when used too often."""
    db = steady_db_connect(dbapi, 10)
    cursor = db.cursor()
    # the connection is silently reset after every 10 uses
    for i in range(100):
        cursor.execute(f'select test{i}')
        r = cursor.fetchone()
        assert r == f'test{i}'
        assert db._con.valid
        j = i % 10 + 1
        assert db._usage == j
        assert db._con.num_uses == j
        assert db._con.num_queries == j
    assert db._con.open_cursors == 1
    # inside a transaction the reset is postponed until it has been ended,
    # so the usage count keeps growing beyond the maximum until then
    db.begin()
    for i in range(100):
        cursor.callproc('test')
        assert db._con.valid
        if i == 49:
            db.commit()
        j = i % 10 + 1 if i > 49 else i + 11
        assert db._usage == j
        assert db._con.num_uses == j
        j = 0 if i > 49 else 10
        assert db._con.num_queries == j
    # a connection that breaks in between is reset early,
    # which also restarts the counting of the uses
    for i in range(10):
        if i == 7:
            db._con.valid = cursor._cursor.valid = False
        cursor.execute(f'select test{i}')
        r = cursor.fetchone()
        assert r == f'test{i}'
        j = i % 7 + 1
        assert db._usage == j
        assert db._con.num_uses == j
        assert db._con.num_queries == j
    for i in range(10):
        if i == 5:
            db._con.valid = cursor._cursor.valid = False
        cursor.callproc('test')
        j = (i + (3 if i < 5 else -5)) % 10 + 1
        assert db._usage == j
        assert db._con.num_uses == j
        j = 3 if i < 5 else 0
        assert db._con.num_queries == j
    # closing the connection restarts the counting as well
    db.close()
    cursor.execute('select test1')
    assert cursor.fetchone() == 'test1'
    assert db._usage == 1
    assert db._con.num_uses == 1
    assert db._con.num_queries == 1


def test_connection_setsession_error():
    """Check that a session that cannot be prepared is reported."""
    with pytest.raises(dbapi.ProgrammingError):
        steady_db_connect(dbapi, 0, ('set time zone', 'error'))
    # the connection is closed again when the session cannot be prepared
    connections = []

    def creator(*args, **kwargs):
        con = dbapi.connect(*args, **kwargs)
        connections.append(con)
        return con

    with pytest.raises(dbapi.ProgrammingError):
        steady_db_connect(creator, 0, ('error',), failures=dbapi.InternalError)
    assert len(connections) == 1
    assert not connections[0].valid


def test_connection_setsession():
    """Check that the session is prepared after every reopening."""
    db = steady_db_connect(dbapi, 3, ('set time zone', 'set datestyle'))
    assert hasattr(db, '_usage')
    assert db._usage == 0
    assert hasattr(db._con, 'open_cursors')
    assert db._con.open_cursors == 0
    assert hasattr(db._con, 'num_uses')
    assert db._con.num_uses == 2
    assert hasattr(db._con, 'num_queries')
    assert db._con.num_queries == 0
    assert hasattr(db._con, 'session')
    assert tuple(db._con.session) == ('time zone', 'datestyle')
    # maxusage is 3, so the connection is reset after every third query
    # and the session is prepared again from scratch each time
    for _i in range(11):
        db.cursor().execute('select test')
    assert db._con.open_cursors == 0
    assert db._usage == 2
    assert db._con.num_uses == 4
    assert db._con.num_queries == 2
    assert db._con.session == ['time zone', 'datestyle']
    # a "set" command is added to the session, but is lost on the next reset
    db.cursor().execute('set test')
    assert db._con.open_cursors == 0
    assert db._usage == 3
    assert db._con.num_uses == 5
    assert db._con.num_queries == 2
    assert db._con.session == ['time zone', 'datestyle', 'test']
    db.cursor().execute('select test')
    assert db._con.open_cursors == 0
    assert db._usage == 1
    assert db._con.num_uses == 3
    assert db._con.num_queries == 1
    assert db._con.session == ['time zone', 'datestyle']
    db.cursor().execute('set test')
    assert db._con.open_cursors == 0
    assert db._usage == 2
    assert db._con.num_uses == 4
    assert db._con.num_queries == 1
    assert db._con.session == ['time zone', 'datestyle', 'test']
    db.cursor().execute('select test')
    assert db._con.open_cursors == 0
    assert db._usage == 3
    assert db._con.num_uses == 5
    assert db._con.num_queries == 2
    assert db._con.session == ['time zone', 'datestyle', 'test']
    # the same happens after the connection has been closed explicitly
    db.close()
    db.cursor().execute('set test')
    assert db._con.open_cursors == 0
    assert db._usage == 1
    assert db._con.num_uses == 3
    assert db._con.num_queries == 0
    assert db._con.session == ['time zone', 'datestyle', 'test']
    db.close()
    db.cursor().execute('select test')
    assert db._con.open_cursors == 0
    assert db._usage == 1
    assert db._con.num_uses == 3
    assert db._con.num_queries == 1
    assert db._con.session == ['time zone', 'datestyle']


def test_connection_maxusage_must_be_integer():
    """Check that maxusage must be an integer when it is given."""
    steady_db_connect(dbapi, None)
    steady_db_connect(dbapi, 42)
    with pytest.raises(TypeError):
        steady_db_connect(dbapi, 'unlimited')
    with pytest.raises(TypeError):
        steady_db_connect(dbapi, 42.5)


def test_connection_failures_must_be_exceptions():
    """Check that failures must be exception classes when they are given."""
    steady_db_connect(dbapi, failures=None)
    steady_db_connect(dbapi, failures=dbapi.InternalError)
    steady_db_connect(dbapi, failures=(dbapi.InternalError,))
    with pytest.raises(TypeError):
        steady_db_connect(dbapi, failures=int)
    with pytest.raises(TypeError):
        steady_db_connect(dbapi, failures='InternalError')
    with pytest.raises(TypeError):
        steady_db_connect(dbapi, failures=42)


def test_connection_failures():
    """Check that only the configured failures trigger the failover."""
    db = steady_db_connect(dbapi)
    db.close()
    db.cursor()
    db = steady_db_connect(dbapi, failures=dbapi.InternalError)
    db.close()
    db.cursor()
    db = steady_db_connect(dbapi, failures=dbapi.OperationalError)
    db.close()
    with pytest.raises(dbapi.InternalError):
        db.cursor()
    db = steady_db_connect(dbapi, failures=(
        dbapi.OperationalError, dbapi.InterfaceError))
    db.close()
    with pytest.raises(dbapi.InternalError):
        db.cursor()
    db = steady_db_connect(dbapi, failures=(
        dbapi.OperationalError, dbapi.InterfaceError, dbapi.InternalError))
    db.close()
    db.cursor()


def test_connection_failure_error():
    """Check that errors after a successful failover are passed on."""
    db = steady_db_connect(dbapi)
    cursor = db.cursor()
    db.close()
    cursor.execute('select test')
    cursor = db.cursor()
    db.close()
    with pytest.raises(dbapi.ProgrammingError):
        cursor.execute('error')


def test_connection_set_sizes():
    """Check that input and output sizes are set and kept when reopening."""
    db = steady_db_connect(dbapi)
    cursor = db.cursor()
    cursor.execute('get sizes')
    result = cursor.fetchone()
    assert result == ([], {})
    cursor.setinputsizes([7, 42, 6])
    cursor.setoutputsize(9)
    cursor.setoutputsize(15, 3)
    cursor.setoutputsize(42, 7)
    cursor.execute('get sizes')
    result = cursor.fetchone()
    assert result == ([7, 42, 6], {None: 9, 3: 15, 7: 42})
    cursor.execute('get sizes')
    result = cursor.fetchone()
    assert result == ([], {})
    cursor.setinputsizes([6, 42, 7])
    cursor.setoutputsize(7)
    cursor.setoutputsize(15, 3)
    cursor.setoutputsize(42, 9)
    db.close()
    cursor.execute('get sizes')
    result = cursor.fetchone()
    assert result == ([6, 42, 7], {None: 7, 3: 15, 9: 42})


def test_connection_ping(ping_con_cls):
    """Check that ping() is passed on to the underlying connection."""
    db = steady_db_connect(dbapi)
    assert ping_con_cls.num_pings == 0
    assert db.ping() is None
    assert ping_con_cls.num_pings == 1
    # in contrast to the ping check, this does not swallow the error
    # and does not reopen the connection when it has been closed
    con = db._con
    db.close()
    with pytest.raises(dbapi.OperationalError):
        db.ping()
    assert ping_con_cls.num_pings == 2
    assert db._con is con


def test_connection_ping_without_ping_method(con_cls):
    """Check that ping() reports when the connection cannot be pinged."""
    db = steady_db_connect(dbapi)
    assert con_cls.num_pings == 0
    with pytest.raises(AttributeError):
        db.ping()
    assert con_cls.num_pings == 1


def test_connection_ping_check_without_ping_method(con_cls):
    """Check that pinging is skipped when there is no ping method."""
    db = steady_db_connect(dbapi)
    db.cursor().execute('select test')
    assert con_cls.num_pings == 0
    db.close()
    db.cursor().execute('select test')
    assert con_cls.num_pings == 0
    # an explicit check attempts a ping, but cannot report anything
    assert db._ping_check() is None
    assert con_cls.num_pings == 1


def test_connection_ping_check_always_without_ping_method(con_cls):
    """Check that pinging is given up when there is no ping method."""
    db = steady_db_connect(dbapi, ping=7)
    # the first attempt fails with an AttributeError,
    # after which no further pings are attempted at all
    db.cursor().execute('select test')
    assert con_cls.num_pings == 1
    db.close()
    db.cursor().execute('select test')
    assert con_cls.num_pings == 1
    assert db._ping_check() is None
    assert con_cls.num_pings == 1


def test_connection_ping_check_default(ping_con_cls):
    """Check that connections are pinged on request by default."""
    db = steady_db_connect(dbapi)
    db.cursor().execute('select test')
    assert ping_con_cls.num_pings == 0
    db.close()
    db.cursor().execute('select test')
    assert ping_con_cls.num_pings == 0
    assert db._ping_check()
    assert ping_con_cls.num_pings == 1


@pytest.mark.parametrize("ping", range(8))
def test_connection_ping_check_combinations(ping, ping_con_cls):
    """Check the three ping triggers in all of their bit combinations."""
    on_request = bool(ping & 1)  # 1 = when _ping_check() is called
    on_cursor = bool(ping & 2)  # 2 = whenever a cursor is created
    on_execute = bool(ping & 4)  # 4 = when a query is executed
    db = steady_db_connect(dbapi, ping=ping)
    assert ping_con_cls.num_pings == 0
    # while the connection is open, only the configured triggers ping it
    expected = 0
    cursor = db.cursor()
    expected += on_cursor
    assert ping_con_cls.num_pings == expected
    cursor.execute('select test')
    expected += on_execute
    assert ping_con_cls.num_pings == expected
    assert cursor.fetchone() == 'test'
    # a closed connection is pinged just as often, since the ping reports
    # it as broken and the connection is then reopened transparently
    db.close()
    cursor = db.cursor()
    expected += on_cursor
    assert ping_con_cls.num_pings == expected
    cursor.execute('select test')
    expected += on_execute
    assert ping_con_cls.num_pings == expected
    assert cursor.fetchone() == 'test'
    # an explicit check pings only when this has been requested,
    # and it reopens the connection when it has been closed
    db.close()
    assert db._ping_check() is (True if on_request else None)
    expected += on_request
    assert ping_con_cls.num_pings == expected
    assert db._con.valid is on_request


def test_connection_ping_check_with_sql(con_cls):
    """Check that connections can be checked with an SQL statement."""
    db = steady_db_connect(dbapi, ping='select 1')
    con = db._con
    assert con.num_queries == 0
    # the statement is executed instead of using the ping method
    assert db._ping_check()
    assert con_cls.num_pings == 0
    assert con.num_queries == 1
    # the cursor used for the check has been closed again
    assert con.open_cursors == 0
    # and the check does not count towards the usage limit
    assert db._usage == 0
    # a broken connection is detected and transparently reopened
    db.close()
    assert not con.valid
    assert db._ping_check()
    assert db._con is not con
    assert db._con.valid
    assert con_cls.num_pings == 0


def test_connection_ping_check_with_sql_when_query_executed(con_cls):
    """Check that an SQL statement can also be used at other times."""
    db = steady_db_connect(dbapi, ping=(4, 'select 1'))
    con = db._con
    cursor = db.cursor()
    # creating a cursor does not check the connection
    assert con.num_queries == 0
    # but executing a query does, in addition to the query itself
    cursor.execute('select test')
    assert con.num_queries == 2
    assert cursor.fetchone() == 'test'
    assert con_cls.num_pings == 0


def test_connection_ping_check_with_failing_sql(con_cls):
    """Check that a failing check statement is not fatal."""
    db = steady_db_connect(dbapi, ping='error')
    con = db._con
    # the failing statement makes the connection appear broken,
    # so that it is unnecessarily, but harmlessly reopened
    assert db._ping_check()
    assert db._con is not con
    assert db._con.valid
    assert con_cls.num_pings == 0


def test_connection_ping_check_with_function(con_cls, pinger):
    """Check that connections can be checked with a check function."""
    db = steady_db_connect(dbapi, ping=pinger)
    con = db._con
    assert not pinger.calls
    assert db._ping_check()
    # the function is passed the underlying DB-API 2 connection
    assert pinger.calls == [con]
    assert con_cls.num_pings == 0
    assert con.num_queries == 0
    # a broken connection is detected and transparently reopened
    db.close()
    assert db._ping_check()
    assert pinger.calls == [con, con]
    assert db._con is not con
    assert db._con.valid


def test_connection_ping_check_with_function_at_default_times(pinger):
    """Check that a check function is used at the default times."""
    db = steady_db_connect(dbapi, ping=pinger)
    # neither creating a cursor nor executing a query checks the connection
    db.cursor().execute('select test')
    assert not pinger.calls
    # but requesting an explicit check does
    assert db._ping_check()
    assert len(pinger.calls) == 1


def test_connection_ping_check_with_broken_function(con_cls):
    """Check that a broken check function does not disable the check."""
    def broken_check(_con):
        raise AttributeError

    db = steady_db_connect(dbapi, ping=(7, broken_check))
    con = db._con
    assert db._ping_check()
    # in contrast to a missing ping method, the check is not given up,
    # the connection is only considered broken and therefore reopened
    assert db._ping == 7
    assert db._con is not con
    assert db._con.valid
    assert con_cls.num_pings == 0


def test_connection_ping_check_with_invalid_parameter():
    """Check that an invalid check function or statement is rejected."""
    with pytest.raises(TypeError):
        steady_db_connect(dbapi, ping=(1, 42))
    with pytest.raises(TypeError):
        steady_db_connect(dbapi, ping=(1, 'select 1', 2))
    # non-integer values without a check function disable the check
    db = steady_db_connect(dbapi, ping=None)
    assert db._ping == 0
    assert db._pinger is None


@pytest.mark.parametrize("ping", range(8))
def test_connection_ping_check_combinations_with_function(
        ping, con_cls, pinger):
    """Check the three ping triggers when a check function is used."""
    on_request = bool(ping & 1)  # 1 = when _ping_check() is called
    on_cursor = bool(ping & 2)  # 2 = whenever a cursor is created
    on_execute = bool(ping & 4)  # 4 = when a query is executed
    db = steady_db_connect(dbapi, ping=(ping, pinger))
    assert not pinger.calls
    # while the connection is open, only the configured triggers check it
    expected = 0
    cursor = db.cursor()
    expected += on_cursor
    assert len(pinger.calls) == expected
    cursor.execute('select test')
    expected += on_execute
    assert len(pinger.calls) == expected
    assert cursor.fetchone() == 'test'
    # a closed connection is checked just as often, since the check reports
    # it as broken and the connection is then reopened transparently
    db.close()
    cursor = db.cursor()
    expected += on_cursor
    assert len(pinger.calls) == expected
    cursor.execute('select test')
    expected += on_execute
    assert len(pinger.calls) == expected
    assert cursor.fetchone() == 'test'
    # an explicit check is made only when this has been requested,
    # and it reopens the connection when it has been closed
    db.close()
    assert db._ping_check() is (True if on_request else None)
    expected += on_request
    assert len(pinger.calls) == expected
    assert db._con.valid is on_request
    # the ping method has not been used at all
    assert con_cls.num_pings == 0


def test_connection_ping_check_always_with_cursor(ping_con_cls):
    """Check that a kept cursor is pinged everywhere when ping is 7."""
    db = steady_db_connect(dbapi, ping=7)
    assert ping_con_cls.num_pings == 0
    db.cursor()
    assert ping_con_cls.num_pings == 1
    db.close()
    cursor = db.cursor()
    assert ping_con_cls.num_pings == 2
    cursor.execute('select test')
    assert ping_con_cls.num_pings == 3
    db.close()
    cursor = db.cursor()
    assert ping_con_cls.num_pings == 4
    cursor.execute('select test')
    assert ping_con_cls.num_pings == 5
    # when the connection was closed, the cursor is recreated on execution,
    # which pings the connection a second time
    db.close()
    cursor.execute('select test')
    assert ping_con_cls.num_pings == 7


def test_begin_transaction():
    """Check that transparent reopening is suspended after begin()."""
    db = steady_db_connect(dbapi, database='ok')
    cursor = db.cursor()
    cursor.close()
    cursor.execute('select test12')
    assert cursor.fetchone() == 'test12'
    db.begin()
    cursor = db.cursor()
    cursor.close()
    with pytest.raises(dbapi.InternalError):
        cursor.execute('select test12')
    cursor.execute('select test12')
    assert cursor.fetchone() == 'test12'
    db.close()
    db.begin()
    with pytest.raises(dbapi.InternalError):
        cursor.execute('select test12')
    cursor.execute('select test12')
    assert cursor.fetchone() == 'test12'
    db.begin()
    with pytest.raises(dbapi.ProgrammingError):
        cursor.execute('error')
    cursor.close()
    cursor.execute('select test12')
    assert cursor.fetchone() == 'test12'


def test_with_begin_extension():
    """Check that begin() is passed on to the underlying connection."""
    db = steady_db_connect(dbapi, database='ok')
    db._con._begin_called_with = None

    def begin(a, b=None, c=7):
        db._con._begin_called_with = (a, b, c)

    db._con.begin = begin
    db.begin(42, 6)
    cursor = db.cursor()
    cursor.execute('select test13')
    assert cursor.fetchone() == 'test13'
    assert db._con._begin_called_with == (42, 6, 7)


def test_cancel_transaction():
    """Check that cancel() ends a transaction started with begin()."""
    db = steady_db_connect(dbapi, database='ok')
    cursor = db.cursor()
    db.begin()
    cursor.execute('select test14')
    assert cursor.fetchone() == 'test14'
    db.cancel()
    cursor.execute('select test14')
    assert cursor.fetchone() == 'test14'


def test_with_cancel_extension():
    """Check that cancel() is passed on to the underlying connection."""
    db = steady_db_connect(dbapi, database='ok')
    db._con._cancel_called = None

    def cancel():
        db._con._cancel_called = 'yes'

    db._con.cancel = cancel
    db.begin()
    cursor = db.cursor()
    cursor.execute('select test15')
    assert cursor.fetchone() == 'test15'
    db.cancel()
    assert db._con._cancel_called == 'yes'


def test_reset_transaction():
    """Check that closing rolls back a transaction when not closeable."""
    db = steady_db_connect(dbapi, database='ok')
    db.begin()
    assert not db._con.session
    db.close()
    assert not db._con.session
    db = steady_db_connect(dbapi, database='ok', closeable=False)
    db.begin()
    assert not db._con.session
    db.close()
    assert db._con.session == ['rollback']


def test_commit_error():
    """Check that the connection is reopened when a commit fails."""
    db = steady_db_connect(dbapi, database='ok')
    db.begin()
    assert not db._con.session
    assert db._con.valid
    db.commit()
    assert db._con.session == ['commit']
    assert db._con.valid
    db.begin()
    db._con.valid = False
    con = db._con
    with pytest.raises(dbapi.InternalError):
        db.commit()
    assert not db._con.session
    assert db._con.valid
    assert con is not db._con
    db.begin()
    assert not db._con.session
    assert db._con.valid
    db.commit()
    assert db._con.session == ['commit']
    assert db._con.valid


def test_rollback_error():
    """Check that the connection is reopened when a rollback fails."""
    db = steady_db_connect(dbapi, database='ok')
    db.begin()
    assert not db._con.session
    assert db._con.valid
    db.rollback()
    assert db._con.session == ['rollback']
    assert db._con.valid
    db.begin()
    db._con.valid = False
    con = db._con
    with pytest.raises(dbapi.InternalError):
        db.rollback()
    assert not db._con.session
    assert db._con.valid
    assert con is not db._con
    db.begin()
    assert not db._con.session
    assert db._con.valid
    db.rollback()
    assert db._con.session == ['rollback']
    assert db._con.valid


def test_commit_error_when_reopening_fails():
    """Check that a failed commit is reported when there is no recovery."""
    db = steady_db_connect(dbapi, database='ok')
    db.begin()
    con = db._con
    # the database goes away and cannot be reached again
    db._con.valid = False
    db._kwargs['database'] = 'error'
    with pytest.raises(dbapi.InternalError):
        db.commit()
    # the connection could not be replaced, but the transaction is over
    assert db._con is con
    assert not db._transaction


def test_rollback_error_when_reopening_fails():
    """Check that a failed rollback is reported when there is no recovery."""
    db = steady_db_connect(dbapi, database='ok')
    db.begin()
    con = db._con
    db._con.valid = False
    db._kwargs['database'] = 'error'
    with pytest.raises(dbapi.InternalError):
        db.rollback()
    assert db._con is con
    assert not db._transaction


def test_ping_check_when_reopening_fails(ping_con_cls):
    """Check that a failed ping is reported when there is no recovery."""
    db = steady_db_connect(dbapi, database='ok')
    db.close()
    db._kwargs['database'] = 'error'
    # the ping reports the connection as broken and it cannot be reopened
    assert db._ping_check() is False
    assert ping_con_cls.num_pings == 1
    assert not db._con.valid
    # when the database is back, the connection is reopened as usual
    db._kwargs['database'] = 'ok'
    assert db._ping_check() is True
    assert ping_con_cls.num_pings == 2
    assert db._con.valid


def test_cursor_when_reopening_fails():
    """Check that a cursor cannot be created when there is no recovery."""
    db = steady_db_connect(dbapi, database='ok')
    db.close()
    db._kwargs['database'] = 'error'
    with pytest.raises(dbapi.InternalError):
        db.cursor()
    # when the database is back, the cursor can be created as usual
    db._kwargs['database'] = 'ok'
    cursor = db.cursor()
    cursor.execute('select test')
    assert cursor.fetchone() == 'test'


def test_cursor_in_transaction_when_connection_is_replaced():
    """Check that a transaction is not silently continued elsewhere."""
    db = steady_db_connect(dbapi, database='ok')
    db.begin()
    con = db._con
    db._con.valid = False
    with pytest.raises(dbapi.InternalError):
        db.cursor()
    # the connection has been replaced, but the error is still raised,
    # since the transaction cannot be continued on the new connection
    assert db._con is not con
    assert db._con.valid
    assert not db._transaction


def test_cursor_in_transaction_when_reopening_fails():
    """A transaction that cannot be reopened must not stay active.

    This is the counterpart of the test below for the case that already
    the creation of the cursor fails, and not only its execution.
    """
    db = steady_db_connect(dbapi, database='ok')
    db.begin()
    assert db._transaction
    # the database goes away and cannot be reached again
    db._con.valid = False
    db._kwargs['database'] = 'error'
    with pytest.raises(dbapi.InternalError):
        db.cursor()
    assert not db._transaction
    # when the database is back, the failover mechanism must work again
    db._kwargs['database'] = 'ok'
    cursor = db.cursor()
    cursor.execute('select test')
    assert cursor.fetchone() == 'test'
    assert db._con.valid


def test_transaction_ended_when_reopening_fails():
    """A transaction that cannot be reopened must not stay active.

    Otherwise the failover mechanism would stay suspended on the
    connection, so that it could never recover by itself again.
    """
    db = steady_db_connect(dbapi, database='ok')
    cursor = db.cursor()
    db.begin()
    assert db._transaction
    # the database goes away and cannot be reached again
    db._kwargs['database'] = 'error'
    db._con.valid = cursor._cursor.valid = False
    with pytest.raises(dbapi.InternalError):
        cursor.execute('select test')
    assert not db._transaction
    # when the database is back, the failover mechanism must work again
    db._kwargs['database'] = 'ok'
    cursor.execute('select test')
    assert cursor.fetchone() == 'test'
    assert db._con.valid


def test_execute_when_reopening_fails():
    """Check that a statement is reported when there is no recovery."""
    db = steady_db_connect(dbapi, database='ok')
    cursor = db.cursor()
    # the database goes away and cannot be reached again
    db._con.valid = cursor._cursor.valid = False
    db._kwargs['database'] = 'error'
    with pytest.raises(dbapi.InternalError):
        cursor.execute('select test')
    # when the database is back, the statement can be executed again
    db._kwargs['database'] = 'ok'
    cursor.execute('select test')
    assert cursor.fetchone() == 'test'


def test_execute_when_cursor_cannot_be_reopened():
    """Check that a statement is reported when no cursor can be opened."""
    db = steady_db_connect(dbapi, database='ok')
    cursor = db.cursor()
    # the cursor cannot be recreated, neither on the old connection
    # that is reopened first, nor on a completely new connection
    cursor._args = ('error',)
    con = db._con
    db._con.valid = cursor._cursor.valid = False
    with pytest.raises(dbapi.InternalError):
        cursor.execute('select test')
    assert db._con is con
    assert not db._con.valid


class FlakyCreator:
    """A creator that fails at the first attempt to reconnect."""

    def __init__(self):
        """Create the creator with the failover switched off."""
        self.fail = False

    def __call__(self, *args, **kwargs):
        """Create a mocked connection, but fail once when requested."""
        if self.fail:
            self.fail = False
            raise dbapi.OperationalError
        return dbapi.connect(*args, **kwargs)


def test_execute_retried_on_a_new_connection():
    """Check that the failover falls back on a completely new connection."""
    creator = FlakyCreator()
    db = steady_db_connect(creator, database='ok')
    cursor = db.cursor()
    cursor.execute('select test')
    assert db._usage == 1
    con = db._con
    # the connection breaks, and reopening it while getting a new cursor
    # fails as well, so the whole connection is created from scratch
    db._con.valid = cursor._cursor.valid = False
    creator.fail = True
    cursor.execute('select test2')
    assert cursor.fetchone() == 'test2'
    assert db._con is not con
    assert db._con.valid
    assert not creator.fail
    # the usage count has been restarted together with the connection
    assert db._usage == 1
    assert db._con.num_uses == 1


def test_execute_retried_on_a_new_connection_with_sizes():
    """Check that the stored sizes are set on the new connection too."""
    creator = FlakyCreator()
    db = steady_db_connect(creator, database='ok')
    cursor = db.cursor()
    cursor.setinputsizes([7, 42, 6])
    cursor.setoutputsize(9)
    db._con.valid = cursor._cursor.valid = False
    creator.fail = True
    cursor.execute('get sizes')
    assert cursor.fetchone() == ([7, 42, 6], {None: 9})
    # the sizes have been cleared after they have been used
    cursor.execute('get sizes')
    assert cursor.fetchone() == ([], {})


def timeout_is_not_fatal(error):
    """Treat a deliberate server side timeout as not fatal."""
    return not error.args or error.args[0] != 3024


def always_fatal(error):  # noqa: ARG001
    """Treat every error as fatal for the connection."""
    return True


def never_fatal(error):  # noqa: ARG001
    """Treat no error as fatal for the connection."""
    return False


def test_connection_isfatal_must_be_callable():
    """Check that isfatal must be a callable when it is given."""
    steady_db_connect(dbapi, isfatal=None)
    steady_db_connect(dbapi, isfatal=always_fatal)
    with pytest.raises(TypeError):
        steady_db_connect(dbapi, isfatal='always')
    with pytest.raises(TypeError):
        steady_db_connect(dbapi, isfatal=42)


def test_connection_isfatal_is_asked():
    """Check that isfatal is asked and can veto the failover."""
    errors = []

    def record_and_veto(error):
        errors.append(error)
        return False

    db = steady_db_connect(dbapi, isfatal=record_and_veto)
    cursor = db.cursor()
    cursor.execute('select test')
    assert cursor.fetchone() == 'test'
    assert not errors  # not asked as long as nothing fails
    con = db._con
    db.close()
    with pytest.raises(dbapi.InternalError):
        cursor.execute('select test')
    assert len(errors) == 1
    assert isinstance(errors[0], dbapi.InternalError)
    # the connection has not been replaced since the failover was vetoed
    assert db._con is con


def test_connection_isfatal_false_and_true():
    """Check that isfatal can switch the failover off and on."""
    db = steady_db_connect(dbapi, isfatal=never_fatal)
    cursor = db.cursor()
    db.close()
    with pytest.raises(dbapi.InternalError):
        cursor.execute('select test')
    db = steady_db_connect(dbapi, isfatal=always_fatal)
    cursor = db.cursor()
    db.close()
    cursor.execute('select test')  # transparently reopened as usual
    assert cursor.fetchone() == 'test'


def test_connection_isfatal_selectively():
    """Statement timeouts shall not be retried (see issue #58)."""
    dbapi.Connection.num_timeouts = 0
    db = steady_db_connect(dbapi)
    cursor = db.cursor()
    with pytest.raises(dbapi.OperationalError):
        cursor.execute('timeout')
    # by default the statement is executed three times in total:
    # once directly, once with a new cursor, once with a new connection
    assert dbapi.Connection.num_timeouts == 3
    dbapi.Connection.num_timeouts = 0
    db = steady_db_connect(dbapi, isfatal=timeout_is_not_fatal)
    cursor = db.cursor()
    with pytest.raises(dbapi.OperationalError):
        cursor.execute('timeout')
    assert dbapi.Connection.num_timeouts == 1
    # the connection is still usable and the failed statement was not counted
    assert db._usage == 0
    cursor.execute('select test')
    assert cursor.fetchone() == 'test'
    assert db._usage == 1
    # other failures are still handled by the failover mechanism
    db.close()
    cursor.execute('select test')
    assert cursor.fetchone() == 'test'


def test_connection_isfatal_cursor_creation():
    """Check that isfatal also applies when creating a cursor."""
    db = steady_db_connect(dbapi, isfatal=never_fatal)
    con = db._con
    db.close()
    with pytest.raises(dbapi.InternalError):
        db.cursor()
    assert db._con is con
    db = steady_db_connect(dbapi, isfatal=always_fatal)
    con = db._con
    db.close()
    db.cursor()  # transparently reopened as usual
    assert db._con is not con


def test_connection_isfatal_ignored_when_overused():
    """The reset triggered by maxusage must not be vetoed."""
    db = steady_db_connect(dbapi, 3, isfatal=never_fatal)
    cursor = db.cursor()
    for i in range(10):
        cursor.execute(f'select test{i}')
        assert cursor.fetchone() == f'test{i}'
        assert db._con.valid
        assert db._usage == i % 3 + 1
        assert db._con.num_uses == i % 3 + 1


def test_cursor_no_failover():
    """Check that no_failover() suspends the failover mechanism."""
    dbapi.Connection.num_timeouts = 0
    db = steady_db_connect(dbapi)
    cursor = db.cursor()
    with cursor.no_failover(), pytest.raises(dbapi.OperationalError):
        cursor.execute('timeout')
    assert dbapi.Connection.num_timeouts == 1
    assert cursor._no_failover == 0
    # outside of the context, the failover mechanism is active again
    dbapi.Connection.num_timeouts = 0
    with pytest.raises(dbapi.OperationalError):
        cursor.execute('timeout')
    assert dbapi.Connection.num_timeouts == 3


def test_cursor_no_failover_keeps_bookkeeping():
    """Check that no_failover() still counts the usage."""
    db = steady_db_connect(dbapi)
    cursor = db.cursor()
    with cursor.no_failover():
        cursor.execute('select test')
    assert cursor.fetchone() == 'test'
    # in contrast to using the raw cursor, the usage is still counted
    assert db._usage == 1
    assert db._con.num_uses == 1


def test_cursor_no_failover_broken_connection():
    """Check that no_failover() does not replace the connection."""
    db = steady_db_connect(dbapi)
    cursor = db.cursor()
    con = db._con
    db.close()
    with cursor.no_failover(), pytest.raises(dbapi.InternalError):
        cursor.execute('select test')
    assert db._con is con  # not replaced inside the context
    # afterwards the failover mechanism works again
    cursor.execute('select test')
    assert cursor.fetchone() == 'test'
    assert db._con is not con


def test_cursor_no_failover_nested():
    """Check that no_failover() contexts can be nested."""
    db = steady_db_connect(dbapi)
    cursor = db.cursor()
    assert cursor._no_failover == 0
    with cursor.no_failover() as cur:
        assert cur is cursor
        assert cursor._no_failover == 1
        with cursor.no_failover():
            assert cursor._no_failover == 2
        assert cursor._no_failover == 1
    assert cursor._no_failover == 0
    # the counter is also restored when the statement fails
    with pytest.raises(dbapi.OperationalError), cursor.no_failover():
        cursor.execute('timeout')
    assert cursor._no_failover == 0


def test_dbapi_connection():
    """Check that the underlying DB-API 2 connection is accessible."""
    db = steady_db_connect(dbapi)
    con = db.dbapi_connection
    assert isinstance(con, dbapi.Connection)
    assert con is db._con
    db.close()
    db.cursor()  # transparently reopened
    assert db.dbapi_connection is db._con
    assert db.dbapi_connection is not con


def test_dbapi_cursor():
    """Check that the underlying DB-API 2 cursor is accessible."""
    db = steady_db_connect(dbapi)
    cursor = db.cursor()
    raw_cursor = cursor.dbapi_cursor
    assert isinstance(raw_cursor, dbapi.Cursor)
    assert raw_cursor is cursor._cursor
    # the raw cursor bypasses the failover mechanism and the bookkeeping
    dbapi.Connection.num_timeouts = 0
    with pytest.raises(dbapi.OperationalError):
        raw_cursor.execute('timeout')
    assert dbapi.Connection.num_timeouts == 1
    raw_cursor.execute('select test')
    assert raw_cursor.fetchone() == 'test'
    assert db._con.num_uses == 2  # both statements reached the server
    assert db._usage == 0  # but they were not counted by the steady connection
    cursor._cursor = None
    with pytest.raises(InvalidCursorError):
        cursor.dbapi_cursor  # noqa: B018


def test_invalid_cursor():
    """Check that the members of an invalid cursor cannot be accessed."""
    db = steady_db_connect(dbapi)
    cursor = db.cursor()
    assert cursor.fetchone() is None  # inherited from the underlying cursor
    assert callable(cursor.execute)  # made "tough" by the wrapper
    cursor._cursor = None
    with pytest.raises(InvalidCursorError):
        cursor.fetchone  # noqa: B018
    with pytest.raises(InvalidCursorError):
        cursor.execute  # noqa: B018
