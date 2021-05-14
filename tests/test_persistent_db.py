"""Test the PersistentDB module.

Note:
We don't test performance here, so the test does not predicate
whether PersistentDB actually will help in improving performance or not.
We also assume that the underlying SteadyDB connections are tested.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke
"""

import unittest

from . import mock_db as dbapi

from dbutils.persistent_db import PersistentDB, local


class TestPersistentDB(unittest.TestCase):

    def setUp(self):
        dbapi.threadsafety = 1

    def test_version(self):
        from dbutils import __version__, persistent_db
        self.assertEqual(persistent_db.__version__, __version__)
        self.assertEqual(PersistentDB.version, __version__)

    def test_no_threadsafety(self):
        from dbutils.persistent_db import NotSupportedError
        for dbapi.threadsafety in (None, 0):
            self.assertRaises(NotSupportedError, PersistentDB, dbapi)

    def test_close(self):
        for closeable in (False, True):
            persist = PersistentDB(dbapi, closeable=closeable)
            db = persist.connection()
            self.assertTrue(db._con.valid)
            db.close()
            self.assertTrue(closeable ^ db._con.valid)
            db.close()
            self.assertTrue(closeable ^ db._con.valid)
            db._close()
            self.assertFalse(db._con.valid)
            db._close()
            self.assertFalse(db._con.valid)

    def test_connection(self):
        persist = PersistentDB(dbapi)
        db = persist.connection()
        db_con = db._con
        self.assertIsNone(db_con.database)
        self.assertIsNone(db_con.user)
        db2 = persist.connection()
        self.assertEqual(db, db2)
        db3 = persist.dedicated_connection()
        self.assertEqual(db, db3)
        db3.close()
        db2.close()
        db.close()

    def test_threads(self):
        num_threads = 3
        persist = PersistentDB(dbapi, closeable=True)
        try:
            from queue import Queue, Empty
        except ImportError:  # Python 2
            from Queue import Queue, Empty
        query_queue, result_queue = [], []
        for i in range(num_threads):
            query_queue.append(Queue(1))
            result_queue.append(Queue(1))

        def run_queries(i):
            this_db = persist.connection()
            while 1:
                try:
                    try:
                        q = query_queue[i].get(1, 1)
                    except TypeError:
                        q = query_queue[i].get(1)
                except Empty:
                    q = None
                if not q:
                    break
                db = persist.connection()
                if db != this_db:
                    r = 'error - not persistent'
                else:
                    if q == 'ping':
                        r = 'ok - thread alive'
                    elif q == 'close':
                        db.close()
                        r = 'ok - connection closed'
                    else:
                        cursor = db.cursor()
                        cursor.execute(q)
                        r = cursor.fetchone()
                        cursor.close()
                r = '%d(%d): %s' % (i, db._usage, r)
                try:
                    result_queue[i].put(r, 1, 1)
                except TypeError:
                    result_queue[i].put(r, 1)
            db.close()

        from threading import Thread
        threads = []
        for i in range(num_threads):
            thread = Thread(target=run_queries, args=(i,))
            threads.append(thread)
            thread.start()
        for i in range(num_threads):
            try:
                query_queue[i].put('ping', 1, 1)
            except TypeError:
                query_queue[i].put('ping', 1)
        for i in range(num_threads):
            try:
                r = result_queue[i].get(1, 1)
            except TypeError:
                r = result_queue[i].get(1)
            self.assertEqual(r, '%d(0): ok - thread alive' % i)
            self.assertTrue(threads[i].is_alive())
        for i in range(num_threads):
            for j in range(i + 1):
                try:
                    query_queue[i].put('select test%d' % j, 1, 1)
                    r = result_queue[i].get(1, 1)
                except TypeError:
                    query_queue[i].put('select test%d' % j, 1)
                    r = result_queue[i].get(1)
                self.assertEqual(r, '%d(%d): test%d' % (i, j + 1, j))
        try:
            query_queue[1].put('select test4', 1, 1)
        except TypeError:
            query_queue[1].put('select test4', 1)
        try:
            r = result_queue[1].get(1, 1)
        except TypeError:
            r = result_queue[1].get(1)
        self.assertEqual(r, '1(3): test4')
        try:
            query_queue[1].put('close', 1, 1)
            r = result_queue[1].get(1, 1)
        except TypeError:
            query_queue[1].put('close', 1)
            r = result_queue[1].get(1)
        self.assertEqual(r, '1(3): ok - connection closed')
        for j in range(2):
            try:
                query_queue[1].put('select test%d' % j, 1, 1)
                r = result_queue[1].get(1, 1)
            except TypeError:
                query_queue[1].put('select test%d' % j, 1)
                r = result_queue[1].get(1)
            self.assertEqual(r, '1(%d): test%d' % (j + 1, j))
        for i in range(num_threads):
            self.assertTrue(threads[i].is_alive())
            try:
                query_queue[i].put('ping', 1, 1)
            except TypeError:
                query_queue[i].put('ping', 1)
        for i in range(num_threads):
            try:
                r = result_queue[i].get(1, 1)
            except TypeError:
                r = result_queue[i].get(1)
            self.assertEqual(r, '%d(%d): ok - thread alive' % (i, i + 1))
            self.assertTrue(threads[i].is_alive())
        for i in range(num_threads):
            try:
                query_queue[i].put(None, 1, 1)
            except TypeError:
                query_queue[i].put(None, 1)

    def test_maxusage(self):
        persist = PersistentDB(dbapi, 20)
        db = persist.connection()
        self.assertEqual(db._maxusage, 20)
        for i in range(100):
            cursor = db.cursor()
            cursor.execute('select test%d' % i)
            r = cursor.fetchone()
            cursor.close()
            self.assertEqual(r, 'test%d' % i)
            self.assertTrue(db._con.valid)
            j = i % 20 + 1
            self.assertEqual(db._usage, j)
            self.assertEqual(db._con.num_uses, j)
            self.assertEqual(db._con.num_queries, j)

    def test_setsession(self):
        persist = PersistentDB(dbapi, 3, ('set datestyle',))
        db = persist.connection()
        self.assertEqual(db._maxusage, 3)
        self.assertEqual(db._setsession_sql, ('set datestyle',))
        self.assertEqual(db._con.session, ['datestyle'])
        cursor = db.cursor()
        cursor.execute('set test')
        cursor.fetchone()
        cursor.close()
        for i in range(3):
            self.assertEqual(db._con.session, ['datestyle', 'test'])
            cursor = db.cursor()
            cursor.execute('select test')
            cursor.fetchone()
            cursor.close()
        self.assertEqual(db._con.session, ['datestyle'])

    def test_threadlocal(self):
        persist = PersistentDB(dbapi)
        self.assertTrue(isinstance(persist.thread, local))

        class threadlocal:
            pass

        persist = PersistentDB(dbapi, threadlocal=threadlocal)
        self.assertTrue(isinstance(persist.thread, threadlocal))

    def test_ping_check(self):
        Connection = dbapi.Connection
        Connection.has_ping = True
        Connection.num_pings = 0
        persist = PersistentDB(dbapi, 0, None, None, 0, True)
        db = persist.connection()
        self.assertTrue(db._con.valid)
        self.assertEqual(Connection.num_pings, 0)
        db.close()
        db = persist.connection()
        self.assertFalse(db._con.valid)
        self.assertEqual(Connection.num_pings, 0)
        persist = PersistentDB(dbapi, 0, None, None, 1, True)
        db = persist.connection()
        self.assertTrue(db._con.valid)
        self.assertEqual(Connection.num_pings, 1)
        db.close()
        db = persist.connection()
        self.assertTrue(db._con.valid)
        self.assertEqual(Connection.num_pings, 2)
        persist = PersistentDB(dbapi, 0, None, None, 2, True)
        db = persist.connection()
        self.assertTrue(db._con.valid)
        self.assertEqual(Connection.num_pings, 2)
        db.close()
        db = persist.connection()
        self.assertFalse(db._con.valid)
        self.assertEqual(Connection.num_pings, 2)
        cursor = db.cursor()
        self.assertTrue(db._con.valid)
        self.assertEqual(Connection.num_pings, 3)
        cursor.execute('select test')
        self.assertTrue(db._con.valid)
        self.assertEqual(Connection.num_pings, 3)
        persist = PersistentDB(dbapi, 0, None, None, 4, True)
        db = persist.connection()
        self.assertTrue(db._con.valid)
        self.assertEqual(Connection.num_pings, 3)
        db.close()
        db = persist.connection()
        self.assertFalse(db._con.valid)
        self.assertEqual(Connection.num_pings, 3)
        cursor = db.cursor()
        db._con.close()
        self.assertFalse(db._con.valid)
        self.assertEqual(Connection.num_pings, 3)
        cursor.execute('select test')
        self.assertTrue(db._con.valid)
        self.assertEqual(Connection.num_pings, 4)
        Connection.has_ping = False
        Connection.num_pings = 0

    def test_failed_transaction(self):
        persist = PersistentDB(dbapi)
        db = persist.connection()
        cursor = db.cursor()
        db._con.close()
        cursor.execute('select test')
        db.begin()
        db._con.close()
        self.assertRaises(dbapi.InternalError, cursor.execute, 'select test')
        cursor.execute('select test')
        db.begin()
        db.cancel()
        db._con.close()
        cursor.execute('select test')

    def test_context_manager(self):
        persist = PersistentDB(dbapi)
        with persist.connection() as db:
            with db.cursor() as cursor:
                cursor.execute('select test')
                r = cursor.fetchone()
            self.assertEqual(r, 'test')


if __name__ == '__main__':
    unittest.main()
