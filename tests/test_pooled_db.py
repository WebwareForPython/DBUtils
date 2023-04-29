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

from .mock_db import dbapi  # noqa: F401


def test_version():
    from dbutils import __version__, pooled_db
    assert pooled_db.__version__ == __version__
    assert PooledDB.version == __version__


@pytest.mark.parametrize("threadsafety", [None, 0])
def test_no_threadsafety(dbapi, threadsafety):  # noqa: F811
    dbapi.threadsafety = threadsafety
    with pytest.raises(NotSupportedError):
        PooledDB(dbapi)


@pytest.mark.parametrize("threadsafety", [1, 2, 3])
def test_threadsafety(dbapi, threadsafety):  # noqa: F811
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
def test_create_connection(dbapi, threadsafety):  # noqa: F811, PLR0915
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(
        dbapi, 1, 1, 1, 0, False, None, None, True, None, None,
        'PooledDBTestDB', user='PooledDBTestUser')
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
    con = pool._idle_cache[0]
    assert isinstance(con, SteadyDBConnection)
    assert hasattr(con, '_maxusage')
    assert con._maxusage == 0
    assert hasattr(con, '_setsession_sql')
    assert con._setsession_sql is None
    db = pool.connection()
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 1
    assert hasattr(db, '_con')
    assert db._con == con
    assert hasattr(db, 'cursor')
    assert hasattr(db, '_usage')
    assert db._usage == 0
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
    cursor = db.cursor()
    assert db_con.open_cursors == 1
    cursor.execute('select test')
    r = cursor.fetchone()
    cursor.close()
    assert db_con.open_cursors == 0
    assert r == 'test'
    assert db_con.num_queries == 1
    assert db._usage == 1
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
    pool = PooledDB(dbapi, 1, 1, 1)
    assert len(pool._idle_cache) == 1
    if shareable:
        assert len(pool._shared_cache) == 0
    db = pool.connection()
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 1
    db.close()
    assert len(pool._idle_cache) == 1
    if shareable:
        assert len(pool._shared_cache) == 0
    db = pool.connection(True)
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 1
    db.close()
    assert len(pool._idle_cache) == 1
    if shareable:
        assert len(pool._shared_cache) == 0
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
    pool = PooledDB(dbapi, 0, 0, 0, 0, False, 3, ('set datestyle',))
    assert pool._maxusage == 3
    assert pool._setsession == ('set datestyle',)
    con = pool.connection()._con
    assert con._maxusage == 3
    assert con._setsession_sql == ('set datestyle',)


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_close_connection(dbapi, threadsafety):  # noqa: F811
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(
        dbapi, 0, 1, 1, 0, False, None, None, True, None, None,
        'PooledDBTestDB', user='PooledDBTestUser')
    assert hasattr(pool, '_idle_cache')
    assert len(pool._idle_cache) == 0
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
    db.close()
    if shareable:
        assert shared_con.shared == 0
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
    db = pool.connection(False)
    assert db._con == con
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 0
    db.close()
    assert len(pool._idle_cache) == 1
    if shareable:
        assert len(pool._shared_cache) == 0


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_close_all(dbapi, threadsafety):  # noqa: F811
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 10)
    assert len(pool._idle_cache) == 10
    pool.close()
    assert len(pool._idle_cache) == 0
    pool = PooledDB(dbapi, 10)
    closed = ['no']

    def close(what=closed):
        what[0] = 'yes'

    pool._idle_cache[7]._con.close = close
    assert closed == ['no']
    del pool
    assert closed == ['yes']
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
    else:
        assert len(pool._idle_cache) == 5
    pool.close()
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 0
    pool = PooledDB(dbapi, 10, 10, 5)
    closed = []

    def close_idle(what=closed):
        what.append('idle')

    def close_shared(what=closed):
        what.append('shared')

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
def test_shareable_connection(dbapi, threadsafety):  # noqa: F811
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 0, 1, 2)
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 0
    db1 = pool.connection()
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 1
    db2 = pool.connection()
    assert db1._con != db2._con
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 2
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
    db5.close()
    assert len(pool._idle_cache) == 1
    db5 = pool.connection()
    if shareable:
        assert len(pool._idle_cache) == 1
        assert len(pool._shared_cache) == 2
        assert db5._shared_con.shared == 3
    else:
        assert len(pool._idle_cache) == 0
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
    del db3
    if shareable:
        assert len(pool._idle_cache) == 0
        assert len(pool._shared_cache) == 1
    else:
        assert len(pool._idle_cache) == 1
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
def test_min_max_cached(dbapi, threadsafety):  # noqa: F811
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 3)
    assert len(pool._idle_cache) == 3
    cache = [pool.connection() for _i in range(3)]
    assert len(pool._idle_cache) == 0
    assert cache
    del cache
    assert len(pool._idle_cache) == 3
    cache = [pool.connection() for _i in range(6)]
    assert len(pool._idle_cache) == 0
    assert cache
    del cache
    assert len(pool._idle_cache) == 6
    pool = PooledDB(dbapi, 0, 3)
    assert len(pool._idle_cache) == 0
    cache = [pool.connection() for _i in range(3)]
    assert len(pool._idle_cache) == 0
    assert cache
    del cache
    assert len(pool._idle_cache) == 3
    cache = [pool.connection() for _i in range(6)]
    assert len(pool._idle_cache) == 0
    assert cache
    del cache
    assert len(pool._idle_cache) == 3
    pool = PooledDB(dbapi, 3, 3)
    assert len(pool._idle_cache) == 3
    cache = [pool.connection() for _i in range(3)]
    assert len(pool._idle_cache) == 0
    assert cache
    del cache
    assert len(pool._idle_cache) == 3
    cache = [pool.connection() for _i in range(6)]
    assert len(pool._idle_cache) == 0
    assert cache
    del cache
    assert len(pool._idle_cache) == 3
    pool = PooledDB(dbapi, 3, 2)
    assert len(pool._idle_cache) == 3
    cache = [pool.connection() for _i in range(4)]
    assert len(pool._idle_cache) == 0
    assert cache
    del cache
    assert len(pool._idle_cache) == 3
    pool = PooledDB(dbapi, 2, 5)
    assert len(pool._idle_cache) == 2
    cache = [pool.connection() for _i in range(10)]
    assert len(pool._idle_cache) == 0
    assert cache
    del cache
    assert len(pool._idle_cache) == 5
    pool = PooledDB(dbapi, 1, 2, 3)
    assert len(pool._idle_cache) == 1
    cache = [pool.connection(False) for _i in range(4)]
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 0
    assert cache
    del cache
    assert len(pool._idle_cache) == 2
    cache = [pool.connection() for _i in range(10)]
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 3
    assert cache
    del cache
    assert len(pool._idle_cache) == 2
    if shareable:
        assert len(pool._shared_cache) == 0
    pool = PooledDB(dbapi, 1, 3, 2)
    assert len(pool._idle_cache) == 1
    cache = [pool.connection(False) for _i in range(4)]
    assert len(pool._idle_cache) == 0
    if shareable:
        assert len(pool._shared_cache) == 0
    assert cache
    del cache
    assert len(pool._idle_cache) == 3
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
def test_max_shared(dbapi, threadsafety):  # noqa: F811
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


