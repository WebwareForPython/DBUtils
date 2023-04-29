"""Test the SimplePooledPg module.

Note:
We don't test performance here, so the test does not predicate
whether SimplePooledPg actually will help in improving performance or not.


Copyright and credit info:

* This test was contributed by Christoph Zwerschke
"""

from queue import Empty, Queue
from threading import Thread

import pg  # noqa: F401
import pytest

from dbutils import simple_pooled_pg


def my_db_pool(max_connections):
    """Get simple PooledPg connection."""
    return simple_pooled_pg.PooledPg(
        max_connections, 'SimplePooledPgTestDB', 'SimplePooledPgTestUser')


def test_version():
    from dbutils import __version__
    assert simple_pooled_pg.__version__ == __version__
    assert simple_pooled_pg.PooledPg.version == __version__


def test_create_connection():
    db_pool = my_db_pool(1)
    db = db_pool.connection()
    assert hasattr(db, 'query')
    assert hasattr(db, 'num_queries')
    assert db.num_queries == 0
    assert hasattr(db, 'dbname')
    assert db.dbname == 'SimplePooledPgTestDB'
    assert hasattr(db, 'user')
    assert db.user == 'SimplePooledPgTestUser'
    db.query('select 1')
    assert db.num_queries == 1


def test_close_connection():
    db_pool = my_db_pool(1)
    db = db_pool.connection()
    assert db.num_queries == 0
    db.query('select 1')
    assert db.num_queries == 1
    db.close()
    assert not hasattr(db, 'num_queries')
    db = db_pool.connection()
    assert hasattr(db, 'dbname')
    assert db.dbname == 'SimplePooledPgTestDB'
    assert hasattr(db, 'user')
    assert db.user == 'SimplePooledPgTestUser'
    assert db.num_queries == 1
    db.query('select 1')
    assert db.num_queries == 2


def test_two_connections():
    db_pool = my_db_pool(2)
    db1 = db_pool.connection()
    for _i in range(5):
        db1.query('select 1')
    db2 = db_pool.connection()
    assert db1 != db2
    assert db1._con != db2._con
    for _i in range(7):
        db2.query('select 1')
    assert db1.num_queries == 5
    assert db2.num_queries == 7
    db1.close()
    db1 = db_pool.connection()
    assert db1 != db2
    assert db1._con != db2._con
    assert hasattr(db1, 'query')
    for _i in range(3):
        db1.query('select 1')
    assert db1.num_queries == 8
    db2.query('select 1')
    assert db2.num_queries == 8


def test_threads():
    db_pool = my_db_pool(2)
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
