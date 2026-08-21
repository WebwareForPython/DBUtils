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


def test_version():
    """Check that the module and class versions are in sync."""
    from dbutils import __version__, persistent_db
    assert persistent_db.__version__ == __version__
    assert PersistentDB.version == __version__


@pytest.mark.parametrize("threadsafety", [None, 0])
def test_no_threadsafety(dbapi, threadsafety):
    """Check that a database module that is not thread-safe is rejected."""
    dbapi.threadsafety = threadsafety
    with pytest.raises(NotSupportedError):
        PersistentDB(dbapi)


def test_creator_function(dbapi):
    """Check that a creator function can be used instead of a module."""
    persist = PersistentDB(dbapi.connect, database='ok')
    # the threadsafety cannot be determined from a plain creator function,
    # so the connections are optimistically assumed to be thread-safe
    db = persist.connection()
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
        PersistentDB(Creator)


def test_creator_with_unsafe_connections(dbapi, monkeypatch):
    """Check that connections that are not thread-safe are rejected."""
    monkeypatch.delattr(dbapi, 'threadsafety')
    # a creator function is optimistically assumed to provide thread-safe
    # connections, but the connections themselves know better
    persist = PersistentDB(dbapi.connect)
    with pytest.raises(NotSupportedError):
        persist.connection()


@pytest.mark.parametrize("closeable", [False, True])
def test_close(dbapi, closeable):
    """Check that closing is only allowed when the connection is closeable."""
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


def test_connection(dbapi):
    """Check that the same thread always gets the same connection."""
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


def test_threads(dbapi):
    """Check that every thread keeps its own persistent connection."""
    num_threads = 3
    persist = PersistentDB(dbapi, closeable=True)
    query_queue, result_queue = [], []
    for _i in range(num_threads):
        query_queue.append(Queue(1))
        result_queue.append(Queue(1))

    def run_queries(idx):
        """Answer the queries sent to this thread until it gets None.

        Every answer is prefixed with the thread number and the usage
        count of the connection, so that the main thread can check that
        the thread kept using its own connection.
        """
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
    # all threads are alive and have an unused connection of their own
    for i in range(num_threads):
        query_queue[i].put('ping', timeout=1)
    for i in range(num_threads):
        r = result_queue[i].get(timeout=1)
        assert r == f'{i}(0): ok - thread alive'
        assert threads[i].is_alive()
    # let thread number i run i + 1 queries on its own connection
    for i in range(num_threads):
        for j in range(i + 1):
            query_queue[i].put(f'select test{j}', timeout=1)
            r = result_queue[i].get(timeout=1)
            assert r == f'{i}({j + 1}): test{j}'
    # closing the connection of the second thread restarts its usage count,
    # but does not affect the connections of the other threads
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
    # every thread still has its own connection with its own usage count
    for i in range(num_threads):
        assert threads[i].is_alive()
        query_queue[i].put('ping', timeout=1)
    for i in range(num_threads):
        r = result_queue[i].get(timeout=1)
        assert r == f'{i}({i + 1}): ok - thread alive'
        assert threads[i].is_alive()
    # send the sentinel that makes the threads finish
    for i in range(num_threads):
        query_queue[i].put(None, timeout=1)


def test_maxusage(dbapi):
    """Check that the connection is reset when used too often."""
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


def test_setsession(dbapi):
    """Check that the session is prepared after every reopening."""
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


def test_threadlocal(dbapi):
    """Check that the class for thread-local data can be replaced."""
    persist = PersistentDB(dbapi)
    assert isinstance(persist.thread, local)

    class Threadlocal:
        pass

    persist = PersistentDB(dbapi, threadlocal=Threadlocal)
    assert isinstance(persist.thread, Threadlocal)


def test_ping_check_never(dbapi, ping_con_cls):
    """Check that connections are not pinged when ping is 0."""
    persist = PersistentDB(dbapi, 0, None, None, 0, True)
    db = persist.connection()
    assert db._con.valid is True
    assert ping_con_cls.num_pings == 0
    # the closed connection is handed out again without being pinged,
    # so the fact that it is broken goes unnoticed
    db.close()
    db = persist.connection()
    assert db._con.valid is False
    assert ping_con_cls.num_pings == 0


def test_ping_check_when_fetched(dbapi, ping_con_cls):
    """Check that connections are pinged when ping is 1."""
    persist = PersistentDB(dbapi, 0, None, None, 1, True)
    db = persist.connection()
    assert db._con.valid is True
    assert ping_con_cls.num_pings == 1
    # the closed connection is pinged when it is requested again,
    # so it is transparently reopened
    db.close()
    db = persist.connection()
    assert db._con.valid is True
    assert ping_con_cls.num_pings == 2


