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

import pg
import pytest

from dbutils.pooled_pg import (
    InvalidConnectionError,
    PooledPg,
    TooManyConnectionsError,
)
from dbutils.steady_pg import SteadyPgConnection


def test_version():
    """Check that the module and class versions are in sync."""
    from dbutils import __version__, pooled_pg
    assert pooled_pg.__version__ == __version__
    assert PooledPg.version == __version__


def test_create_connection():
    """Check that the pool creates connections with the given parameters."""
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
    # mincached=1, so one steady connection has been created up front
    db_con = pool._cache.get(0)
    pool._cache.put(db_con, 0)
    assert isinstance(db_con, SteadyPgConnection)
    # taking it out of the pool empties the cache
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
    # the connect parameters have been passed down to the connection
    assert hasattr(db, 'dbname')
    assert db.dbname == 'PooledPgTestDB'
    assert hasattr(db, 'user')
    assert db.user == 'PooledPgTestUser'
    db.query('select test')
    assert db.num_queries == 1


def test_create_connection_without_parameters():
    """Check that a pool can be created without connect parameters."""
    pool = PooledPg(1)
    db = pool.connection()
    assert hasattr(db, 'dbname')
    assert db.dbname is None
    assert hasattr(db, 'user')
    assert db.user is None
    assert hasattr(db, 'num_queries')
    assert db.num_queries == 0


def test_create_connection_with_settings():
    """Check that maxusage and setsession are passed on to the connections."""
    pool = PooledPg(0, 0, 0, False, 3, ('set datestyle',))
    assert pool._maxusage == 3
    assert pool._setsession == ('set datestyle',)
    db = pool.connection()
    assert db._maxusage == 3
    assert db._setsession_sql == ('set datestyle',)


def test_close_connection():
    """Check that a closed connection is returned to the pool."""
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


def test_close_all():
    """Check that closing the pool keeps the connections accounted for."""
    pool = PooledPg(0, 1, 1, False, None, None, False, 'PooledPgTestDB')
    assert pool._cache.qsize() == 0
    assert pool._connections._value == 1
    db = pool.connection()
    db_con = db._con
    db.close()
    # the cached connection has already given back its share of the
    # generally allowed connections when it was returned to the pool
    assert pool._cache.qsize() == 1
    assert pool._connections._value == 1
    pool.close()
    # closing the pool discards the cached connection,
    # but it must not give back its share a second time
    assert pool._cache.qsize() == 0
    assert pool._connections._value == 1
    assert db_con._closed
    # so the pool still hands out only one connection at a time
    db = pool.connection()
    assert db._con is not db_con
    assert pool._connections._value == 0
    with pytest.raises(TooManyConnectionsError):
        pool.connection()
    # closing the pool again (this also happens when it is deleted)
    # must not change the accounting while a connection is still in use
    pool.close()
    assert pool._connections._value == 0
    # the connection in use gives back its share when it is returned
    db.close()
    assert pool._cache.qsize() == 1
    assert pool._connections._value == 1


def test_connection_error_does_not_use_up_a_connection():
    """Check that a failing connection attempt is properly accounted for."""
    pool = PooledPg(0, 0, 1, False, None, None, False, dbname='ok')
    assert pool._cache.qsize() == 0
    assert pool._connections._value == 1
    # the mock database raises an error when the database is named 'error'
    pool._kwargs['dbname'] = 'error'
    with pytest.raises(pg.InternalError):
        pool.connection()
    pool._kwargs['dbname'] = 'ok'
    # the failed attempt must not have used up the allowed connection
    assert pool._connections._value == 1
    db = pool.connection()
    assert db.dbname == 'ok'
    assert pool._connections._value == 0
    # but the connection that could be established still counts
    with pytest.raises(TooManyConnectionsError):
        pool.connection()
    db.close()
    assert pool._connections._value == 1


@pytest.mark.parametrize(("mincached", "maxcached", "cached", "rounds"), [
    # every round takes the given number of connections out of the pool
    # and expects the given number of cached connections after closing them
    (3, 0, 3, [(3, 3), (6, 6)]),  # unlimited cache grows with the demand
    (3, None, 3, [(3, 3), (6, 6)]),  # None is the same as zero here
    (None, None, 0, [(3, 3), (6, 6)]),  # and also when nothing is cached
    (3, 4, 3, [(3, 3), (6, 4)]),  # cache fills up to maxcached
    (3, 2, 3, [(4, 3)]),  # mincached wins when it exceeds maxcached
    (2, 5, 2, [(10, 5)]),  # cache grows from mincached to maxcached
])
def test_min_max_cached(mincached, maxcached, cached, rounds):
    """Check that the cache is kept between the given bounds."""
    pool = PooledPg(mincached, maxcached)
    assert hasattr(pool, '_cache')
    assert pool._cache.qsize() == cached
    cache = []
    for taken, cached_again in rounds:
        for _i in range(taken):
            cache.append(pool.connection())
        assert pool._cache.qsize() == 0
        for _i in range(taken):
            cache.pop().close()
        assert pool._cache.qsize() == cached_again


def test_max_connections():
    """Check that the maximum number of connections is enforced."""
    pool = PooledPg(1, 2, 3)
    assert pool._cache.qsize() == 1
    cache = [pool.connection() for _i in range(3)]
    assert pool._cache.qsize() == 0
    with pytest.raises(TooManyConnectionsError):
        pool.connection()
    assert cache


