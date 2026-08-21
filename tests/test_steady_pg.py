"""Test the SteadyPg module.

Note:
We do not test the real PyGreSQL module, but we just
mock the basic connection functionality of that module.
We assume that the PyGreSQL module will detect lost
connections correctly and set the status flag accordingly.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke
"""

import sys

import pg
import pytest

from dbutils.steady_pg import SteadyPgConnection


def test_version():
    """Check that the module and class versions are in sync."""
    from dbutils import __version__, steady_pg
    assert steady_pg.__version__ == __version__
    assert steady_pg.SteadyPgConnection.version == __version__


def test_mocked_connection():
    """Check that the mocked PyGreSQL connection behaves as expected."""
    db_cls = pg.DB
    db = db_cls(
        'SteadyPgTestDB', user='SteadyPgTestUser')
    assert hasattr(db, 'db')
    assert hasattr(db.db, 'status')
    assert db.db.status
    assert hasattr(db.db, 'query')
    assert hasattr(db.db, 'close')
    assert not hasattr(db.db, 'reopen')
    assert hasattr(db, 'reset')
    assert hasattr(db.db, 'num_queries')
    assert hasattr(db.db, 'session')
    assert not hasattr(db.db, 'get_tables')
    assert hasattr(db.db, 'db')
    assert db.db.db == 'SteadyPgTestDB'
    assert hasattr(db.db, 'user')
    assert db.db.user == 'SteadyPgTestUser'
    assert hasattr(db, 'query')
    assert hasattr(db, 'close')
    assert hasattr(db, 'reopen')
    assert hasattr(db, 'reset')
    assert hasattr(db, 'num_queries')
    assert hasattr(db, 'session')
    assert hasattr(db, 'get_tables')
    assert hasattr(db, 'dbname')
    assert db.dbname == 'SteadyPgTestDB'
    assert hasattr(db, 'user')
    assert db.user == 'SteadyPgTestUser'
    # queries are counted, and reopening the connection resets the counter
    for i in range(3):
        assert db.num_queries == i
        assert db.query(f'select test{i}') == f'test{i}'
    assert db.db.status
    db.reopen()
    assert db.db.status
    assert db.num_queries == 0
    assert db.query('select test4') == 'test4'
    assert db.get_tables() == 'test'
    # a closed connection cannot be used or closed again
    db.close()
    try:
        status = db.db.status
    except AttributeError:
        status = False
    assert not status
    with pytest.raises(pg.InternalError):
        db.close()
    with pytest.raises(pg.InternalError):
        db.query('select test')
    with pytest.raises(pg.InternalError):
        db.get_tables()


def test_broken_connection():
    """Check that errors when opening a connection are reported."""
    with pytest.raises(TypeError):
        SteadyPgConnection('wrong')
    db = SteadyPgConnection(dbname='ok')
    internal_error_cls = sys.modules[db._con.__module__].InternalError
    for _i in range(3):
        db.close()
    del db
    with pytest.raises(internal_error_cls):
        SteadyPgConnection(dbname='error')


@pytest.mark.parametrize("closeable", [False, True])
def test_close(closeable):
    """Check that closing is only allowed when the connection is closeable."""
    db = SteadyPgConnection(closeable=closeable)
    assert db._con.db
    assert db._con.valid is True
    db.close()
    assert closeable ^ (db._con.db is not None and db._con.valid)
    db.close()
    assert closeable ^ (db._con.db is not None and db._con.valid)
    db._close()
    assert not db._con.db
    db._close()
    assert not db._con.db


