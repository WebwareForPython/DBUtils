"""Test the PooledPg module.

Note:
We don't test performance here, so the test does not predicate
whether PooledPg actually will help in improving performance or not.
We also assume that the underlying SteadyPg connections are tested.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke
"""

from queue import Empty, Queue
from threading import Thread

import pg  # noqa: F401
import pytest

from dbutils.pooled_pg import (
    InvalidConnectionError,
    PooledPg,
    TooManyConnectionsError,
)
from dbutils.steady_pg import SteadyPgConnection


def test_version():
    from dbutils import __version__, pooled_pg
    assert pooled_pg.__version__ == __version__
    assert PooledPg.version == __version__


def test_create_connection():
    pool = PooledPg(
        1, 1, 0, False, None, None, False,
        'PooledPgTestDB', user='PooledPgTestUser')
    assert hasattr(pool, '_cache')
    assert pool._cache.qsize() == 1
    assert hasattr(pool, '_maxusage')
    assert pool._maxusage is None
    assert hasattr(pool, '_setsession')
    assert pool._setsession is None
    assert hasattr(pool, '_reset')
    assert not pool._reset
    db_con = pool._cache.get(0)
    pool._cache.put(db_con, 0)
    assert isinstance(db_con, SteadyPgConnection)
    db = pool.connection()
    assert pool._cache.qsize() == 0
    assert hasattr(db, '_con')
    assert db._con == db_con
    assert hasattr(db, 'query')
    assert hasattr(db, 'num_queries')
    assert db.num_queries == 0
    assert hasattr(db, '_maxusage')
    assert db._maxusage == 0
    assert hasattr(db, '_setsession_sql')
    assert db._setsession_sql is None
    assert hasattr(db, 'dbname')
    assert db.dbname == 'PooledPgTestDB'
    assert hasattr(db, 'user')
    assert db.user == 'PooledPgTestUser'
    db.query('select test')
    assert db.num_queries == 1
    pool = PooledPg(1)
    db = pool.connection()
    assert hasattr(db, 'dbname')
    assert db.dbname is None
    assert hasattr(db, 'user')
    assert db.user is None
    assert hasattr(db, 'num_queries')
    assert db.num_queries == 0
    pool = PooledPg(0, 0, 0, False, 3, ('set datestyle',))
    assert pool._maxusage == 3
    assert pool._setsession == ('set datestyle',)
    db = pool.connection()
    assert db._maxusage == 3
    assert db._setsession_sql == ('set datestyle',)


def test_close_connection():
    pool = PooledPg(
        0, 1, 0, False, None, None, False,
        'PooledPgTestDB', user='PooledPgTestUser')
    db = pool.connection()
    assert hasattr(db, '_con')
    db_con = db._con
    assert isinstance(db_con, SteadyPgConnection)
    assert hasattr(pool, '_cache')
    assert pool._cache.qsize() == 0
    assert db.num_queries == 0
    db.query('select test')
    assert db.num_queries == 1
    db.close()
    with pytest.raises(InvalidConnectionError):
        assert db.num_queries
    db = pool.connection()
    assert hasattr(db, 'dbname')
    assert db.dbname == 'PooledPgTestDB'
    assert hasattr(db, 'user')
    assert db.user == 'PooledPgTestUser'
    assert db.num_queries == 1
    db.query('select test')
    assert db.num_queries == 2
    db = pool.connection()
    assert pool._cache.qsize() == 1
    assert pool._cache.get(0) == db_con
    assert db
    del db


def test_min_max_cached():
    pool = PooledPg(3)
    assert hasattr(pool, '_cache')
    assert pool._cache.qsize() == 3
    cache = [pool.connection() for _i in range(3)]
    assert pool._cache.qsize() == 0
    for _i in range(3):
        cache.pop().close()
    assert pool._cache.qsize() == 3
    for _i in range(6):
        cache.append(pool.connection())
    assert pool._cache.qsize() == 0
    for _i in range(6):
        cache.pop().close()
    assert pool._cache.qsize() == 6
    pool = PooledPg(3, 4)
    assert hasattr(pool, '_cache')
    assert pool._cache.qsize() == 3
    cache = [pool.connection() for _i in range(3)]
    assert pool._cache.qsize() == 0
    for _i in range(3):
        cache.pop().close()
    assert pool._cache.qsize() == 3
    for _i in range(6):
        cache.append(pool.connection())
    assert pool._cache.qsize() == 0
    for _i in range(6):
        cache.pop().close()
    assert pool._cache.qsize() == 4
    pool = PooledPg(3, 2)
    assert hasattr(pool, '_cache')
    assert pool._cache.qsize() == 3
    cache = [pool.connection() for _i in range(4)]
    assert pool._cache.qsize() == 0
    for _i in range(4):
        cache.pop().close()
    assert pool._cache.qsize() == 3
    pool = PooledPg(2, 5)
    assert hasattr(pool, '_cache')
    assert pool._cache.qsize() == 2
    cache = [pool.connection() for _i in range(10)]
    assert pool._cache.qsize() == 0
    for _i in range(10):
        cache.pop().close()
    assert pool._cache.qsize() == 5


