"""Test the PersistentPg module.

Note:
We don't test performance here, so the test does not predicate
whether PersistentPg actually will help in improving performance or not.
We also assume that the underlying SteadyPg connections are tested.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke
"""

import unittest

from . import mock_pg as pg

from dbutils.persistent_pg import PersistentPg


class TestPersistentPg(unittest.TestCase):

    def test_version(self):
        from dbutils import __version__, persistent_pg
        self.assertEqual(persistent_pg.__version__, __version__)
        self.assertEqual(PersistentPg.version, __version__)

    def test_close(self):
        for closeable in (False, True):
            persist = PersistentPg(closeable=closeable)
            db = persist.connection()
            self.assertTrue(db._con.db and db._con.valid)
            db.close()
            self.assertTrue(
                closeable ^ (db._con.db is not None and db._con.valid))
            db.close()
            self.assertTrue(
                closeable ^ (db._con.db is not None and db._con.valid))
            db._close()
            self.assertFalse(db._con.db and db._con.valid)
            db._close()
            self.assertFalse(db._con.db and db._con.valid)

    def test_threads(self):
        num_threads = 3
        persist = PersistentPg()
        try:
            from queue import Queue, Empty
        except ImportError:  # Python 2
            from Queue import Queue, Empty
        query_queue, result_queue = [], []
        for i in range(num_threads):
            query_queue.append(Queue(1))
            result_queue.append(Queue(1))

        def run_queries(i):
            this_db = persist.connection().db
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
                if db.db != this_db:
                    r = 'error - not persistent'
                else:
                    if q == 'ping':
                        r = 'ok - thread alive'
                    elif q == 'close':
                        db.db.close()
                        r = 'ok - connection closed'
                    else:
                        r = db.query(q)
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
            r = result_queue[1].get(1, 1)
        except TypeError:
            query_queue[1].put('select test4', 1)
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
        persist = PersistentPg(20)
        db = persist.connection()
        self.assertEqual(db._maxusage, 20)
        for i in range(100):
            r = db.query('select test%d' % i)
            self.assertEqual(r, 'test%d' % i)
            self.assertTrue(db.db.status)
            j = i % 20 + 1
            self.assertEqual(db._usage, j)
            self.assertEqual(db.num_queries, j)

    def test_setsession(self):
        persist = PersistentPg(3, ('set datestyle',))
        db = persist.connection()
        self.assertEqual(db._maxusage, 3)
        self.assertEqual(db._setsession_sql, ('set datestyle',))
        self.assertEqual(db.db.session, ['datestyle'])
        db.query('set test')
        for i in range(3):
            self.assertEqual(db.db.session, ['datestyle', 'test'])
            db.query('select test')
        self.assertEqual(db.db.session, ['datestyle'])

    def test_failed_transaction(self):
        persist = PersistentPg()
        db = persist.connection()
        db._con.close()
        self.assertEqual(db.query('select test'), 'test')
        db.begin()
        db._con.close()
        self.assertRaises(pg.InternalError, db.query, 'select test')
        self.assertEqual(db.query('select test'), 'test')
        db.begin()
        self.assertEqual(db.query('select test'), 'test')
        db.rollback()
        db._con.close()
        self.assertEqual(db.query('select test'), 'test')

    def test_context_manager(self):
        persist = PersistentPg()
        with persist.connection() as db:
            db.query('select test')
            self.assertEqual(db.num_queries, 1)


if __name__ == '__main__':
    unittest.main()
