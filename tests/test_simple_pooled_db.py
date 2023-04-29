"""Test the SimplePooledDB module.

Note:
We don't test performance here, so the test does not predicate
whether SimplePooledDB actually will help in improving performance or not.
We also do not test any real world DB-API 2 module, we just
mock the basic connection functionality of an arbitrary module.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke
"""

from queue import Empty, Queue
from threading import Thread

import pytest

from dbutils import simple_pooled_db

from . import mock_db as dbapi


def my_db_pool(threadsafety, max_connections):
    """Get simple PooledDB connection."""
    dbapi_threadsafety = dbapi.threadsafety
    dbapi.threadsafety = threadsafety
    try:
        return simple_pooled_db.PooledDB(
            dbapi, max_connections,
            'SimplePooledDBTestDB', 'SimplePooledDBTestUser')
    finally:
        dbapi.threadsafety = dbapi_threadsafety


def test_version():
    from dbutils import __version__
    assert simple_pooled_db.__version__ == __version__
    assert simple_pooled_db.PooledDB.version == __version__


@pytest.mark.parametrize("threadsafety", [None, -1, 0, 4])
def test_no_threadsafety(threadsafety):
    with pytest.raises(simple_pooled_db.NotSupportedError):
        my_db_pool(threadsafety, 1)


@pytest.mark.parametrize("threadsafety", [1, 2, 3])
def test_create_connection(threadsafety):
    dbpool = my_db_pool(threadsafety, 1)
    db = dbpool.connection()
    assert hasattr(db, 'cursor')
    assert hasattr(db, 'open_cursors')
    assert db.open_cursors == 0
    assert hasattr(db, 'database')
    assert db.database == 'SimplePooledDBTestDB'
    assert hasattr(db, 'user')
    assert db.user == 'SimplePooledDBTestUser'
    cursor = db.cursor()
    assert cursor is not None
    assert db.open_cursors == 1
    del cursor


@pytest.mark.parametrize("threadsafety", [1, 2, 3])
def test_close_connection(threadsafety):
    db_pool = my_db_pool(threadsafety, 1)
    db = db_pool.connection()
    assert db.open_cursors == 0
    cursor1 = db.cursor()
    assert cursor1 is not None
    assert db.open_cursors == 1
    db.close()
    assert not hasattr(db, 'open_cursors')
    db = db_pool.connection()
    assert hasattr(db, 'database')
    assert db.database == 'SimplePooledDBTestDB'
    assert hasattr(db, 'user')
    assert db.user == 'SimplePooledDBTestUser'
    assert db.open_cursors == 1
    cursor2 = db.cursor()
    assert cursor2 is not None
    assert db.open_cursors == 2
    del cursor2
    del cursor1


@pytest.mark.parametrize("threadsafety", [1, 2, 3])
def test_two_connections(threadsafety):
    db_pool = my_db_pool(threadsafety, 2)
    db1 = db_pool.connection()
    cursors1 = [db1.cursor() for _i_ in range(5)]
    db2 = db_pool.connection()
    assert db1 != db2
    cursors2 = [db2.cursor() for _i in range(7)]
    assert db1.open_cursors == 5
    assert db2.open_cursors == 7
    db1.close()
    db1 = db_pool.connection()
    assert db1 != db2
    assert hasattr(db1, 'cursor')
    for _i in range(3):
        cursors1.append(db1.cursor())
    assert db1.open_cursors == 8
    cursors2.append(db2.cursor())
    assert db2.open_cursors == 8
    del cursors2
    del cursors1


def test_threadsafety_1():
    db_pool = my_db_pool(1, 2)
    queue = Queue(3)

    def connection():
        queue.put(db_pool.connection())

    threads = [Thread(target=connection).start() for _i in range(3)]
    assert len(threads) == 3
    db1 = queue.get(timeout=1)
    db2 = queue.get(timeout=1)
    assert db1 != db2
    assert db1._con != db2._con
    with pytest.raises(Empty):
        queue.get(timeout=0.1)
    db2.close()
    db3 = queue.get(timeout=1)
    assert db1 != db3
    assert db1._con != db3._con


@pytest.mark.parametrize("threadsafety", [2, 3])
def test_threadsafety_2(threadsafety):
    dbpool = my_db_pool(threadsafety, 2)
    db1 = dbpool.connection()
    db2 = dbpool.connection()
    cursors = [dbpool.connection().cursor() for _i in range(100)]
    assert db1.open_cursors == 50
    assert db2.open_cursors == 50
    assert cursors
    del cursors