def test_max_connections():
    pool = PooledPg(1, 2, 3)
    assert pool._cache.qsize() == 1
    cache = [pool.connection() for _i in range(3)]
    assert pool._cache.qsize() == 0
    with pytest.raises(TooManyConnectionsError):
        pool.connection()
    pool = PooledPg(0, 1, 1, False)
    assert pool._blocking == 0
    assert pool._cache.qsize() == 0
    db = pool.connection()
    assert pool._cache.qsize() == 0
    with pytest.raises(TooManyConnectionsError):
        pool.connection()
    assert db
    del db
    assert cache
    del cache
    pool = PooledPg(1, 2, 1)
    assert pool._cache.qsize() == 1
    cache = [pool.connection()]
    assert pool._cache.qsize() == 0
    cache.append(pool.connection())
    assert pool._cache.qsize() == 0
    with pytest.raises(TooManyConnectionsError):
        pool.connection()
    pool = PooledPg(3, 2, 1, False)
    assert pool._cache.qsize() == 3
    cache = [pool.connection() for _i in range(3)]
    assert len(cache) == 3
    assert pool._cache.qsize() == 0
    with pytest.raises(TooManyConnectionsError):
        pool.connection()
    pool = PooledPg(1, 1, 1, True)
    assert pool._blocking == 1
    assert pool._cache.qsize() == 1
    db = pool.connection()
    assert pool._cache.qsize() == 0

    def connection():
        pool.connection().query('set thread')

    thread = Thread(target=connection)
    thread.start()
    thread.join(0.1)
    assert thread.is_alive()
    assert pool._cache.qsize() == 0
    session = db._con.session
    assert session == []
    del db
    thread.join(0.1)
    assert not thread.is_alive()
    assert pool._cache.qsize() == 1
    db = pool.connection()
    assert pool._cache.qsize() == 0
    assert session == ['thread']
    assert db
    del db


def test_one_thread_two_connections():
    pool = PooledPg(2)
    db1 = pool.connection()
    for _i in range(5):
        db1.query('select test')
    db2 = pool.connection()
    assert db1 != db2
    assert db1._con != db2._con
    for _i in range(7):
        db2.query('select test')
    assert db1.num_queries == 5
    assert db2.num_queries == 7
    del db1
    db1 = pool.connection()
    assert db1 != db2
    assert db1._con != db2._con
    assert hasattr(db1, 'query')
    for _i in range(3):
        db1.query('select test')
    assert db1.num_queries == 8
    db2.query('select test')
    assert db2.num_queries == 8


def test_three_threads_two_connections():
    pool = PooledPg(2, 2, 2, True)
    queue = Queue(3)

    def connection():
        queue.put(pool.connection(), timeout=1)

    for _i in range(3):
        Thread(target=connection).start()
    db1 = queue.get(timeout=1)
    db2 = queue.get(timeout=1)
    db1_con = db1._con
    db2_con = db2._con
    assert db1 != db2
    assert db1_con != db2_con
    with pytest.raises(Empty):
        queue.get(timeout=0.1)
    del db1
    db1 = queue.get(timeout=1)
    assert db1 != db2
    assert db1._con != db2._con
    assert db1._con == db1_con


def test_reset_transaction():
    pool = PooledPg(1)
    db = pool.connection()
    db.begin()
    con = db._con
    assert con._transaction
    db.query('select test')
    assert con.num_queries == 1
    db.close()
    assert pool.connection()._con is con
    assert not con._transaction
    assert con.session == ['begin', 'rollback']
    assert con.num_queries == 1
    pool = PooledPg(1, reset=1)
    db = pool.connection()
    db.begin()
    con = db._con
    assert con._transaction
    assert con.session == ['rollback', 'begin']
    db.query('select test')
    assert con.num_queries == 1
    db.close()
    assert pool.connection()._con is con
    assert not con._transaction
    assert con.session == ['rollback', 'begin', 'rollback', 'rollback']
    assert con.num_queries == 1
    pool = PooledPg(1, reset=2)
    db = pool.connection()
    db.begin()
    con = db._con
    assert con._transaction
    assert con.session == ['begin']
    db.query('select test')
    assert con.num_queries == 1
    db.close()
    assert pool.connection()._con is con
    assert not con._transaction
    assert con.session == []
    assert con.num_queries == 0


def test_context_manager():
    pool = PooledPg(1, 1, 1)
    with pool.connection() as db:
        db_con = db._con._con
        db.query('select test')
        assert db_con.num_queries == 1
        with pytest.raises(TooManyConnectionsError):
            pool.connection()
    with pool.connection() as db:
        db_con = db._con._con
        db.query('select test')
        assert db_con.num_queries == 2
        with pytest.raises(TooManyConnectionsError):
            pool.connection()
