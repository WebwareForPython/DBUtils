"""Test the PooledDB module.

Note:
We don't test performance here, so the test does not predicate
whether PooledDB actually will help in improving performance or not.
We also assume that the underlying SteadyDB connections are tested.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke
"""

from queue import Empty, Queue
from threading import Thread

import pytest

from dbutils.pooled_db import (
    InvalidConnectionError,
    NotSupportedError,
    PooledDB,
    SharedDBConnection,
    TooManyConnectionsError,
)
from dbutils.steady_db import SteadyDBConnection


def test_version():
    """Check that the module and class versions are in sync."""
    from dbutils import __version__, pooled_db
    assert pooled_db.__version__ == __version__
    assert PooledDB.version == __version__


@pytest.mark.parametrize("threadsafety", [None, 0])
def test_no_threadsafety(dbapi, threadsafety):
    """Check that a database module that is not thread-safe is rejected."""
    dbapi.threadsafety = threadsafety
    with pytest.raises(NotSupportedError):
        PooledDB(dbapi)


def test_creator_function(dbapi):
    """Check that a creator function can be used instead of a module."""
    pool = PooledDB(dbapi.connect, 1, database='ok')
    # the threadsafety cannot be determined from a plain creator function,
    # so the connections are optimistically assumed to be thread-safe,
    # but not safe enough to be shared between several threads
    assert pool._maxshared == 0
    db = pool.connection()
    assert db.threadsafety() == dbapi.threadsafety
    cursor = db.cursor()
    cursor.execute('select test')
    assert cursor.fetchone() == 'test'


def test_creator_without_threadsafety(dbapi):
    """Check that a creator that hides its threadsafety is rejected."""

    class Creator:
        """A database module that does not report its threadsafety."""

        connect = staticmethod(dbapi.connect)

    with pytest.raises(NotSupportedError):
        PooledDB(Creator)


def test_creator_with_unsafe_connections(dbapi, monkeypatch):
    """Check that connections that are not thread-safe are rejected."""
    monkeypatch.delattr(dbapi, 'threadsafety')
    # the pool optimistically assumes that a creator function provides
    # thread-safe connections, but the connections themselves know better
    pool = PooledDB(dbapi.connect, 0)
    with pytest.raises(NotSupportedError):
        pool.connection()


@pytest.mark.parametrize("threadsafety", [1, 2, 3])
def test_threadsafety(dbapi, threadsafety):
    """Check that connections are only shared when they may be."""
    dbapi.threadsafety = threadsafety
    pool = PooledDB(dbapi, 0, 0, 1)
    assert hasattr(pool, '_maxshared')
    if threadsafety > 1:
        assert pool._maxshared == 1
        assert hasattr(pool, '_shared_cache')
    else:
        assert pool._maxshared == 0
        assert not hasattr(pool, '_shared_cache')


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_create_connection(dbapi, threadsafety):
    """Check that the pool creates connections with the given parameters."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(
        dbapi, 1, 1, 1, 0, False, None, None, True, None, None, None,
        'PooledDBTestDB', user='PooledDBTestUser')
    # mincached=1, so one connection has been created up front
    assert hasattr(pool, '_idle_cache')
    assert len(pool._idle_cache) == 1
    if shareable:
        assert hasattr(pool, '_shared_cache')
        assert len(pool._shared_cache) == 0
    else:
        assert not hasattr(pool, '_shared_cache')
    assert hasattr(pool, '_maxusage')
    assert pool._maxusage is None
    assert hasattr(pool, '_setsession')
    assert pool._setsession is None
    # the cached connection is a steady connection without extra settings
    con = pool._idle_cache[0]
    assert isinstance(con, SteadyDBConnection)
    assert hasattr(con, '_maxusage')
    assert con._maxusage == 0
    assert hasattr(con, '_setsession_sql')
    assert con._setsession_sql is None
    # taking it out of the pool moves it from the idle to the shared cache
    db = pool.connection()
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 1
    assert hasattr(db, '_con')
    assert db._con == con
    assert hasattr(db, 'cursor')
    assert hasattr(db, '_usage')
    assert db._usage == 0
    # the connect parameters have been passed down to the DB-API 2 connection
    assert hasattr(con, '_con')
    db_con = con._con
    assert hasattr(db_con, 'database')
    assert db_con.database == 'PooledDBTestDB'
    assert hasattr(db_con, 'user')
    assert db_con.user == 'PooledDBTestUser'
    assert hasattr(db_con, 'open_cursors')
    assert db_con.open_cursors == 0
    assert hasattr(db_con, 'num_uses')
    assert db_con.num_uses == 0
    assert hasattr(db_con, 'num_queries')
    assert db_con.num_queries == 0
    # a query opens and closes a cursor and counts as one query and one use
    cursor = db.cursor()
    assert db_con.open_cursors == 1
    cursor.execute('select test')
    r = cursor.fetchone()
    cursor.close()
    assert db_con.open_cursors == 0
    assert r == 'test'
    assert db_con.num_queries == 1
    assert db._usage == 1
    # two cursors can be open at the same time on the same connection,
    # and a "set" command is recorded in the session instead of as a query
    cursor = db.cursor()
    assert db_con.open_cursors == 1
    cursor.execute('set sessiontest')
    cursor2 = db.cursor()
    assert db_con.open_cursors == 2
    cursor2.close()
    assert db_con.open_cursors == 1
    cursor.close()
    assert db_con.open_cursors == 0
    assert db_con.num_queries == 1
    assert db._usage == 2
    assert db_con.session == ['rollback', 'sessiontest']


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_dedicated_connection(dbapi, threadsafety):
    """Check the difference between shared and dedicated connections."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 1, 1, 1)
    assert len(pool._idle_cache) == 1
    if shareable:
        assert len(pool._shared_cache) == 0
    # connection() defaults to a shared connection
    db = pool.connection()
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 1
    db.close()
    assert len(pool._idle_cache) == 1
    if shareable:
        assert len(pool._shared_cache) == 0
    # asking for a shared connection explicitly does the same
    db = pool.connection(True)
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 1
    db.close()
    assert len(pool._idle_cache) == 1
    if shareable:
        assert len(pool._shared_cache) == 0
    # a dedicated connection never enters the shared cache
    db = pool.connection(False)
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 0
    assert db._usage == 0
    db_con = db._con._con
    assert db_con.database is None
    assert db_con.user is None
    db.close()
    assert len(pool._idle_cache) == 1
    if shareable:
        assert len(pool._shared_cache) == 0
    # dedicated_connection() is a shortcut for connection(False)
    db = pool.dedicated_connection()
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 0
    assert db._usage == 0
    db_con = db._con._con
    assert db_con.database is None
    assert db_con.user is None
    db.close()
    assert len(pool._idle_cache) == 1
    if shareable:
        assert len(pool._shared_cache) == 0


