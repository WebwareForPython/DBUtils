"""Test the PooledPg module.

Note:
We don't test performance here, so the test does not predicate
whether PooledPg actually will help in improving performance or not.
We also assume that the underlying SteadyPg connections are tested.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke
"""

import unittest

from . import mock_pg  # noqa

from dbutils.pooled_pg import PooledPg, InvalidConnection, TooManyConnections


class TestPooledPg(unittest.TestCase):

    def test_version(self):
        from dbutils import __version__, pooled_pg
        self.assertEqual(pooled_pg.__version__, __version__)
        self.assertEqual(PooledPg.version, __version__)

    def test_create_connection(self):
        pool = PooledPg(
            1, 1, 0, False, None, None, False,
            'PooledPgTestDB', user='PooledPgTestUser')
        self.assertTrue(hasattr(pool, '_cache'))
        self.assertEqual(pool._cache.qsize(), 1)
        self.assertTrue(hasattr(pool, '_maxusage'))
        self.assertIsNone(pool._maxusage)
        self.assertTrue(hasattr(pool, '_setsession'))
        self.assertIsNone(pool._setsession)
        self.assertTrue(hasattr(pool, '_reset'))
        self.assertFalse(pool._reset)
        db_con = pool._cache.get(0)
        pool._cache.put(db_con, 0)
        from dbutils.steady_pg import SteadyPgConnection
        self.assertTrue(isinstance(db_con, SteadyPgConnection))
        db = pool.connection()
        self.assertEqual(pool._cache.qsize(), 0)
        self.assertTrue(hasattr(db, '_con'))
        self.assertEqual(db._con, db_con)
        self.assertTrue(hasattr(db, 'query'))
        self.assertTrue(hasattr(db, 'num_queries'))
        self.assertEqual(db.num_queries, 0)
        self.assertTrue(hasattr(db, '_maxusage'))
        self.assertEqual(db._maxusage, 0)
        self.assertTrue(hasattr(db, '_setsession_sql'))
        self.assertIsNone(db._setsession_sql)
        self.assertTrue(hasattr(db, 'dbname'))
        self.assertEqual(db.dbname, 'PooledPgTestDB')
        self.assertTrue(hasattr(db, 'user'))
        self.assertEqual(db.user, 'PooledPgTestUser')
        db.query('select test')
        self.assertEqual(db.num_queries, 1)
        pool = PooledPg(1)
        db = pool.connection()
        self.assertTrue(hasattr(db, 'dbname'))
        self.assertIsNone(db.dbname)
        self.assertTrue(hasattr(db, 'user'))
        self.assertIsNone(db.user)
        self.assertTrue(hasattr(db, 'num_queries'))
        self.assertEqual(db.num_queries, 0)
        pool = PooledPg(0, 0, 0, False, 3, ('set datestyle',),)
        self.assertEqual(pool._maxusage, 3)
        self.assertEqual(pool._setsession, ('set datestyle',))
        db = pool.connection()
        self.assertEqual(db._maxusage, 3)
        self.assertEqual(db._setsession_sql, ('set datestyle',))

    def test_close_connection(self):
        pool = PooledPg(
            0, 1, 0, False, None, None, False,
            'PooledPgTestDB', user='PooledPgTestUser')
        db = pool.connection()
        self.assertTrue(hasattr(db, '_con'))
        db_con = db._con
        from dbutils.steady_pg import SteadyPgConnection
        self.assertTrue(isinstance(db_con, SteadyPgConnection))
        self.assertTrue(hasattr(pool, '_cache'))
        self.assertEqual(pool._cache.qsize(), 0)
        self.assertEqual(db.num_queries, 0)
        db.query('select test')
        self.assertEqual(db.num_queries, 1)
        db.close()
        self.assertRaises(InvalidConnection, getattr, db, 'num_queries')
        db = pool.connection()
        self.assertTrue(hasattr(db, 'dbname'))
        self.assertEqual(db.dbname, 'PooledPgTestDB')
        self.assertTrue(hasattr(db, 'user'))
        self.assertEqual(db.user, 'PooledPgTestUser')
        self.assertEqual(db.num_queries, 1)
        db.query('select test')
        self.assertEqual(db.num_queries, 2)
        db = pool.connection()
        self.assertEqual(pool._cache.qsize(), 1)
        self.assertEqual(pool._cache.get(0), db_con)

    def test_min_max_cached(self):
        pool = PooledPg(3)
        self.assertTrue(hasattr(pool, '_cache'))
        self.assertEqual(pool._cache.qsize(), 3)
        cache = [pool.connection() for i in range(3)]
        self.assertEqual(pool._cache.qsize(), 0)
        for i in range(3):
            cache.pop().close()
        self.assertEqual(pool._cache.qsize(), 3)
        for i in range(6):
            cache.append(pool.connection())
        self.assertEqual(pool._cache.qsize(), 0)
        for i in range(6):
            cache.pop().close()
        self.assertEqual(pool._cache.qsize(), 6)
        pool = PooledPg(3, 4)
        self.assertTrue(hasattr(pool, '_cache'))
        self.assertEqual(pool._cache.qsize(), 3)
        cache = [pool.connection() for i in range(3)]
        self.assertEqual(pool._cache.qsize(), 0)
        for i in range(3):
            cache.pop().close()
        self.assertEqual(pool._cache.qsize(), 3)
        for i in range(6):
            cache.append(pool.connection())
        self.assertEqual(pool._cache.qsize(), 0)
        for i in range(6):
            cache.pop().close()
        self.assertEqual(pool._cache.qsize(), 4)
        pool = PooledPg(3, 2)
        self.assertTrue(hasattr(pool, '_cache'))
        self.assertEqual(pool._cache.qsize(), 3)
        cache = [pool.connection() for i in range(4)]
        self.assertEqual(pool._cache.qsize(), 0)
        for i in range(4):
            cache.pop().close()
        self.assertEqual(pool._cache.qsize(), 3)
        pool = PooledPg(2, 5)
        self.assertTrue(hasattr(pool, '_cache'))
        self.assertEqual(pool._cache.qsize(), 2)
        cache = [pool.connection() for i in range(10)]
        self.assertEqual(pool._cache.qsize(), 0)
        for i in range(10):
            cache.pop().close()
        self.assertEqual(pool._cache.qsize(), 5)

    def test_max_connections(self):
        from dbutils.pooled_pg import TooManyConnections
        pool = PooledPg(1, 2, 3)
        self.assertEqual(pool._cache.qsize(), 1)
        cache = [pool.connection() for i in range(3)]
        self.assertEqual(pool._cache.qsize(), 0)
        self.assertRaises(TooManyConnections, pool.connection)
        pool = PooledPg(0, 1, 1, False)
        self.assertEqual(pool._blocking, 0)
        self.assertEqual(pool._cache.qsize(), 0)
        db = pool.connection()
        self.assertEqual(pool._cache.qsize(), 0)
        self.assertRaises(TooManyConnections, pool.connection)
        del db
        del cache
        pool = PooledPg(1, 2, 1)
        self.assertEqual(pool._cache.qsize(), 1)
        cache = [pool.connection()]
        self.assertEqual(pool._cache.qsize(), 0)
        cache.append(pool.connection())
        self.assertEqual(pool._cache.qsize(), 0)
        self.assertRaises(TooManyConnections, pool.connection)
        pool = PooledPg(3, 2, 1, False)
        self.assertEqual(pool._cache.qsize(), 3)
        cache = [pool.connection() for i in range(3)]
        self.assertEqual(len(cache), 3)
        self.assertEqual(pool._cache.qsize(), 0)
        self.assertRaises(TooManyConnections, pool.connection)
        pool = PooledPg(1, 1, 1, True)
        self.assertEqual(pool._blocking, 1)
        self.assertEqual(pool._cache.qsize(), 1)
        db = pool.connection()
        self.assertEqual(pool._cache.qsize(), 0)

        def connection():
            pool.connection().query('set thread')

        from threading import Thread
        thread = Thread(target=connection)
        thread.start()
        thread.join(0.1)
        self.assertTrue(thread.is_alive())
        self.assertEqual(pool._cache.qsize(), 0)
        session = db._con.session
        self.assertEqual(session, [])
        del db
        thread.join(0.1)
        self.assertFalse(thread.is_alive())
        self.assertEqual(pool._cache.qsize(), 1)
        db = pool.connection()
        self.assertEqual(pool._cache.qsize(), 0)
        self.assertEqual(session, ['thread'])
        del db

    def test_one_thread_two_connections(self):
        pool = PooledPg(2)
        db1 = pool.connection()
        for i in range(5):
            db1.query('select test')
        db2 = pool.connection()
        self.assertNotEqual(db1, db2)
        self.assertNotEqual(db1._con, db2._con)
        for i in range(7):
            db2.query('select test')
        self.assertEqual(db1.num_queries, 5)
        self.assertEqual(db2.num_queries, 7)
        del db1
        db1 = pool.connection()
        self.assertNotEqual(db1, db2)
        self.assertNotEqual(db1._con, db2._con)
        self.assertTrue(hasattr(db1, 'query'))
        for i in range(3):
            db1.query('select test')
        self.assertEqual(db1.num_queries, 8)
        db2.query('select test')
        self.assertEqual(db2.num_queries, 8)

    def test_three_threads_two_connections(self):
        pool = PooledPg(2, 2, 2, True)
        try:
            from queue import Queue, Empty
        except ImportError:  # Python 2
            from Queue import Queue, Empty
        queue = Queue(3)

        def connection():
            try:
                queue.put(pool.connection(), 1, 1)
            except TypeError:
                queue.put(pool.connection(), 1)

        from threading import Thread
        for i in range(3):
            Thread(target=connection).start()
        try:
            db1 = queue.get(1, 1)
            db2 = queue.get(1, 1)
        except TypeError:
            db1 = queue.get(1)
            db2 = queue.get(1)
        db1_con = db1._con
        db2_con = db2._con
        self.assertNotEqual(db1, db2)
        self.assertNotEqual(db1_con, db2_con)
        try:
            self.assertRaises(Empty, queue.get, 1, 0.1)
        except TypeError:
            self.assertRaises(Empty, queue.get, 0)
        del db1
        try:
            db1 = queue.get(1, 1)
        except TypeError:
            db1 = queue.get(1)
        self.assertNotEqual(db1, db2)
        self.assertNotEqual(db1._con, db2._con)
        self.assertEqual(db1._con, db1_con)

    def test_reset_transaction(self):
        pool = PooledPg(1)
        db = pool.connection()
        db.begin()
        con = db._con
        self.assertTrue(con._transaction)
        db.query('select test')
        self.assertEqual(con.num_queries, 1)
        db.close()
        self.assertIs(pool.connection()._con, con)
        self.assertFalse(con._transaction)
        self.assertEqual(con.session, ['begin', 'rollback'])
        self.assertEqual(con.num_queries, 1)
        pool = PooledPg(1, reset=1)
        db = pool.connection()
        db.begin()
        con = db._con
        self.assertTrue(con._transaction)
        self.assertEqual(con.session, ['rollback', 'begin'])
        db.query('select test')
        self.assertEqual(con.num_queries, 1)
        db.close()
        self.assertIs(pool.connection()._con, con)
        self.assertFalse(con._transaction)
        self.assertEqual(
            con.session, ['rollback', 'begin', 'rollback', 'rollback'])
        self.assertEqual(con.num_queries, 1)
        pool = PooledPg(1, reset=2)
        db = pool.connection()
        db.begin()
        con = db._con
        self.assertTrue(con._transaction)
        self.assertEqual(con.session, ['begin'])
        db.query('select test')
        self.assertEqual(con.num_queries, 1)
        db.close()
        self.assertIs(pool.connection()._con, con)
        self.assertFalse(con._transaction)
        self.assertEqual(con.session, [])
        self.assertEqual(con.num_queries, 0)

    def test_context_manager(self):
        pool = PooledPg(1, 1, 1)
        with pool.connection() as db:
            db_con = db._con._con
            db.query('select test')
            self.assertEqual(db_con.num_queries, 1)
            self.assertRaises(TooManyConnections, pool.connection)
        with pool.connection() as db:
            db_con = db._con._con
            db.query('select test')
            self.assertEqual(db_con.num_queries, 2)
            self.assertRaises(TooManyConnections, pool.connection)


if __name__ == '__main__':
    unittest.main()
