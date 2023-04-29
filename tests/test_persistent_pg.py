"""Test the PersistentPg module.

Note:
We don't test performance here, so the test does not predicate
whether PersistentPg actually will help in improving performance or not.
We also assume that the underlying SteadyPg connections are tested.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke
"""

from queue import Empty, Queue
from threading import Thread

import pg
import pytest

from dbutils.persistent_pg import PersistentPg


def test_version():
    from dbutils import __version__, persistent_pg
    assert persistent_pg.__version__ == __version__
    assert PersistentPg.version == __version__


@pytest.mark.parametrize("closeable", [False, True])
def test_close(closeable):
    persist = PersistentPg(closeable=closeable)
    db = persist.connection()
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


def test_threads():
    num_threads = 3
    persist = PersistentPg()
    query_queue, result_queue = [], []
    for _i in range(num_threads):
        query_queue.append(Queue(1))
        result_queue.append(Queue(1))

    def run_queries(idx):
        this_db = persist.connection().db
        db = None
        while True:
            try:
                q = query_queue[idx].get(timeout=1)
            except Empty:
                q = None
            if not q:
                break
            db = persist.connection()
            if db.db != this_db:
                res = 'error - not persistent'
            elif q == 'ping':
                res = 'ok - thread alive'
            elif q == 'close':
                db.db.close()
                res = 'ok - connection closed'
            else:
                res = db.query(q)
            res = f'{idx}({db._usage}): {res}'
            result_queue[idx].put(res, timeout=1)
        if db:
            db.close()

    threads = []
    for i in range(num_threads):
        thread = Thread(target=run_queries, args=(i,))
        threads.append(thread)
        thread.start()
    for i in range(num_threads):
        query_queue[i].put('ping', timeout=1)
    for i in range(num_threads):
        r = result_queue[i].get(timeout=1)
        assert r == f'{i}(0): ok - thread alive'
        assert threads[i].is_alive()
    for i in range(num_threads):
        for j in range(i + 1):
            query_queue[i].put(f'select test{j}', timeout=1)
            r = result_queue[i].get(timeout=1)
            assert r == f'{i}({j + 1}): test{j}'
    query_queue[1].put('select test4', timeout=1)
    r = result_queue[1].get(timeout=1)
    assert r == '1(3): test4'
    query_queue[1].put('close', timeout=1)
    r = result_queue[1].get(timeout=1)
    assert r == '1(3): ok - connection closed'
    for j in range(2):
        query_queue[1].put(f'select test{j}', timeout=1)
        r = result_queue[1].get(timeout=1)
        assert r == f'1({j + 1}): test{j}'
    for i in range(num_threads):
        assert threads[i].is_alive()
        query_queue[i].put('ping', timeout=1)
    for i in range(num_threads):
        r = result_queue[i].get(timeout=1)
        assert r == f'{i}({i + 1}): ok - thread alive'
        assert threads[i].is_alive()
    for i in range(num_threads):
        query_queue[i].put(None, timeout=1)


def test_maxusage():
    persist = PersistentPg(20)
    db = persist.connection()
    assert db._maxusage == 20
    for i in range(100):
        r = db.query(f'select test{i}')
        assert r == f'test{i}'
        assert db.db.status
        j = i % 20 + 1
        assert db._usage == j
        assert db.num_queries == j


def test_setsession():
    persist = PersistentPg(3, ('set datestyle',))
    db = persist.connection()
    assert db._maxusage == 3
    assert db._setsession_sql == ('set datestyle',)
    assert db.db.session == ['datestyle']
    db.query('set test')
    for _i in range(3):
        assert db.db.session == ['datestyle', 'test']
        db.query('select test')
    assert db.db.session == ['datestyle']


def test_failed_transaction():
    persist = PersistentPg()
    db = persist.connection()
    db._con.close()
    assert db.query('select test') == 'test'
    db.begin()
    db._con.close()
    with pytest.raises(pg.InternalError):
        db.query('select test')
    assert db.query('select test') == 'test'
    db.begin()
    assert db.query('select test') == 'test'
    db.rollback()
    db._con.close()
    assert db.query('select test') == 'test'


def test_context_manager():
    persist = PersistentPg()
    with persist.connection() as db:
        db.query('select test')
        assert db.num_queries == 1