def test_sort_shared(dbapi):  # noqa: F811
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
def test_equally_shared(dbapi, threadsafety):  # noqa: F811
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
def test_many_shared(dbapi, threadsafety):  # noqa: F811
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 0, 0, 5)
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
        cache[3] = cache[8] = cache[33] = None
        cache[12] = cache[17] = cache[34] = None
        assert len(pool._shared_cache) == 5
        assert pool._shared_cache[0].shared == 7
        assert pool._shared_cache[1].shared == 7
        assert pool._shared_cache[2].shared == 5
        assert pool._shared_cache[3].shared == 4
        assert pool._shared_cache[4].shared == 6
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
def test_rollback(dbapi, threadsafety):  # noqa: F811
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
def test_maxconnections(dbapi, threadsafety):  # noqa: F811, PLR0915
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 1, 2, 2, 3)
    assert hasattr(pool, '_maxconnections')
    assert pool._maxconnections == 3
    assert hasattr(pool, '_connections')
    assert pool._connections == 0
    assert len(pool._idle_cache) == 1
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
    cache = []
    assert pool._connections == 0
    assert len(pool._idle_cache) == 2
    if shareable:
        assert len(pool._shared_cache) == 0
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
    if shareable:
        cache.append(pool.connection(True))
        assert pool._connections == 3
    else:
        with pytest.raises(TooManyConnectionsError):
            pool.connection()
    del cache
    assert pool._connections == 0
    assert len(pool._idle_cache) == 2
    pool = PooledDB(dbapi, 0, 1, 1, 1)
    assert pool._maxconnections == 1
    assert pool._connections == 0
    assert len(pool._idle_cache) == 0
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
    db = pool.connection(False)
    assert pool._connections == 1
    assert len(pool._idle_cache) == 0
    assert db
    del db
    assert pool._connections == 0
    assert len(pool._idle_cache) == 1
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
    pool = PooledDB(dbapi, 1, 2, 3, 4, False)
    assert pool._maxconnections == 4
    assert pool._connections == 0
    assert len(pool._idle_cache) == 1
    for _i in range(4):
        cache.append(pool.connection())
    assert len(pool._idle_cache) == 0
    if shareable:
        assert pool._connections == 3
        assert len(pool._shared_cache) == 3
        cache.append(pool.connection())
        assert pool._connections == 3
        cache.append(pool.connection(False))
        assert pool._connections == 4
    else:
        assert pool._connections == 4
        with pytest.raises(TooManyConnectionsError):
            pool.connection()
    with pytest.raises(TooManyConnectionsError):
        pool.connection(False)
    pool = PooledDB(dbapi, 0, 0, 3, 3, False)
    assert pool._maxconnections == 3
    assert pool._connections == 0
    cache = []
    for _i in range(3):
        cache.append(pool.connection(False))
    assert pool._connections == 3
    with pytest.raises(TooManyConnectionsError):
        pool.connection(False)
    with pytest.raises(TooManyConnectionsError):
        pool.connection(True)
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
    pool = PooledDB(dbapi, 0, 0, 3)
    assert pool._maxconnections == 0
    assert pool._connections == 0
    cache = []
    for _i in range(10):
        cache.append(pool.connection(False))
        cache.append(pool.connection())
    if shareable:
        assert pool._connections == 13
        assert len(pool._shared_cache) == 3
    else:
        assert pool._connections == 20
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
def test_maxusage(dbapi, threadsafety, maxusage):  # noqa: F811
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
def test_setsession(dbapi, threadsafety):  # noqa: F811
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
def test_one_thread_two_connections(dbapi, threadsafety):  # noqa: F811
    dbapi.threadsafety = threadsafety
    shareable = threadsafety > 1
    pool = PooledDB(dbapi, 2)
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
    del db1
    db1 = pool.connection()
    assert db1 != db2
    assert db1._con != db2._con
    for _i in range(3):
        db1.cursor().execute('select test')
    assert db1._con._con.num_queries == 8
    db2.cursor().execute('select test')
    assert db2._con._con.num_queries == 8
    pool = PooledDB(dbapi, 0, 0, 2)
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
    del db1
    db1 = pool.connection()
    assert db1 != db2
    assert db1._con != db2._con
    for _i in range(3):
        db1.cursor().execute('select test')
    assert db1._con._con.num_queries == 8
    db2.cursor().execute('select test')
    assert db2._con._con.num_queries == 8
    pool = PooledDB(dbapi, 0, 0, 1)
    db1 = pool.connection()
    db2 = pool.connection()
    assert db1 != db2
    if shareable:
        assert db1._con == db2._con
    else:
        assert db1._con != db2._con
    del db1
    db1 = pool.connection(False)
    assert db1 != db2
    assert db1._con != db2._con