def test_connection():
    """Check that the connection wraps the PyGreSQL connection."""
    db = SteadyPgConnection(
        0, None, 1, 'SteadyPgTestDB', user='SteadyPgTestUser')
    assert hasattr(db, 'db')
    assert hasattr(db, '_con')
    assert db.db == db._con.db
    assert hasattr(db, '_usage')
    assert db._usage == 0
    assert hasattr(db.db, 'status')
    assert db.db.status
    assert hasattr(db.db, 'query')
    assert hasattr(db.db, 'close')
    assert not hasattr(db.db, 'reopen')
    assert hasattr(db.db, 'reset')
    assert hasattr(db.db, 'num_queries')
    assert hasattr(db.db, 'session')
    assert hasattr(db.db, 'db')
    assert db.db.db == 'SteadyPgTestDB'
    assert hasattr(db.db, 'user')
    assert db.db.user == 'SteadyPgTestUser'
    assert not hasattr(db.db, 'get_tables')
    assert hasattr(db, 'query')
    assert hasattr(db, 'close')
    assert hasattr(db, 'reopen')
    assert hasattr(db, 'reset')
    assert hasattr(db, 'num_queries')
    assert hasattr(db, 'session')
    assert hasattr(db, 'dbname')
    assert db.dbname == 'SteadyPgTestDB'
    assert hasattr(db, 'user')
    assert db.user == 'SteadyPgTestUser'
    assert hasattr(db, 'get_tables')
    # the wrapper keeps its own usage count next to the query count,
    # and get_tables() counts as a use, but not as a query
    for i in range(3):
        assert db._usage == i
        assert db.num_queries == i
        assert db.query(f'select test{i}') == f'test{i}'
    assert db.db.status
    assert db.get_tables() == 'test'
    assert db.db.status
    assert db._usage == 4
    assert db.num_queries == 3
    # reopening the connection resets both counters
    db.reopen()
    assert db.db.status
    assert db._usage == 0
    assert db.num_queries == 0
    assert db.query('select test') == 'test'
    assert db.db.status
    assert hasattr(db._con, 'status')
    assert db._con.status


def test_connection_close():
    """Check that closing the connection closes the PyGreSQL connection."""
    db = SteadyPgConnection(
        0, None, 1, 'SteadyPgTestDB', user='SteadyPgTestUser')
    db.query('select test')
    assert db.db.status
    db.close()
    try:
        status = db.db.status
    except AttributeError:
        status = False
    assert not status
    # the underlying connection is still wrapped, but cannot be used any more
    assert hasattr(db._con, 'close')
    assert hasattr(db._con, 'query')
    internal_error_cls = sys.modules[db._con.__module__].InternalError
    with pytest.raises(internal_error_cls):
        db._con.close()
    with pytest.raises(internal_error_cls):
        db._con.query('select test')


def test_connection_reopen_when_broken():
    """Check that the PyGreSQL connection is transparently reopened."""
    db = SteadyPgConnection(
        0, None, 1, 'SteadyPgTestDB', user='SteadyPgTestUser')
    # querying a closed connection reopens it and starts counting anew
    db.close()
    assert db.query('select test') == 'test'
    assert db.db.status
    assert db._usage == 1
    assert db.num_queries == 1
    # the same happens when the connection reports a bad status
    db.db.status = False
    assert not db.db.status
    assert db.query('select test') == 'test'
    assert db.db.status
    assert db._usage == 1
    assert db.num_queries == 1
    # and when it is used through one of the PyGreSQL extension methods
    db.db.status = False
    assert not db.db.status
    assert db.get_tables() == 'test'
    assert db.db.status
    assert db._usage == 1
    assert db.num_queries == 0


def test_connection_context_handler():
    """Check that the context handler commits or rolls back."""
    db = SteadyPgConnection(
        0, None, 1, 'SteadyPgTestDB', user='SteadyPgTestUser')
    assert db.session == []
    with db:
        db.query('select test')
    assert db.session == ['begin', 'commit']
    try:
        with db:
            db.query('error')
    except pg.ProgrammingError:
        error = True
    else:
        error = False
    assert error
    assert db._con.session == ['begin', 'commit', 'begin', 'rollback']