def test_max_connections_unlimited():
    """Check that the number of connections is unlimited by default."""
    pool = PooledPg(0, 0, None)
    assert pool._connections is None
    cache = [pool.connection() for _i in range(10)]
    assert pool._cache.qsize() == 0
    assert cache


def test_max_connections_one():
    """Check that a pool can be limited to a single connection."""
    pool = PooledPg(0, 1, 1, False)
    assert pool._blocking == 0
    assert pool._cache.qsize() == 0
    db = pool.connection()
    assert pool._cache.qsize() == 0
    with pytest.raises(TooManyConnectionsError):
        pool.connection()
    assert db
    del db


def test_max_connections_raised_to_maxcached():
    """Check that maxconnections is raised to the value of maxcached."""
    pool = PooledPg(1, 2, 1)
    assert pool._cache.qsize() == 1
    cache = [pool.connection()]
    assert pool._cache.qsize() == 0
    cache.append(pool.connection())
    assert pool._cache.qsize() == 0
    with pytest.raises(TooManyConnectionsError):
        pool.connection()


def test_max_connections_raised_to_mincached():
    """Check that maxconnections is raised to the value of mincached."""
    pool = PooledPg(3, 2, 1, False)
    assert pool._cache.qsize() == 3
    cache = [pool.connection() for _i in range(3)]
    assert len(cache) == 3
    assert pool._cache.qsize() == 0
    with pytest.raises(TooManyConnectionsError):
        pool.connection()


def test_max_connections_blocking():
    """Check that a thread waits for a connection when blocking is set."""
    pool = PooledPg(1, 1, 1, True)
    assert pool._blocking == 1
    assert pool._cache.qsize() == 1
    db = pool.connection()
    assert pool._cache.qsize() == 0

    def connection():
        pool.connection().query('set thread')

    # the thread cannot get a connection and blocks instead of failing
    thread = Thread(target=connection)
    thread.start()
    thread.join(0.1)
    assert thread.is_alive()
    assert pool._cache.qsize() == 0
    session = db._con.session
    assert session == []
    # releasing the connection unblocks the thread, which then runs to the end
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
    """Check that one thread can use two connections at once."""
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
    """Check that a third thread must wait for a free connection."""
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
    """Check that an open transaction is rolled back by default."""
    pool = PooledPg(1)
    db = pool.connection()
    db.begin()
    con = db._con
    assert con._transaction
    db.query('select test')
    assert con.num_queries == 1
    # the transaction is rolled back, but nothing else is reset
    db.close()
    assert pool.connection()._con is con
    assert not con._transaction
    assert con.session == ['begin', 'rollback']
    assert con.num_queries == 1


def test_reset_transaction_always():
    """Check that a rollback is always issued when reset is 1."""
    pool = PooledPg(1, reset=1)
    db = pool.connection()
    db.begin()
    con = db._con
    assert con._transaction
    # the connection has already been rolled back when it was created
    assert con.session == ['rollback', 'begin']
    db.query('select test')
    assert con.num_queries == 1
    # and it is rolled back again when it is returned to the pool
    db.close()
    assert pool.connection()._con is con
    assert not con._transaction
    assert con.session == ['rollback', 'begin', 'rollback', 'rollback']
    assert con.num_queries == 1


def test_reset_transaction_completely():
    """Check that the connection is reopened when reset is 2."""
    pool = PooledPg(1, reset=2)
    db = pool.connection()
    db.begin()
    con = db._con
    assert con._transaction
    assert con.session == ['begin']
    db.query('select test')
    assert con.num_queries == 1
    # the connection is closed and reopened, so session and counters are gone
    db.close()
    assert pool.connection()._con is con
    assert not con._transaction
    assert con.session == []
    assert con.num_queries == 0


def test_reopen_connection():
    """Check that a pooled connection in use can be reopened."""
    pool = PooledPg(1)
    db = pool.connection()
    con = db._con
    db.query('select test')
    assert con.num_queries == 1
    # the underlying connection is reopened, which resets the counter
    db.reopen()
    assert db._con is con
    assert con.num_queries == 0
    assert db.query('select test') == 'test'
    assert con.num_queries == 1


def test_reopen_connection_after_closing():
    """Check that a connection that is back in the pool can be reopened."""
    pool = PooledPg(1)
    db = pool.connection()
    con = db._con
    db.close()
    assert db._con is None
    # the connection cannot be used any more when it has been closed
    with pytest.raises(InvalidConnectionError):
        db.query  # noqa: B018
    # but reopening takes another connection out of the pool
    db.reopen()
    assert db._con is not None
    assert db.query('select test') == 'test'
    assert con.num_queries == 1


def test_reopen_connection_does_not_nest_the_proxy():
    """Check that reopening does not wrap another pooled connection."""
    pool = PooledPg(1, 2, 3)
    db = pool.connection()
    con = db._con
    db.close()
    db.reopen()
    # the proxy must wrap the steady connection itself, not another proxy,
    # since otherwise the pool cache would fill up with nested proxies
    assert db._con is con
    assert isinstance(db._con, SteadyPgConnection)
    db.close()
    cached = pool._cache.get_nowait()
    assert cached is con
    assert isinstance(cached, SteadyPgConnection)
    pool._cache.put_nowait(cached)
    # reopening must not disturb the accounting of the allowed connections
    dbs = [pool.connection() for _ in range(3)]
    with pytest.raises(TooManyConnectionsError):
        pool.connection()
    while dbs:
        dbs.pop().close()


def test_context_manager():
    """Check that the connection can be used as a context manager."""
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
