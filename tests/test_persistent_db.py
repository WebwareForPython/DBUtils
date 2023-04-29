"""Test the PersistentDB module.

Note:
We don't test performance here, so the test does not predicate
whether PersistentDB actually will help in improving performance or not.
We also assume that the underlying SteadyDB connections are tested.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke
"""

from queue import Empty, Queue
from threading import Thread

import pytest

from dbutils.persistent_db import NotSupportedError, PersistentDB, local

from .mock_db import dbapi  # noqa: F401


def test_version():
    from dbutils import __version__, persistent_db
    assert persistent_db.__version__ == __version__
    assert PersistentDB.version == __version__


@pytest.mark.parametrize("threadsafety", [None, 0])
def test_no_threadsafety(dbapi, threadsafety):  # noqa: F811
    dbapi.threadsafety = threadsafety
    with pytest.raises(NotSupportedError):
        PersistentDB(dbapi)


@pytest.mark.parametrize("closeable", [False, True])
def test_close(dbapi, closeable):  # noqa: F811
    persist = PersistentDB(dbapi, closeable=closeable)
    db = persist.connection()
    assert db._con.valid is True
    db.close()
    assert closeable ^ db._con.valid
    db.close()
    assert closeable ^ db._con.valid
    db._close()
    assert db._con.valid is False
    db._close()
    assert db._con.valid is False


def test_connection(dbapi):  # noqa: F811
    persist = PersistentDB(dbapi)
    db = persist.connection()
    db_con = db._con
    assert db_con.database is None
    assert db_con.user is None
    db2 = persist.connection()
    assert db == db2
    db3 = persist.dedicated_connection()
    assert db == db3
    db3.close()
    db2.close()
    db.close()


def test_threads(dbapi):  # noqa: F811
    num_threads = 3
    persist = PersistentDB(dbapi, closeable=True)
    query_queue, result_queue = [], []
    for _i in range(num_threads):
        query_queue.append(Queue(1))
        result_queue.append(Queue(1))

    def run_queries(idx):
        this_db = persist.connection()
        db = None
        while True:
            try:
                q = query_queue[idx].get(timeout=1)
            except Empty:
                q = None
            if not q:
                break
            db = persist.connection()
            if db != this_db:
                res = 'error - not persistent'
            elif q == 'ping':
                res = 'ok - thread alive'
            elif q == 'close':
                db.close()
                res = 'ok - connection closed'
            else:
                cursor = db.cursor()
                cursor.execute(q)
                res = cursor.fetchone()
                cursor.close()
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


def test_maxusage(dbapi):  # noqa: F811
    persist = PersistentDB(dbapi, 20)
    db = persist.connection()
    assert db._maxusage == 20
    for i in range(100):
        cursor = db.cursor()
        cursor.execute(f'select test{i}')
        r = cursor.fetchone()
        cursor.close()
        assert r == f'test{i}'
        assert db._con.valid is True
        j = i % 20 + 1
        assert db._usage == j
        assert db._con.num_uses == j
        assert db._con.num_queries == j


def test_setsession(dbapi):  # noqa: F811
    persist = PersistentDB(dbapi, 3, ('set datestyle',))
    db = persist.connection()
    assert db._maxusage == 3
    assert db._setsession_sql == ('set datestyle',)
    assert db._con.session == ['datestyle']
    cursor = db.cursor()
    cursor.execute('set test')
    cursor.fetchone()
    cursor.close()
    for _i in range(3):
        assert db._con.session == ['datestyle', 'test']
        cursor = db.cursor()
        cursor.execute('select test')
        cursor.fetchone()
        cursor.close()
    assert db._con.session == ['datestyle']


def test_threadlocal(dbapi):  # noqa: F811
    persist = PersistentDB(dbapi)
    assert isinstance(persist.thread, local)

    class Threadlocal:
        pass

    persist = PersistentDB(dbapi, threadlocal=Threadlocal)
    assert isinstance(persist.thread, Threadlocal)


def test_ping_check(dbapi):  # noqa: F811
    con_cls = dbapi.Connection
    con_cls.has_ping = True
    con_cls.num_pings = 0
    persist = PersistentDB(dbapi, 0, None, None, 0, True)
    db = persist.connection()
    assert db._con.valid is True
    assert con_cls.num_pings == 0
    db.close()
    db = persist.connection()
    assert db._con.valid is False
    assert con_cls.num_pings == 0
    persist = PersistentDB(dbapi, 0, None, None, 1, True)
    db = persist.connection()
    assert db._con.valid is True
    assert con_cls.num_pings == 1
    db.close()
    db = persist.connection()
    assert db._con.valid is True
    assert con_cls.num_pings == 2
    persist = PersistentDB(dbapi, 0, None, None, 2, True)
    db = persist.connection()
    assert db._con.valid is True
    assert con_cls.num_pings == 2
    db.close()
    db = persist.connection()
    assert db._con.valid is False
    assert con_cls.num_pings == 2
    cursor = db.cursor()
    assert db._con.valid is True
    assert con_cls.num_pings == 3
    cursor.execute('select test')
    assert db._con.valid is True
    assert con_cls.num_pings == 3
    persist = PersistentDB(dbapi, 0, None, None, 4, True)
    db = persist.connection()
    assert db._con.valid is True
    assert con_cls.num_pings == 3
    db.close()
    db = persist.connection()
    assert db._con.valid is False
    assert con_cls.num_pings == 3
    cursor = db.cursor()
    db._con.close()
    assert db._con.valid is False
    assert con_cls.num_pings == 3
    cursor.execute('select test')
    assert db._con.valid is True
    assert con_cls.num_pings == 4
    con_cls.has_ping = False
    con_cls.num_pings = 0


def test_failed_transaction(dbapi):  # noqa: F811
    persist = PersistentDB(dbapi)
    db = persist.connection()
    cursor = db.cursor()
    db._con.close()
    cursor.execute('select test')
    db.begin()
    db._con.close()
    with pytest.raises(dbapi.InternalError):
        cursor.execute('select test')
    cursor.execute('select test')
    db.begin()
    db.cancel()
    db._con.close()
    cursor.execute('select test')


def test_context_manager(dbapi):  # noqa: F811
    persist = PersistentDB(dbapi)
    with persist.connection() as db:
        with db.cursor() as cursor:
            cursor.execute('select test')
            r = cursor.fetchone()
        assert r == 'test'