def test_ping_check_with_sql_when_fetched(dbapi, con_cls):
    """Check that connections can be checked with an SQL statement."""
    persist = PersistentDB(dbapi, 0, None, None, 'select 1', True)
    db = persist.connection()
    assert db._con.valid is True
    # the statement has been executed instead of using the ping method
    assert db._con.num_queries == 1
    assert con_cls.num_pings == 0
    # the closed connection is checked when it is requested again,
    # so it is transparently reopened
    db.close()
    db = persist.connection()
    assert db._con.valid is True
    assert con_cls.num_pings == 0


def test_ping_check_when_cursor_created(dbapi, ping_con_cls):
    """Check that connections are pinged when ping is 2."""
    persist = PersistentDB(dbapi, 0, None, None, 2, True)
    db = persist.connection()
    assert db._con.valid is True
    assert ping_con_cls.num_pings == 0
    # requesting the closed connection does not ping it yet
    db.close()
    db = persist.connection()
    assert db._con.valid is False
    assert ping_con_cls.num_pings == 0
    # but creating a cursor does, which reopens the connection
    cursor = db.cursor()
    assert db._con.valid is True
    assert ping_con_cls.num_pings == 1
    # executing a query does not ping again
    cursor.execute('select test')
    assert db._con.valid is True
    assert ping_con_cls.num_pings == 1


def test_ping_check_when_query_executed(dbapi, ping_con_cls):
    """Check that connections are pinged when ping is 4."""
    persist = PersistentDB(dbapi, 0, None, None, 4, True)
    db = persist.connection()
    assert db._con.valid is True
    assert ping_con_cls.num_pings == 0
    # neither requesting the connection nor creating a cursor pings it
    db.close()
    db = persist.connection()
    assert db._con.valid is False
    assert ping_con_cls.num_pings == 0
    cursor = db.cursor()
    db._con.close()
    assert db._con.valid is False
    assert ping_con_cls.num_pings == 0
    # only executing a query does, which reopens the connection
    cursor.execute('select test')
    assert db._con.valid is True
    assert ping_con_cls.num_pings == 1


def test_failed_transaction(dbapi):
    """Check that a failed transaction is reported and recovered from."""
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


def test_context_manager(dbapi):
    """Check that connection and cursor can be used as context managers."""
    persist = PersistentDB(dbapi)
    with persist.connection() as db:
        with db.cursor() as cursor:
            cursor.execute('select test')
            r = cursor.fetchone()
        assert r == 'test'


def timeout_is_not_fatal(error):
    """Treat a deliberate server side timeout as not fatal."""
    return not error.args or error.args[0] != 3024


def test_isfatal_default(dbapi):
    """Check that no error check is configured by default."""
    persist = PersistentDB(dbapi)
    assert persist._isfatal is None
    db = persist.connection()
    assert db._isfatal is None


def test_isfatal(dbapi):
    """Check that isfatal is passed on and can veto the failover."""
    persist = PersistentDB(dbapi, isfatal=timeout_is_not_fatal)
    assert persist._isfatal is timeout_is_not_fatal
    db = persist.connection()
    assert db._isfatal is timeout_is_not_fatal
    dbapi.Connection.num_timeouts = 0
    cursor = db.cursor()
    with pytest.raises(dbapi.OperationalError):
        cursor.execute('timeout')
    assert dbapi.Connection.num_timeouts == 1
    # the failover mechanism still applies to other failures
    db._con.close()
    cursor.execute('select test')
    assert cursor.fetchone() == 'test'


def test_no_failover(dbapi):
    """Check that no_failover() suspends the failover mechanism."""
    persist = PersistentDB(dbapi)
    db = persist.connection()
    dbapi.Connection.num_timeouts = 0
    with db.cursor() as cursor:
        with cursor.no_failover(), pytest.raises(dbapi.OperationalError):
            cursor.execute('timeout')
        assert dbapi.Connection.num_timeouts == 1
        cursor.execute('select test')  # connection is still usable
        assert cursor.fetchone() == 'test'


def test_dbapi_connection(dbapi):
    """Check that the underlying DB-API 2 objects are accessible."""
    persist = PersistentDB(dbapi)
    db = persist.connection()
    con = db.dbapi_connection
    assert isinstance(con, dbapi.Connection)
    assert con is db._con
    cursor = db.cursor()
    assert cursor.dbapi_cursor is cursor._cursor