def test_create_connection_with_settings(dbapi):
    """Check that maxusage and setsession are passed on to the connections."""
    pool = PooledDB(dbapi, 0, 0, 0, 0, False, 3, ('set datestyle',))
    assert pool._maxusage == 3
    assert pool._setsession == ('set datestyle',)
    con = pool.connection()._con
    assert con._maxusage == 3
    assert con._setsession_sql == ('set datestyle',)


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_close_connection(dbapi, threadsafety):
    """Check that a closed connection is returned to the pool."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(
        dbapi, 0, 1, 1, 0, False, None, None, True, None, None, None,
        'PooledDBTestDB', user='PooledDBTestUser')
    assert hasattr(pool, '_idle_cache')
    assert len(pool._idle_cache) == 0
    # take a connection out of the pool and note its underlying connection
    db = pool.connection()
    assert hasattr(db, '_con')
    con = db._con
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 1
        assert hasattr(db, '_shared_con')
        shared_con = db._shared_con
        assert pool._shared_cache[0] == shared_con
        assert hasattr(shared_con, 'shared')
        assert shared_con.shared == 1
        assert hasattr(shared_con, 'con')
        assert shared_con.con == con
    assert isinstance(con, SteadyDBConnection)
    assert hasattr(con, '_con')
    db_con = con._con
    assert hasattr(db_con, 'num_queries')
    assert db._usage == 0
    assert db_con.num_queries == 0
    db.cursor().execute('select test')
    assert db._usage == 1
    assert db_con.num_queries == 1
    # closing the pooled connection invalidates it, but returns the
    # underlying connection to the idle cache instead of closing it
    db.close()
    assert db._con is None
    if shareable:
        assert db._shared_con is None
        assert shared_con.shared == 0
    with pytest.raises(InvalidConnectionError):
        assert db._usage
    assert not hasattr(db_con, '_num_queries')
    assert len(pool._idle_cache) == 1
    assert pool._idle_cache[0]._con == db_con
    if shareable:
        assert len(pool._shared_cache) == 0
    # closing it a second time is a no-op
    db.close()
    if shareable:
        assert shared_con.shared == 0
    # the next request gets the same underlying connection back,
    # with its usage counters and connect parameters still intact
    db = pool.connection()
    assert db._con == con
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 1
        shared_con = db._shared_con
        assert pool._shared_cache[0] == shared_con
        assert shared_con.con == con
        assert shared_con.shared == 1
    assert db._usage == 1
    assert db_con.num_queries == 1
    assert hasattr(db_con, 'database')
    assert db_con.database == 'PooledDBTestDB'
    assert hasattr(db_con, 'user')
    assert db_con.user == 'PooledDBTestUser'
    db.cursor().execute('select test')
    assert db_con.num_queries == 2
    db.cursor().execute('select test')
    assert db_con.num_queries == 3
    db.close()
    assert len(pool._idle_cache) == 1
    assert pool._idle_cache[0]._con == db_con
    if shareable:
        assert len(pool._shared_cache) == 0
    # a dedicated connection is returned to the idle cache as well
    db = pool.connection(False)
    assert db._con == con
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 0
    db.close()
    assert len(pool._idle_cache) == 1
    if shareable:
        assert len(pool._shared_cache) == 0


def test_close_all(dbapi):
    """Check that closing the pool empties the idle cache."""
    pool = PooledDB(dbapi, 10)
    assert len(pool._idle_cache) == 10
    pool.close()
    assert len(pool._idle_cache) == 0


def test_close_all_when_pool_is_deleted(dbapi):
    """Check that deleting the pool closes the cached connections."""
    pool = PooledDB(dbapi, 10)
    closed = ['no']

    def close(what=closed):
        what[0] = 'yes'

    pool._idle_cache[7]._con.close = close
    assert closed == ['no']
    del pool
    assert closed == ['yes']


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_close_all_shared(dbapi, threadsafety):
    """Check that closing the pool empties the shared cache as well."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 10, 10, 5)
    assert len(pool._idle_cache) == 10
    if shareable:
        assert len(pool._shared_cache) == 0
    cache = []
    for _i in range(5):
        cache.append(pool.connection())
    assert len(pool._idle_cache) == 5
    if shareable:
        assert len(pool._shared_cache) == 5
    pool.close()
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 0


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_close_all_shared_when_pool_is_deleted(dbapi, threadsafety):
    """Check that deleting the pool closes idle and shared connections."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 10, 10, 5)
    closed = []

    def close_idle(what=closed):
        what.append('idle')

    def close_shared(what=closed):
        what.append('shared')

    # spy on one idle and one shared connection (or, when connections
    # cannot be shared, on a second idle connection closed after the first)
    if shareable:
        cache = []
        for _i in range(5):
            cache.append(pool.connection())
        pool._shared_cache[3].con.close = close_shared
    else:
        pool._idle_cache[7]._con.close = close_shared
    pool._idle_cache[3]._con.close = close_idle
    assert closed == []
    del pool
    if shareable:
        del cache
    assert closed == ['idle', 'shared']


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_shareable_connection(dbapi, threadsafety):
    """Check that connections are shared when the maximum is reached."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 0, 1, 2)
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 0
    # the first two requests get connections of their own
    db1 = pool.connection()
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 1
    db2 = pool.connection()
    assert db1._con != db2._con
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 2
    # maxshared is reached now, so the next requests share those connections
    db3 = pool.connection()
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 2
        assert db3._con == db1._con
        assert db1._shared_con.shared == 2
        assert db2._shared_con.shared == 1
    else:
        assert db3._con != db1._con
        assert db3._con != db2._con
    db4 = pool.connection()
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 2
        assert db4._con == db2._con
        assert db1._shared_con.shared == 2
        assert db2._shared_con.shared == 2
    else:
        assert db4._con != db1._con
        assert db4._con != db2._con
        assert db4._con != db3._con
    # a dedicated connection is never taken from the shared cache
    db5 = pool.connection(False)
    assert db5._con != db1._con
    assert db5._con != db2._con
    assert db5._con != db3._con
    assert db5._con != db4._con
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 2
        assert db1._shared_con.shared == 2
        assert db2._shared_con.shared == 2
    # and once returned it stays in the idle cache,
    # since a shareable request prefers to share an existing connection
    db5.close()
    assert len(pool._idle_cache) == 1
    db5 = pool.connection()
    if shareable:
        assert len(pool._idle_cache) == 1
        assert len(pool._shared_cache) == 2
        assert db5._shared_con.shared == 3
    else:
        assert len(pool._idle_cache) == 0


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_unshare_connection(dbapi, threadsafety):
    """Check that a shared connection is cached again when fully unshared."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 0, 0, 1)
    assert len(pool._idle_cache) == 0
    db1 = pool.connection(False)
    if shareable:
        assert len(pool._shared_cache) == 0
    db2 = pool.connection()
    if shareable:
        assert len(pool._shared_cache) == 1
    db3 = pool.connection()
    if shareable:
        assert len(pool._shared_cache) == 1
        assert db2._con == db3._con
    else:
        assert db2._con != db3._con
    # dropping one of the two sharers leaves the connection shared once,
    # so it is not cached as idle yet
    del db3
    if shareable:
        assert len(pool._idle_cache) == 0
        assert len(pool._shared_cache) == 1
    else:
        assert len(pool._idle_cache) == 1
    # dropping the last sharer moves it back to the idle cache
    del db2
    if shareable:
        assert len(pool._idle_cache) == 1
        assert len(pool._shared_cache) == 0
    else:
        assert len(pool._idle_cache) == 2
    del db1
    if shareable:
        assert len(pool._idle_cache) == 2
        assert len(pool._shared_cache) == 0
    else:
        assert len(pool._idle_cache) == 3


@pytest.mark.parametrize("threadsafety", [1, 2])
@pytest.mark.parametrize(("mincached", "maxcached", "cached", "rounds"), [
    # every round takes the given number of connections out of the pool
    # and expects the given number of idle connections after releasing them
    (3, 0, 3, [(3, 3), (6, 6)]),  # unlimited cache grows with the demand
    (3, None, 3, [(3, 3), (6, 6)]),  # None is the same as zero here
    (None, None, 0, [(3, 3), (6, 6)]),  # and also when nothing is cached
    (0, 3, 0, [(3, 3), (6, 3)]),  # cache fills up to maxcached
    (3, 3, 3, [(3, 3), (6, 3)]),  # cache stays at the common bound
    (3, 2, 3, [(4, 3)]),  # mincached wins when it exceeds maxcached
    (2, 5, 2, [(10, 5)]),  # cache grows from mincached to maxcached
])
def test_min_max_cached(dbapi, threadsafety,
                        mincached, maxcached, cached, rounds):
    """Check that the idle cache is kept between the given bounds."""
    dbapi.threadsafety = threadsafety
    pool = PooledDB(dbapi, mincached, maxcached)
    assert len(pool._idle_cache) == cached
    for taken, cached_again in rounds:
        cache = [pool.connection() for _i in range(taken)]
        assert len(pool._idle_cache) == 0
        assert cache
        del cache
        assert len(pool._idle_cache) == cached_again


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_min_max_cached_with_shared(dbapi, threadsafety):
    """Check the idle cache bounds when connections can also be shared."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 1, 2, 3)
    assert len(pool._idle_cache) == 1
    # dedicated connections are cached up to maxcached when released
    cache = [pool.connection(False) for _i in range(4)]
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 0
    assert cache
    del cache
    assert len(pool._idle_cache) == 2
    # shared connections do not touch the idle cache while they are in use
    cache = [pool.connection() for _i in range(10)]
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 3
    assert cache
    del cache
    assert len(pool._idle_cache) == 2
    if shareable:
        assert len(pool._shared_cache) == 0


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_min_max_cached_with_fewer_shared(dbapi, threadsafety):
    """Check the idle cache bounds when maxshared is below maxcached."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 1, 3, 2)
    assert len(pool._idle_cache) == 1
    cache = [pool.connection(False) for _i in range(4)]
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 0
    assert cache
    del cache
    assert len(pool._idle_cache) == 3
    # only maxshared connections are needed, so one stays in the idle cache
    cache = [pool.connection() for _i in range(10)]
    if shareable:
        assert len(pool._idle_cache) == 1
        assert len(pool._shared_cache) == 2
    else:
        assert len(pool._idle_cache) == 0
    assert cache
    del cache
    assert len(pool._idle_cache) == 3
    if shareable:
        assert len(pool._shared_cache) == 0


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_max_shared(dbapi, threadsafety):
    """Check that the maximum number of shared connections is not exceeded."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi)
    assert len(pool._idle_cache) == 0
    cache = [pool.connection() for _i in range(10)]
    assert len(cache) == 10
    assert len(pool._idle_cache) == 0
    pool = PooledDB(dbapi, 1, 1, 0)
    assert len(pool._idle_cache) == 1
    cache = [pool.connection() for _i in range(10)]
    assert len(cache) == 10
    assert len(pool._idle_cache) == 0
    pool = PooledDB(dbapi, 0, 0, 1)
    cache = [pool.connection() for _i in range(10)]
    assert len(cache) == 10
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 1
    pool = PooledDB(dbapi, 1, 1, 1)
    assert len(pool._idle_cache) == 1
    cache = [pool.connection() for _i in range(10)]
    assert len(cache) == 10
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 1
    pool = PooledDB(dbapi, 0, 0, 7)
    cache = [pool.connection(False) for _i in range(3)]
    assert len(cache) == 3
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 0
    cache = [pool.connection() for _i in range(10)]
    assert len(cache) == 10
    assert len(pool._idle_cache) == 3
    if shareable:
        assert len(pool._shared_cache) == 7