@pytest.mark.parametrize("threadsafety", [1, 2])
def test_three_threads_two_connections(dbapi, threadsafety):  # noqa: F811
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


def test_ping_check(dbapi):  # noqa: F811
    con_cls = dbapi.Connection
    con_cls.has_ping = True
    con_cls.num_pings = 0
    pool = PooledDB(dbapi, 1, 1, 0, 0, False, None, None, True, None, 0)
    db = pool.connection()
    assert db._con._con.valid
    assert con_cls.num_pings == 0
    db._con.close()
    db.close()
    db = pool.connection()
    assert not db._con._con.valid
    assert con_cls.num_pings == 0
    pool = PooledDB(dbapi, 1, 1, 1, 0, False, None, None, True, None, 0)
    db = pool.connection()
    assert db._con._con.valid
    assert con_cls.num_pings == 0
    db._con.close()
    db = pool.connection()
    assert not db._con._con.valid
    assert con_cls.num_pings == 0
    pool = PooledDB(dbapi, 1, 1, 0, 0, False, None, None, True, None, 1)
    db = pool.connection()
    assert db._con._con.valid
    assert con_cls.num_pings == 1
    db._con.close()
    db.close()
    db = pool.connection()
    assert db._con._con.valid
    assert con_cls.num_pings == 2
    pool = PooledDB(dbapi, 1, 1, 1, 0, False, None, None, True, None, 1)
    db = pool.connection()
    assert db._con._con.valid
    assert con_cls.num_pings == 3
    db._con.close()
    db = pool.connection()
    assert db._con._con.valid
    assert con_cls.num_pings == 4
    pool = PooledDB(dbapi, 1, 1, 1, 0, False, None, None, True, None, 2)
    db = pool.connection()
    assert db._con._con.valid
    assert con_cls.num_pings == 4
    db._con.close()
    db = pool.connection()
    assert not db._con._con.valid
    assert con_cls.num_pings == 4
    db.cursor()
    assert db._con._con.valid
    assert con_cls.num_pings == 5
    pool = PooledDB(dbapi, 1, 1, 1, 0, False, None, None, True, None, 4)
    db = pool.connection()
    assert db._con._con.valid
    assert con_cls.num_pings == 5
    db._con.close()
    db = pool.connection()
    assert not db._con._con.valid
    assert con_cls.num_pings == 5
    cursor = db.cursor()
    db._con.close()
    assert not db._con._con.valid
    assert con_cls.num_pings == 5
    cursor.execute('select test')
    assert db._con._con.valid
    assert con_cls.num_pings == 6
    con_cls.has_ping = False
    con_cls.num_pings = 0


