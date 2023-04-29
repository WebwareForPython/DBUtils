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
    from dbutils import __version__, steady_pg
    assert steady_pg.__version__ == __version__
    assert steady_pg.SteadyPgConnection.version == __version__


def test_mocked_connection():
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
    for i in range(3):
        assert db.num_queries == i
        assert db.query(f'select test{i}') == f'test{i}'
    assert db.db.status
    db.reopen()
    assert db.db.status
    assert db.num_queries == 0
    assert db.query('select test4') == 'test4'
    assert db.get_tables() == 'test'
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
    for i in range(3):
        assert db._usage == i
        assert db.num_queries == i
        assert db.query(f'select test{i}') == f'test{i}'
    assert db.db.status
    assert db.get_tables() == 'test'
    assert db.db.status
    assert db._usage == 4
    assert db.num_queries == 3
    db.reopen()
    assert db.db.status
    assert db._usage == 0
    assert db.num_queries == 0
    assert db.query('select test') == 'test'
    assert db.db.status
    assert hasattr(db._con, 'status')
    assert db._con.status
    assert hasattr(db._con, 'close')
    assert hasattr(db._con, 'query')
    db.close()
    try:
        status = db.db.status
    except AttributeError:
        status = False
    assert not status
    assert hasattr(db._con, 'close')
    assert hasattr(db._con, 'query')
    internal_error_cls = sys.modules[db._con.__module__].InternalError
    with pytest.raises(internal_error_cls):
        db._con.close()
    with pytest.raises(internal_error_cls):
        db._con.query('select test')
    assert db.query('select test') == 'test'
    assert db.db.status
    assert db._usage == 1
    assert db.num_queries == 1
    db.db.status = False
    assert not db.db.status
    assert db.query('select test') == 'test'
    assert db.db.status
    assert db._usage == 1
    assert db.num_queries == 1
    db.db.status = False
    assert not db.db.status
    assert db.get_tables() == 'test'
    assert db.db.status
    assert db._usage == 1
    assert db.num_queries == 0


def test_connection_context_handler():
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
    db = SteadyPgConnection(10)
    for i in range(100):
        r = db.query(f'select test{i}')
        assert r == f'test{i}'
        assert db.db.status
        j = i % 10 + 1
        assert db._usage == j
        assert db.num_queries == j
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
def test_end(closeable):
    db = SteadyPgConnection(closeable=closeable)
    db.begin()
    db.query('select test')
    db.end()
    assert db.session == ['begin', 'end']
    db.db.close()
    db.query('select test')
    assert db.num_queries == 1
    assert db.begin('select sql:end') == 'sql:end'
    assert db.num_queries == 2
    db.begin()
    db.query('select test')
    db.commit()
    assert db.session == ['begin', 'commit']
    db.db.close()
    db.query('select test')
    assert db.num_queries == 1
    assert db.begin('select sql:commit') == 'sql:commit'
    assert db.num_queries == 2
    db.begin()
    db.query('select test')
    db.rollback()
    assert db.session == ['begin', 'rollback']
    db.db.close()
    db.query('select test')
    assert db.num_queries == 1
    assert db.begin('select sql:rollback') == 'sql:rollback'
    assert db.num_queries == 2
