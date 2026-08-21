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
    from dbutils import __version__, steady_db
    assert steady_db.__version__ == __version__
    assert steady_db.SteadyDBConnection.version == __version__


def test_mocked_connection():
    db = dbapi.connect(
        'SteadyDBTestDB', user='SteadyDBTestUser')
    db.__class__.has_ping = False
    db.__class__.num_pings = 0
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
    with pytest.raises(dbapi.InternalError):
        cursor.close()
    with pytest.raises(dbapi.InternalError):
        cursor.execute('select test')
    assert db.valid
    assert not db.__class__.has_ping
    assert db.__class__.num_pings == 0
    with pytest.raises(AttributeError):
        db.ping()
    assert db.__class__.num_pings == 1
    db.__class__.has_ping = True
    assert db.ping() is None
    assert db.__class__.num_pings == 2
    db.close()
    assert not db.valid
    assert db.num_uses == 0
    assert db.num_queries == 0
    with pytest.raises(dbapi.InternalError):
        db.close()
    with pytest.raises(dbapi.InternalError):
        db.cursor()
    with pytest.raises(dbapi.OperationalError):
        db.ping()
    assert db.__class__.num_pings == 3
    db.__class__.has_ping = False
    db.__class__.num_pings = 0


def test_broken_connection():
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


def test_connection():  # noqa: PLR0915
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
    cursor.close()
    cursor.execute('select test8')
    assert cursor.valid
    assert db._con.open_cursors == 1
    assert cursor.fetchone() == 'test8'
    assert db._usage == 8
    assert db._con.num_uses == 8
    assert db._con.num_queries == 4
    assert db._con.valid
    db.close()
    assert not db._con.valid
    assert db._con.open_cursors == 0
    assert db._usage == 8
    assert db._con.num_uses == 0
    assert db._con.num_queries == 0
    with pytest.raises(dbapi.InternalError):
        db._con.close()
    db.close()
    with pytest.raises(dbapi.InternalError):
        db._con.cursor()
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
    cursor2 = db.cursor()
    assert db._con.open_cursors == 2
    cursor2.execute('select test13')
    assert cursor2.fetchone() == 'test13'
    assert db._con.num_queries == 3
    db.close()
    assert db._con.open_cursors == 0
    assert db._con.num_queries == 0
    cursor = db.cursor()
    assert cursor.valid
    cursor.callproc('test')
    cursor._cursor.valid = False
    assert not cursor.valid
    with pytest.raises(dbapi.InternalError):
        cursor._cursor.callproc('test')
    cursor.callproc('test')
    assert cursor.valid
    cursor._cursor.callproc('test')
    assert db._usage == 2
    assert db._con.num_uses == 3
    db._con.valid = cursor._cursor.valid = False
    cursor.callproc('test')
    assert cursor.valid
    assert db._usage == 1
    assert db._con.num_uses == 1
    cursor.execute('set this')
    db.commit()
    cursor.execute('set that')
    db.rollback()
    assert db._con.session == ['this', 'commit', 'that', 'rollback']


def test_connection_context_handler():
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


def test_connection_maxusage():
    db = steady_db_connect(dbapi, 10)
    cursor = db.cursor()
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
    db.close()
    cursor.execute('select test1')
    assert cursor.fetchone() == 'test1'
    assert db._usage == 1
    assert db._con.num_uses == 1
    assert db._con.num_queries == 1


def test_connection_setsession():
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
    for _i in range(11):
        db.cursor().execute('select test')
    assert db._con.open_cursors == 0
    assert db._usage == 2
    assert db._con.num_uses == 4
    assert db._con.num_queries == 2
    assert db._con.session == ['time zone', 'datestyle']
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


def test_connection_failures():
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
    db = steady_db_connect(dbapi)
    cursor = db.cursor()
    db.close()
    cursor.execute('select test')
    cursor = db.cursor()
    db.close()
    with pytest.raises(dbapi.ProgrammingError):
        cursor.execute('error')


def test_connection_set_sizes():
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