def test_sort_shared(dbapi):
    """Check that shared connections are sorted by transaction and shares."""
    pool = PooledDB(dbapi, 0, 4, 4)
    cache = []
    for _i in range(6):
        db = pool.connection()
        db.cursor().execute('select test')
        cache.append(db)
    for i, db in enumerate(cache):
        assert db._shared_con.shared == 1 if 2 <= i < 4 else 2
    cache[2].begin()
    cache[3].begin()
    db = pool.connection()
    assert db._con is cache[0]._con
    db.close()
    cache[3].rollback()
    db = pool.connection()
    assert db._con is cache[3]._con


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_equally_shared(dbapi, threadsafety):
    """Check that the load is spread equally over the connections."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 5, 5, 5)
    assert len(pool._idle_cache) == 5
    for _i in range(15):
        db = pool.connection(False)
        db.cursor().execute('select test')
        db.close()
    assert len(pool._idle_cache) == 5
    for i in range(5):
        con = pool._idle_cache[i]
        assert con._usage == 3
        assert con._con.num_queries == 3
    cache = []
    for _i in range(35):
        db = pool.connection()
        db.cursor().execute('select test')
        cache.append(db)
        del db
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 5
        for i in range(5):
            con = pool._shared_cache[i]
            assert con.shared == 7
            con = con.con
            assert con._usage == 10
            assert con._con.num_queries == 10
    del cache
    assert len(pool._idle_cache) == 5
    if shareable:
        assert len(pool._shared_cache) == 0


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_many_shared(dbapi, threadsafety):
    """Check that many shared connections are counted correctly."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 0, 0, 5)
    # 35 requests are spread evenly over the 5 shareable connections,
    # each of which then carries 7 shares and 3 uses per share
    cache = []
    for _i in range(35):
        db = pool.connection()
        db.cursor().execute('select test1')
        db.cursor().execute('select test2')
        db.cursor().callproc('test3')
        cache.append(db)
        del db
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 5
        for i in range(5):
            con = pool._shared_cache[i]
            assert con.shared == 7
            con = con.con
            assert con._usage == 21
            assert con._con.num_queries == 14
        # dropping 6 of the requests unshares the connections unevenly,
        # and re-sorts the cache so that the least shared one comes first
        cache[3] = cache[8] = cache[33] = None
        cache[12] = cache[17] = cache[34] = None
        assert len(pool._shared_cache) == 5
        assert pool._shared_cache[0].shared == 7
        assert pool._shared_cache[1].shared == 7
        assert pool._shared_cache[2].shared == 5
        assert pool._shared_cache[3].shared == 4
        assert pool._shared_cache[4].shared == 6
        # 6 new requests fill up the gaps, so the load is balanced again
        for db in cache:
            if db:
                db.cursor().callproc('test4')
        for _i in range(6):
            db = pool.connection()
            db.cursor().callproc('test4')
            cache.append(db)
            del db
        for i in range(5):
            con = pool._shared_cache[i]
            assert con.shared == 7
            con = con.con
            assert con._usage == 28
            assert con._con.num_queries == 14
    del cache
    if shareable:
        assert len(pool._idle_cache) == 5
        assert len(pool._shared_cache) == 0
    else:
        assert len(pool._idle_cache) == 35


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_rollback(dbapi, threadsafety):
    """Check that connections are rolled back when returned to the pool."""
    dbapi.threadsafety = threadsafety
    pool = PooledDB(dbapi, 0, 1)
    assert len(pool._idle_cache) == 0
    db = pool.connection(False)
    assert len(pool._idle_cache) == 0
    assert db._con._con.open_cursors == 0
    cursor = db.cursor()
    assert db._con._con.open_cursors == 1
    cursor.execute('set doit1')
    db.commit()
    cursor.execute('set dont1')
    cursor.close()
    assert db._con._con.open_cursors == 0
    del db
    assert len(pool._idle_cache) == 1
    db = pool.connection(False)
    assert len(pool._idle_cache) == 0
    assert db._con._con.open_cursors == 0
    cursor = db.cursor()
    assert db._con._con.open_cursors == 1
    cursor.execute('set doit2')
    cursor.close()
    assert db._con._con.open_cursors == 0
    db.commit()
    session = db._con._con.session
    db.close()
    assert session == [
        'doit1', 'commit', 'dont1', 'rollback',
        'doit2', 'commit', 'rollback']


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_maxconnections(dbapi, threadsafety):
    """Check that the maximum number of connections is enforced."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 1, 2, 2, 3)
    assert hasattr(pool, '_maxconnections')
    assert pool._maxconnections == 3
    assert hasattr(pool, '_connections')
    assert pool._connections == 0
    assert len(pool._idle_cache) == 1
    # three dedicated connections exhaust the pool
    cache = []
    for _i in range(3):
        cache.append(pool.connection(False))
    assert pool._connections == 3
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 0
    with pytest.raises(TooManyConnectionsError):
        pool.connection(False)
    with pytest.raises(TooManyConnectionsError):
        pool.connection()
    # releasing them frees the pool again (only maxcached=2 are kept)
    cache = []
    assert pool._connections == 0
    assert len(pool._idle_cache) == 2
    if shareable:
        assert len(pool._shared_cache) == 0
    # three shareable connections only need maxshared=2 connections,
    # which leaves room for one more dedicated connection
    for _i in range(3):
        cache.append(pool.connection())
    assert len(pool._idle_cache) == 0
    if shareable:
        assert pool._connections == 2
        assert len(pool._shared_cache) == 2
        cache.append(pool.connection(False))
        assert pool._connections == 3
        assert len(pool._shared_cache) == 2
    else:
        assert pool._connections == 3
    with pytest.raises(TooManyConnectionsError):
        pool.connection(False)
    # further shareable requests are always served by sharing
    if shareable:
        cache.append(pool.connection(True))
        assert pool._connections == 3
    else:
        with pytest.raises(TooManyConnectionsError):
            pool.connection()
    del cache
    assert pool._connections == 0
    assert len(pool._idle_cache) == 2


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_maxconnections_one(dbapi, threadsafety):
    """Check that a pool can be limited to a single connection."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 0, 1, 1, 1)
    assert pool._maxconnections == 1
    assert pool._connections == 0
    assert len(pool._idle_cache) == 0
    # while the one connection is used exclusively, nothing else is served
    db = pool.connection(False)
    assert pool._connections == 1
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 0
    with pytest.raises(TooManyConnectionsError):
        pool.connection(False)
    with pytest.raises(TooManyConnectionsError):
        pool.connection()
    assert db
    del db
    assert pool._connections == 0
    assert len(pool._idle_cache) == 1
    # when it is used as a shared connection, it can serve any number
    # of shareable requests, but still no dedicated one
    cache = [pool.connection()]
    assert pool._connections == 1
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 1
        cache.append(pool.connection())
        assert pool._connections == 1
        assert len(pool._shared_cache) == 1
        assert pool._shared_cache[0].shared == 2
    else:
        with pytest.raises(TooManyConnectionsError):
            pool.connection()
    with pytest.raises(TooManyConnectionsError):
        pool.connection(False)
    if shareable:
        cache.append(pool.connection(True))
        assert pool._connections == 1
        assert len(pool._shared_cache) == 1
        assert pool._shared_cache[0].shared == 3
    else:
        with pytest.raises(TooManyConnectionsError):
            pool.connection(True)
    del cache
    assert pool._connections == 0
    assert len(pool._idle_cache) == 1
    if shareable:
        assert len(pool._shared_cache) == 0
    # afterwards the connection can be used exclusively again
    db = pool.connection(False)
    assert pool._connections == 1
    assert len(pool._idle_cache) == 0
    assert db
    del db
    assert pool._connections == 0
    assert len(pool._idle_cache) == 1


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_maxconnections_raised_to_maxcached(dbapi, threadsafety):
    """Check that maxconnections is raised to the value of maxcached."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 1, 2, 2, 1)
    assert pool._maxconnections == 2
    assert pool._connections == 0
    assert len(pool._idle_cache) == 1
    cache = [pool.connection(False)]
    assert pool._connections == 1
    assert len(pool._idle_cache) == 0
    cache.append(pool.connection(False))
    assert pool._connections == 2
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 0
    with pytest.raises(TooManyConnectionsError):
        pool.connection(False)
    with pytest.raises(TooManyConnectionsError):
        pool.connection()


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_maxconnections_raised_to_mincached(dbapi, threadsafety):
    """Check that maxconnections is raised to the value of mincached."""
    dbapi.threadsafety = threadsafety
    pool = PooledDB(dbapi, 4, 3, 2, 1, False)
    assert pool._maxconnections == 4
    assert pool._connections == 0
    assert len(pool._idle_cache) == 4
    cache = []
    for _i in range(4):
        cache.append(pool.connection(False))
    assert pool._connections == 4
    assert len(pool._idle_cache) == 0
    with pytest.raises(TooManyConnectionsError):
        pool.connection(False)
    with pytest.raises(TooManyConnectionsError):
        pool.connection()


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_maxconnections_above_maxshared(dbapi, threadsafety):
    """Check that shared connections leave room for dedicated ones."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 1, 2, 3, 4, False)
    assert pool._maxconnections == 4
    assert pool._connections == 0
    assert len(pool._idle_cache) == 1
    # four shareable requests only need maxshared=3 connections
    cache = []
    for _i in range(4):
        cache.append(pool.connection())
    assert len(pool._idle_cache) == 0
    if shareable:
        assert pool._connections == 3
        assert len(pool._shared_cache) == 3
        cache.append(pool.connection())
        assert pool._connections == 3
        # so the fourth connection is still available as a dedicated one
        cache.append(pool.connection(False))
        assert pool._connections == 4
    else:
        assert pool._connections == 4
        with pytest.raises(TooManyConnectionsError):
            pool.connection()
    with pytest.raises(TooManyConnectionsError):
        pool.connection(False)


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_maxconnections_equal_to_maxshared(dbapi, threadsafety):
    """Check that all connections may be shared when maxshared allows it."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 0, 0, 3, 3, False)
    assert pool._maxconnections == 3
    assert pool._connections == 0
    # used exclusively, the three connections are exhausted right away
    cache = []
    for _i in range(3):
        cache.append(pool.connection(False))
    assert pool._connections == 3
    with pytest.raises(TooManyConnectionsError):
        pool.connection(False)
    with pytest.raises(TooManyConnectionsError):
        pool.connection(True)
    # used as shared connections, they can serve any number of requests
    cache = []
    assert pool._connections == 0
    for _i in range(3):
        cache.append(pool.connection())
    assert pool._connections == 3
    if shareable:
        for _i in range(3):
            cache.append(pool.connection())
        assert pool._connections == 3
    else:
        with pytest.raises(TooManyConnectionsError):
            pool.connection()
    with pytest.raises(TooManyConnectionsError):
        pool.connection(False)


@pytest.mark.parametrize("threadsafety", [1, 2])
@pytest.mark.parametrize("maxconnections", [0, None])
def test_maxconnections_unlimited(dbapi, threadsafety, maxconnections):
    """Check that the number of connections is unlimited by default."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 0, 0, 3, maxconnections)
    assert pool._maxconnections == 0
    assert pool._connections == 0
    cache = []
    for _i in range(10):
        cache.append(pool.connection(False))
        cache.append(pool.connection())
    assert cache
    if shareable:
        # the ten shareable requests need only maxshared=3 connections
        assert pool._connections == 13
        assert len(pool._shared_cache) == 3
    else:
        assert pool._connections == 20


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_maxconnections_blocking(dbapi, threadsafety):
    """Check that a thread waits for a connection when blocking is set."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 1, 1, 1, 1, True)
    assert pool._maxconnections == 1
    assert pool._connections == 0
    assert len(pool._idle_cache) == 1
    db = pool.connection(False)
    assert pool._connections == 1
    assert len(pool._idle_cache) == 0

    def connection():
        db = pool.connection()
        cursor = db.cursor()
        cursor.execute('set thread')
        cursor.close()
        db.close()

    # the thread cannot get a connection and blocks instead of failing
    thread = Thread(target=connection)
    thread.start()
    thread.join(0.1)
    assert thread.is_alive()
    assert pool._connections == 1
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 0
    session = db._con._con.session
    assert session == ['rollback']
    # releasing the connection unblocks the thread, which then runs to the end
    del db
    thread.join(0.1)
    assert not thread.is_alive()
    assert pool._connections == 0
    assert len(pool._idle_cache) == 1
    if shareable:
        assert len(pool._shared_cache) == 0
    db = pool.connection(False)
    assert pool._connections == 1
    assert len(pool._idle_cache) == 0
    assert session == ['rollback', 'rollback', 'thread', 'rollback']
    assert db
    del db


@pytest.mark.parametrize("threadsafety", [1, 2])
@pytest.mark.parametrize("maxusage", [0, 3, 7])
def test_maxusage(dbapi, threadsafety, maxusage):
    """Check that connections are reset when used too often."""
    dbapi.threadsafety = threadsafety
    pool = PooledDB(dbapi, 0, 0, 0, 1, False, maxusage)
    assert pool._maxusage == maxusage
    assert len(pool._idle_cache) == 0
    db = pool.connection(False)
    assert db._con._maxusage == maxusage
    assert len(pool._idle_cache) == 0
    assert db._con._con.open_cursors == 0
    assert db._usage == 0
    assert db._con._con.num_uses == 0
    assert db._con._con.num_queries == 0
    for i in range(20):
        cursor = db.cursor()
        assert db._con._con.open_cursors == 1
        cursor.execute(f'select test{i}')
        r = cursor.fetchone()
        assert r == f'test{i}'
        cursor.close()
        assert db._con._con.open_cursors == 0
        j = i % maxusage + 1 if maxusage else i + 1
        assert db._usage == j
        assert db._con._con.num_uses == j
        assert db._con._con.num_queries == j
    db.cursor().callproc('test')
    assert db._con._con.open_cursors == 0
    assert db._usage == j + 1
    assert db._con._con.num_uses == j + 1
    assert db._con._con.num_queries == j


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_setsession(dbapi, threadsafety):
    """Check that the session is prepared after every reopening."""
    dbapi.threadsafety = threadsafety
    setsession = ('set time zone', 'set datestyle')
    pool = PooledDB(dbapi, 0, 0, 0, 1, False, None, setsession)
    assert pool._setsession == setsession
    db = pool.connection(False)
    assert db._setsession_sql == setsession
    assert db._con._con.session == ['time zone', 'datestyle']
    db.cursor().execute('select test')
    db.cursor().execute('set test1')
    assert db._usage == 2
    assert db._con._con.num_uses == 4
    assert db._con._con.num_queries == 1
    assert db._con._con.session == ['time zone', 'datestyle', 'test1']
    db.close()
    db = pool.connection(False)
    assert db._setsession_sql == setsession
    assert db._con._con.session == \
        ['time zone', 'datestyle', 'test1', 'rollback']
    db._con._con.close()
    db.cursor().execute('select test')
    db.cursor().execute('set test2')
    assert db._con._con.session == ['time zone', 'datestyle', 'test2']


@pytest.mark.parametrize("threadsafety", [1, 2])
@pytest.mark.parametrize("pool_args", [
    (2,),  # two idle connections are cached up front
    (0, 0, 2),  # two connections may be shared
])
def test_one_thread_two_connections(dbapi, threadsafety, pool_args):
    """Check that one thread can use two connections at once."""
    dbapi.threadsafety = threadsafety
    pool = PooledDB(dbapi, *pool_args)
    # both connections are distinct and count their queries separately
    db1 = pool.connection()
    for _i in range(5):
        db1.cursor().execute('select test')
    db2 = pool.connection()
    assert db1 != db2
    assert db1._con != db2._con
    for _i in range(7):
        db2.cursor().execute('select test')
    assert db1._con._con.num_queries == 5
    assert db2._con._con.num_queries == 7
    # releasing the first one and taking it again keeps them distinct
    del db1
    db1 = pool.connection()
    assert db1 != db2
    assert db1._con != db2._con
    for _i in range(3):
        db1.cursor().execute('select test')
    assert db1._con._con.num_queries == 8
    db2.cursor().execute('select test')
    assert db2._con._con.num_queries == 8


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_one_thread_two_shared_connections(dbapi, threadsafety):
    """Check that one thread can use the same connection twice."""
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 0, 0, 1)
    # only one connection may be shared, so both requests get the same one
    db1 = pool.connection()
    db2 = pool.connection()
    assert db1 != db2
    if shareable:
        assert db1._con == db2._con
    else:
        assert db1._con != db2._con
    # but a dedicated connection is always a separate one
    del db1
    db1 = pool.connection(False)
    assert db1 != db2
    assert db1._con != db2._con


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_three_threads_two_connections(dbapi, threadsafety):
    """Check that a third thread must wait for a free connection."""
    dbapi.threadsafety = threadsafety
    pool = PooledDB(dbapi, 2, 2, 0, 2, True)
    queue = Queue(3)

    def connection():
        queue.put(pool.connection(), timeout=1)

    for _i in range(3):
        Thread(target=connection).start()
    db1 = queue.get(timeout=1)
    db2 = queue.get(timeout=1)
    assert db1 != db2
    db1_con = db1._con
    db2_con = db2._con
    assert db1_con != db2_con
    with pytest.raises(Empty):
        queue.get(timeout=0.1)
    del db1
    db1 = queue.get(timeout=1)
    assert db1 != db2
    assert db1._con != db2._con
    assert db1._con == db1_con
    pool = PooledDB(dbapi, 2, 2, 1, 2, True)
    db1 = pool.connection(False)
    db2 = pool.connection(False)
    assert db1 != db2
    db1_con = db1._con
    db2_con = db2._con
    assert db1_con != db2_con
    Thread(target=connection).start()
    with pytest.raises(Empty):
        queue.get(timeout=0.1)
    del db1
    db1 = queue.get(timeout=1)
    assert db1 != db2
    assert db1._con != db2._con
    assert db1._con == db1_con


def test_ping_check_never_dedicated(dbapi, ping_con_cls):
    """Check that dedicated connections are not pinged when ping is 0."""
    pool = PooledDB(dbapi, 1, 1, 0, 0, False, None, None, True, None, 0)
    db = pool.connection()
    assert db._con._con.valid
    assert ping_con_cls.num_pings == 0
    # the broken connection is returned to the pool and handed out again
    # without being pinged, so the breakage goes unnoticed
    db._con.close()
    db.close()
    db = pool.connection()
    assert not db._con._con.valid
    assert ping_con_cls.num_pings == 0


def test_ping_check_never_shared(dbapi, ping_con_cls):
    """Check that shared connections are not pinged when ping is 0."""
    pool = PooledDB(dbapi, 1, 1, 1, 0, False, None, None, True, None, 0)
    db = pool.connection()
    assert db._con._con.valid
    assert ping_con_cls.num_pings == 0
    db._con.close()
    db = pool.connection()
    assert not db._con._con.valid
    assert ping_con_cls.num_pings == 0


def test_ping_check_when_fetched_dedicated(dbapi, ping_con_cls):
    """Check that dedicated connections are pinged when ping is 1."""
    pool = PooledDB(dbapi, 1, 1, 0, 0, False, None, None, True, None, 1)
    db = pool.connection()
    assert db._con._con.valid
    assert ping_con_cls.num_pings == 1
    # the broken connection is pinged when fetched from the pool again,
    # so it is transparently reopened
    db._con.close()
    db.close()
    db = pool.connection()
    assert db._con._con.valid
    assert ping_con_cls.num_pings == 2


def test_ping_check_when_fetched_shared(dbapi, ping_con_cls):
    """Check that shared connections are pinged when ping is 1."""
    pool = PooledDB(dbapi, 1, 1, 1, 0, False, None, None, True, None, 1)
    db = pool.connection()
    assert db._con._con.valid
    assert ping_con_cls.num_pings == 1
    db._con.close()
    db = pool.connection()
    assert db._con._con.valid
    assert ping_con_cls.num_pings == 2


def test_ping_check_with_sql_when_fetched(dbapi, con_cls):
    """Check that connections can be checked with an SQL statement."""
    pool = PooledDB(
        dbapi, 1, 1, 0, 0, False, None, None, True, None, 'select 1')
    db = pool.connection()
    assert db._con._con.valid
    # the statement has been executed instead of using the ping method
    assert db._con._con.num_queries == 1
    assert con_cls.num_pings == 0
    # the broken connection is checked when fetched from the pool again,
    # so it is transparently reopened
    db._con.close()
    db.close()
    db = pool.connection()
    assert db._con._con.valid
    assert con_cls.num_pings == 0


def test_ping_check_when_cursor_created(dbapi, ping_con_cls):
    """Check that connections are pinged when ping is 2."""
    pool = PooledDB(dbapi, 1, 1, 1, 0, False, None, None, True, None, 2)
    db = pool.connection()
    assert db._con._con.valid
    assert ping_con_cls.num_pings == 0
    # fetching the broken connection does not ping it yet
    db._con.close()
    db = pool.connection()
    assert not db._con._con.valid
    assert ping_con_cls.num_pings == 0
    # but creating a cursor does, which reopens the connection
    db.cursor()
    assert db._con._con.valid
    assert ping_con_cls.num_pings == 1


def test_ping_check_when_query_executed(dbapi, ping_con_cls):
    """Check that connections are pinged when ping is 4."""
    pool = PooledDB(dbapi, 1, 1, 1, 0, False, None, None, True, None, 4)
    db = pool.connection()
    assert db._con._con.valid
    assert ping_con_cls.num_pings == 0
    # neither fetching the broken connection nor creating a cursor pings it
    db._con.close()
    db = pool.connection()
    assert not db._con._con.valid
    assert ping_con_cls.num_pings == 0
    cursor = db.cursor()
    db._con.close()
    assert not db._con._con.valid
    assert ping_con_cls.num_pings == 0
    # only executing a query does, which reopens the connection
    cursor.execute('select test')
    assert db._con._con.valid
    assert ping_con_cls.num_pings == 1


@pytest.mark.parametrize("pool_args", [
    (0, 1, 1),  # one connection that may be shared
    (1, 1, 0),  # one cached connection that is always dedicated
])
def test_failed_transaction(dbapi, pool_args):
    """Check that a failed transaction is reported and recovered from."""
    pool = PooledDB(dbapi, *pool_args)
    db = pool.connection()
    cursor = db.cursor()
    # outside of a transaction, a broken connection is silently reopened
    db._con._con.close()
    cursor.execute('select test')
    # inside a transaction, the failure must be reported instead
    db.begin()
    db._con._con.close()
    with pytest.raises(dbapi.InternalError):
        cursor.execute('select test')
    # but the connection is usable again afterwards
    cursor.execute('select test')
    # cancelling the transaction restores the silent reopening as well
    db.begin()
    db.cancel()
    db._con._con.close()
    cursor.execute('select test')


def test_shared_in_transaction(dbapi):
    """Check that a connection in a transaction is not shared."""
    pool = PooledDB(dbapi, 0, 1, 1)
    db = pool.connection()
    db.begin()
    # the only connection is in a transaction now, so it cannot be shared
    # and no other connection may be created either
    pool.connection(False)
    with pytest.raises(TooManyConnectionsError):
        pool.connection()


def test_shared_in_transaction_blocking(dbapi):
    """Check that a thread waits for a shared connection in a transaction."""
    pool = PooledDB(dbapi, 0, 0, 1, 0, True)
    db = pool.connection()
    con = db._con
    db.begin()
    # the only connection that may be shared is in a transaction now
    shared = []

    def connection():
        shared.append(pool.connection())

    thread = Thread(target=connection)
    thread.start()
    thread.join(0.1)
    # the thread cannot share that connection and blocks instead of failing
    assert thread.is_alive()
    assert not shared
    db.commit()
    # the thread is woken up when a connection is put back into the pool,
    # and then finds the connection shareable again
    pool.dedicated_connection().close()
    thread.join(0.1)
    assert not thread.is_alive()
    assert len(shared) == 1
    assert shared[0]._con is con


def test_shared_in_transaction_becoming_idle(dbapi):
    """Check that a thread waiting for a shared connection survives unshare."""
    pool = PooledDB(dbapi, 0, 0, 1, 0, True)
    db = pool.connection()
    con = db._con
    db.begin()
    # the only connection that may be shared is in a transaction now
    shared = []
    errors = []

    def connection():
        try:
            shared.append(pool.connection())
        except Exception as error:
            errors.append(error)

    thread = Thread(target=connection)
    thread.start()
    thread.join(0.1)
    # the thread cannot share that connection and blocks instead of failing
    assert thread.is_alive()
    assert not shared
    # closing the connection takes it out of the shared cache completely,
    # so the waiting thread is woken up to find an empty shared cache;
    # it must then get the connection from the idle cache instead of
    # trying to share a connection that is no longer there
    db.close()
    thread.join(0.1)
    assert not thread.is_alive()
    assert not errors
    assert len(shared) == 1
    assert shared[0]._con is con


def test_shared_in_transaction_with_two_connections(dbapi):
    """Check that sharing prefers connections without a transaction."""
    pool = PooledDB(dbapi, 0, 2, 2)
    # the first two requests use the two connections that may be shared
    db1 = pool.connection()
    db2 = pool.connection()
    assert db2._con is not db1._con
    db2.close()
    db2 = pool.connection()
    assert db2._con is not db1._con
    # the third request shares the least used one
    db = pool.connection()
    assert db._con is db1._con
    db.close()
    # when that one is in a transaction, the other one is shared instead
    db1.begin()
    db = pool.connection()
    assert db._con is db2._con
    db.close()
    # when both are in a transaction, nothing can be shared any more
    db2.begin()
    pool.connection(False)
    with pytest.raises(TooManyConnectionsError):
        pool.connection()
    # ending one of the transactions makes that connection shareable again
    db1.rollback()
    db = pool.connection()
    assert db._con is db1._con


def test_reset_transaction(dbapi):
    """Check how connections are reset when returned to the pool."""
    pool = PooledDB(dbapi, 1, 1, 0)
    db = pool.connection()
    db.begin()
    con = db._con
    assert con._transaction
    assert con._con.session == ['rollback']
    db.close()
    assert pool.connection()._con is con
    assert not con._transaction
    assert con._con.session == ['rollback'] * 3
    pool = PooledDB(dbapi, 1, 1, 0, reset=False)
    db = pool.connection()
    db.begin()
    con = db._con
    assert con._transaction
    assert con._con.session == []
    db.close()
    assert pool.connection()._con is con
    assert not con._transaction
    assert con._con.session == ['rollback']


def test_context_manager(dbapi):
    """Check that connection and cursor can be used as context managers."""
    pool = PooledDB(dbapi, 1, 1, 1)
    con = pool._idle_cache[0]._con
    with pool.connection() as db:
        assert hasattr(db, '_shared_con')
        assert not pool._idle_cache
        assert con.valid
        with db.cursor() as cursor:
            assert con.open_cursors == 1
            cursor.execute('select test')
            r = cursor.fetchone()
        assert con.open_cursors == 0
        assert r == 'test'
        assert con.num_queries == 1
    assert pool._idle_cache
    with pool.dedicated_connection() as db:
        assert not hasattr(db, '_shared_con')
        assert not pool._idle_cache
        with db.cursor() as cursor:
            assert con.open_cursors == 1
            cursor.execute('select test')
            r = cursor.fetchone()
        assert con.open_cursors == 0
        assert r == 'test'
        assert con.num_queries == 2
    assert pool._idle_cache


def test_shared_db_connection_create(dbapi):
    """Check that a shared connection starts with one share."""
    db_con = dbapi.connect()
    con = SharedDBConnection(db_con)
    assert con.con == db_con
    assert con.shared == 1


def test_shared_db_connection_share_and_unshare(dbapi):
    """Check that the number of shares is counted correctly."""
    con = SharedDBConnection(dbapi.connect())
    assert con.shared == 1
    con.share()
    assert con.shared == 2
    con.share()
    assert con.shared == 3
    con.unshare()
    assert con.shared == 2
    con.unshare()
    assert con.shared == 1


def test_shared_db_connection_compare(dbapi):
    """Check that shared connections are ordered by transaction and shares."""
    con1 = SharedDBConnection(dbapi.connect())
    con1.con._transaction = False
    con2 = SharedDBConnection(dbapi.connect())
    con2.con._transaction = False
    # connections with the same number of shares are ranked equally
    assert not con1 < con2
    assert not con2 < con1
    # the connection with fewer shares is preferred
    con2.share()
    assert con1 < con2
    assert not con2 < con1
    assert con1 <= con2
    assert not con1 >= con2
    # but connections in a transaction always come last
    con1.con._transaction = True
    assert not con1 < con2
    assert con2 < con1
    assert con1 > con2
    assert not con1 <= con2


def test_shared_db_connection_equality(dbapi):
    """Check that shared connections are only equal to themselves."""
    con1 = SharedDBConnection(dbapi.connect())
    con1.con._transaction = False
    con2 = SharedDBConnection(dbapi.connect())
    con2.con._transaction = False
    same_as_con1 = con1
    # the ordering only serves to pick the least shared connection,
    # it does not make equally ranked connections interchangeable
    assert con1 == same_as_con1
    assert con1 != con2
    # equal connections must therefore also have equal hash values
    # (this used to be violated, since the equality was based on the
    # values while the hash value was based on the identity)
    assert hash(con1) == hash(same_as_con1)
    assert len({con1, con2, same_as_con1}) == 2
    # and removing one connection from a list of connections
    # must not remove another connection that is ranked the same
    cache = [con1, con2]
    cache.remove(con2)
    assert len(cache) == 1
    assert cache[0] is con1


def test_shared_db_connection_hash(dbapi):
    """Check that shared connections stay hashable."""
    # defining __eq__ would otherwise make the class unhashable
    con = SharedDBConnection(dbapi.connect())
    hashed = hash(con)
    assert hash(con) == hashed
    # the hash is based on the identity, so it does not change
    # when the number of shares of the connection changes
    con.share()
    assert hash(con) == hashed
    con.unshare()
    assert hash(con) == hashed


def timeout_is_not_fatal(error):
    """Treat a deliberate server side timeout as not fatal."""
    return not error.args or error.args[0] != 3024


def test_isfatal_default(dbapi):
    """Check that no error check is configured by default."""
    pool = PooledDB(dbapi, 1)
    assert pool._isfatal is None
    db = pool.connection()
    assert db._con._isfatal is None


def test_isfatal(dbapi):
    """Check that isfatal is passed on and can veto the failover."""
    pool = PooledDB(dbapi, 1, isfatal=timeout_is_not_fatal)
    assert pool._isfatal is timeout_is_not_fatal
    db = pool.connection()
    assert db._con._isfatal is timeout_is_not_fatal
    dbapi.Connection.num_timeouts = 0
    cursor = db.cursor()
    with pytest.raises(dbapi.OperationalError):
        cursor.execute('timeout')
    assert dbapi.Connection.num_timeouts == 1
    # the failover mechanism still applies to other failures
    db._con._con.close()
    cursor.execute('select test')
    assert cursor.fetchone() == 'test'


def test_no_failover(dbapi):
    """Check that no_failover() suspends the failover mechanism."""
    pool = PooledDB(dbapi, 1)
    dbapi.Connection.num_timeouts = 0
    with pool.connection() as db, db.cursor() as cursor:
        with cursor.no_failover(), pytest.raises(dbapi.OperationalError):
            cursor.execute('timeout')
        assert dbapi.Connection.num_timeouts == 1
        cursor.execute('select test')  # connection is still usable
        assert cursor.fetchone() == 'test'


def test_dbapi_connection(dbapi):
    """Check that the underlying DB-API 2 objects are accessible."""
    pool = PooledDB(dbapi, 1)
    db = pool.connection()
    con = db.dbapi_connection
    assert isinstance(con, dbapi.Connection)
    assert con is db._con._con
    cursor = db.cursor()
    assert cursor.dbapi_cursor is cursor._cursor