def test_connection_maxusage():
    """Check that the connection is reset when used too often."""
    db = SteadyPgConnection(10)
    # the connection is silently reset after every 10 uses
    for i in range(100):
        r = db.query(f'select test{i}')
        assert r == f'test{i}'
        assert db.db.status
        j = i % 10 + 1
        assert db._usage == j
        assert db.num_queries == j
    # inside a transaction the reset is postponed until it has been ended,
    # so the usage count keeps growing beyond the maximum until then
    db.begin()
    for i in range(100):
        r = db.get_tables()
        assert r == 'test'
        assert db.db.status
        if i == 49:
            db.commit()
        j = i % 10 + 1 if i > 49 else i + 11
        assert db._usage == j
        j = 0 if i > 49 else 10
        assert db.num_queries == j
    # a connection that breaks in between is reset early,
    # which also restarts the counting of the uses
    for i in range(10):
        if i == 7:
            db.db.status = False
        r = db.query(f'select test{i}')
        assert r == f'test{i}'
        j = i % 7 + 1
        assert db._usage == j
        assert db.num_queries == j
    for i in range(10):
        if i == 5:
            db.db.status = False
        r = db.get_tables()
        assert r == 'test'
        j = (i + (3 if i < 5 else -5)) % 10 + 1
        assert db._usage == j
        j = 3 if i < 5 else 0
        assert db.num_queries == j
    # closing and reopening the connection restart the counting as well
    db.close()
    assert db.query('select test1') == 'test1'
    assert db._usage == 1
    assert db.num_queries == 1
    db.reopen()
    assert db._usage == 0
    assert db.num_queries == 0
    assert db.query('select test2') == 'test2'
    assert db._usage == 1
    assert db.num_queries == 1


def test_connection_setsession():
    """Check that the session is prepared after every reopening."""
    db = SteadyPgConnection(3, ('set time zone', 'set datestyle'))
    assert hasattr(db, 'num_queries')
    assert db.num_queries == 0
    assert hasattr(db, 'session')
    assert tuple(db.session) == ('time zone', 'datestyle')
    for _i in range(11):
        db.query('select test')
    assert db.num_queries == 2
    assert db.session == ['time zone', 'datestyle']
    db.query('set test')
    assert db.num_queries == 2
    assert db.session == ['time zone', 'datestyle', 'test']
    db.query('select test')
    assert db.num_queries == 1
    assert db.session == ['time zone', 'datestyle']
    db.close()
    db.query('set test')
    assert db.num_queries == 0
    assert db.session == ['time zone', 'datestyle', 'test']


@pytest.mark.parametrize("closeable", [False, True])
def test_begin(closeable):
    """Check that transparent reopening is suspended after begin()."""
    db = SteadyPgConnection(closeable=closeable)
    db.begin()
    assert db.session == ['begin']
    db.query('select test')
    assert db.num_queries == 1
    db.close()
    db.query('select test')
    assert db.num_queries == 1
    db.begin()
    assert db.session == ['begin']
    db.db.close()
    with pytest.raises(pg.InternalError):
        db.query('select test')
    assert db.num_queries == 0
    db.query('select test')
    assert db.num_queries == 1
    assert db.begin('select sql:begin') == 'sql:begin'
    assert db.num_queries == 2


@pytest.mark.parametrize("closeable", [False, True])
@pytest.mark.parametrize("end", ["end", "commit", "rollback"])
def test_end(closeable, end):
    """Check that end(), commit() and rollback() finish the transaction."""
    db = SteadyPgConnection(closeable=closeable)
    db.begin()
    db.query('select test')
    getattr(db, end)()
    assert db.session == ['begin', end]
    # the transaction is over, so the connection is reopened transparently
    db.db.close()
    db.query('select test')
    assert db.num_queries == 1
    # a transaction can also be started with an explicit SQL command
    assert db.begin(f'select sql:{end}') == f'sql:{end}'
    assert db.num_queries == 2