def test_connection_ping_check():
    con_cls = dbapi.Connection
    con_cls.has_ping = False
    con_cls.num_pings = 0
    db = steady_db_connect(dbapi)
    db.cursor().execute('select test')
    assert con_cls.num_pings == 0
    db.close()
    db.cursor().execute('select test')
    assert con_cls.num_pings == 0
    assert db._ping_check() is None
    assert con_cls.num_pings == 1
    db = steady_db_connect(dbapi, ping=7)
    db.cursor().execute('select test')
    assert con_cls.num_pings == 2
    db.close()
    db.cursor().execute('select test')
    assert con_cls.num_pings == 2
    assert db._ping_check() is None
    assert con_cls.num_pings == 2
    con_cls.has_ping = True
    db = steady_db_connect(dbapi)
    db.cursor().execute('select test')
    assert con_cls.num_pings == 2
    db.close()
    db.cursor().execute('select test')
    assert con_cls.num_pings == 2
    assert db._ping_check()
    assert con_cls.num_pings == 3
    db = steady_db_connect(dbapi, ping=1)
    db.cursor().execute('select test')
    assert con_cls.num_pings == 3
    db.close()
    db.cursor().execute('select test')
    assert con_cls.num_pings == 3
    assert db._ping_check()
    assert con_cls.num_pings == 4
    db.close()
    assert db._ping_check()
    assert con_cls.num_pings == 5
    db = steady_db_connect(dbapi, ping=7)
    db.cursor().execute('select test')
    assert con_cls.num_pings == 7
    db.close()
    db.cursor().execute('select test')
    assert con_cls.num_pings == 9
    db = steady_db_connect(dbapi, ping=3)
    assert con_cls.num_pings == 9
    db.cursor()
    assert con_cls.num_pings == 10
    db.close()
    cursor = db.cursor()
    assert con_cls.num_pings == 11
    cursor.execute('select test')
    assert con_cls.num_pings == 11
    db = steady_db_connect(dbapi, ping=5)
    assert con_cls.num_pings == 11
    db.cursor()
    assert con_cls.num_pings == 11
    db.close()
    cursor = db.cursor()
    assert con_cls.num_pings == 11
    cursor.execute('select test')
    assert con_cls.num_pings == 12
    db.close()
    cursor = db.cursor()
    assert con_cls.num_pings == 12
    cursor.execute('select test')
    assert con_cls.num_pings == 13
    db = steady_db_connect(dbapi, ping=7)
    assert con_cls.num_pings == 13
    db.cursor()
    assert con_cls.num_pings == 14
    db.close()
    cursor = db.cursor()
    assert con_cls.num_pings == 15
    cursor.execute('select test')
    assert con_cls.num_pings == 16
    db.close()
    cursor = db.cursor()
    assert con_cls.num_pings == 17
    cursor.execute('select test')
    assert con_cls.num_pings == 18
    db.close()
    cursor.execute('select test')
    assert con_cls.num_pings == 20
    con_cls.has_ping = False
    con_cls.num_pings = 0


def test_begin_transaction():
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
    db = steady_db_connect(dbapi, database='ok')
    cursor = db.cursor()
    db.begin()
    cursor.execute('select test14')
    assert cursor.fetchone() == 'test14'
    db.cancel()
    cursor.execute('select test14')
    assert cursor.fetchone() == 'test14'


def test_with_cancel_extension():
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


def timeout_is_not_fatal(error):
    """A deliberate server side timeout does not break the connection."""
    return not error.args or error.args[0] != 3024


def always_fatal(error):  # noqa: ARG001
    return True


def never_fatal(error):  # noqa: ARG001
    return False


def test_connection_isfatal_must_be_callable():
    steady_db_connect(dbapi, isfatal=None)
    steady_db_connect(dbapi, isfatal=always_fatal)
    with pytest.raises(TypeError):
        steady_db_connect(dbapi, isfatal='always')
    with pytest.raises(TypeError):
        steady_db_connect(dbapi, isfatal=42)


def test_connection_isfatal_is_asked():
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
    db = steady_db_connect(dbapi)
    cursor = db.cursor()
    with cursor.no_failover():
        cursor.execute('select test')
    assert cursor.fetchone() == 'test'
    # in contrast to using the raw cursor, the usage is still counted
    assert db._usage == 1
    assert db._con.num_uses == 1


def test_cursor_no_failover_broken_connection():
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
    db = steady_db_connect(dbapi)
    con = db.dbapi_connection
    assert isinstance(con, dbapi.Connection)
    assert con is db._con
    db.close()
    db.cursor()  # transparently reopened
    assert db.dbapi_connection is db._con
    assert db.dbapi_connection is not con


def test_dbapi_cursor():
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