def test_failed_transaction(dbapi):  # noqa: F811
    pool = PooledDB(dbapi, 0, 1, 1)
    db = pool.connection()
    cursor = db.cursor()
    db._con._con.close()
    cursor.execute('select test')
    db.begin()
    db._con._con.close()
    with pytest.raises(dbapi.InternalError):
        cursor.execute('select test')
    cursor.execute('select test')
    db.begin()
    db.cancel()
    db._con._con.close()
    cursor.execute('select test')
    pool = PooledDB(dbapi, 1, 1, 0)
    db = pool.connection()
    cursor = db.cursor()
    db._con._con.close()
    cursor.execute('select test')
    db.begin()
    db._con._con.close()
    with pytest.raises(dbapi.InternalError):
        cursor.execute('select test')
    cursor.execute('select test')
    db.begin()
    db.cancel()
    db._con._con.close()
    cursor.execute('select test')


def test_shared_in_transaction(dbapi):  # noqa: F811
    pool = PooledDB(dbapi, 0, 1, 1)
    db = pool.connection()
    db.begin()
    pool.connection(False)
    with pytest.raises(TooManyConnectionsError):
        pool.connection()
    pool = PooledDB(dbapi, 0, 2, 2)
    db1 = pool.connection()
    db2 = pool.connection()
    assert db2._con is not db1._con
    db2.close()
    db2 = pool.connection()
    assert db2._con is not db1._con
    db = pool.connection()
    assert db._con is db1._con
    db.close()
    db1.begin()
    db = pool.connection()
    assert db._con is db2._con
    db.close()
    db2.begin()
    pool.connection(False)
    with pytest.raises(TooManyConnectionsError):
        pool.connection()
    db1.rollback()
    db = pool.connection()
    assert db._con is db1._con


def test_reset_transaction(dbapi):  # noqa: F811
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


def test_context_manager(dbapi):  # noqa: F811
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


def test_shared_db_connection_create(dbapi):  # noqa: F811
    db_con = dbapi.connect()
    con = SharedDBConnection(db_con)
    assert con.con == db_con
    assert con.shared == 1


def test_shared_db_connection_share_and_unshare(dbapi):  # noqa: F811
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


def test_shared_db_connection_compare(dbapi):  # noqa: F811
    con1 = SharedDBConnection(dbapi.connect())
    con1.con._transaction = False
    con2 = SharedDBConnection(dbapi.connect())
    con2.con._transaction = False
    assert con1 == con2
    assert con1 <= con2
    assert con1 >= con2
    assert not con1 != con2  # noqa: SIM202
    assert not con1 < con2
    assert not con1 > con2
    con2.share()
    assert not con1 == con2  # noqa: SIM201
    assert con1 <= con2
    assert not con1 >= con2
    assert con1 != con2
    assert con1 < con2
    assert not con1 > con2
    con1.con._transaction = True
    assert not con1 == con2  # noqa: SIM201
    assert not con1 <= con2
    assert con1 >= con2
    assert con1 != con2
    assert not con1 < con2
    assert con1 > con2
