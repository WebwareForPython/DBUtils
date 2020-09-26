"""Test the SimplePooledDB module.

Note:
We don't test performance here, so the test does not predicate
whether SimplePooledDB actually will help in improving performance or not.
We also do not test any real world DB-API 2 module, we just
mock the basic connection functionality of an arbitrary module.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke
"""

import unittest

from . import mock_db as dbapi

from dbutils import simple_pooled_db


class TestSimplePooledDB(unittest.TestCase):

    def my_db_pool(self, mythreadsafety, maxConnections):
        threadsafety = dbapi.threadsafety
        dbapi.threadsafety = mythreadsafety
        try:
            return simple_pooled_db.PooledDB(
                dbapi, maxConnections,
                'SimplePooledDBTestDB', 'SimplePooledDBTestUser')
        finally:
            dbapi.threadsafety = threadsafety

    def test_version(self):
        from dbutils import __version__
        self.assertEqual(simple_pooled_db.__version__, __version__)
        self.assertEqual(simple_pooled_db.PooledDB.version, __version__)

    def test_no_threadsafety(self):
        for threadsafety in (None, -1, 0, 4):
            self.assertRaises(
                simple_pooled_db.NotSupportedError,
                self.my_db_pool, threadsafety, 1)

    def test_create_connection(self):
        for threadsafety in (1, 2, 3):
            dbpool = self.my_db_pool(threadsafety, 1)
            db = dbpool.connection()
            self.assertTrue(hasattr(db, 'cursor'))
            self.assertTrue(hasattr(db, 'open_cursors'))
            self.assertEqual(db.open_cursors, 0)
            self.assertTrue(hasattr(db, 'database'))
            self.assertEqual(db.database, 'SimplePooledDBTestDB')
            self.assertTrue(hasattr(db, 'user'))
            self.assertEqual(db.user, 'SimplePooledDBTestUser')
            cursor = db.cursor()
            self.assertIsNotNone(cursor)
            self.assertEqual(db.open_cursors, 1)
            del cursor

    def test_close_connection(self):
        for threadsafety in (1, 2, 3):
            db_pool = self.my_db_pool(threadsafety, 1)
            db = db_pool.connection()
            self.assertEqual(db.open_cursors, 0)
            cursor1 = db.cursor()
            self.assertIsNotNone(cursor1)
            self.assertEqual(db.open_cursors, 1)
            db.close()
            self.assertFalse(hasattr(db, 'open_cursors'))
            db = db_pool.connection()
            self.assertTrue(hasattr(db, 'database'))
            self.assertEqual(db.database, 'SimplePooledDBTestDB')
            self.assertTrue(hasattr(db, 'user'))
            self.assertEqual(db.user, 'SimplePooledDBTestUser')
            self.assertEqual(db.open_cursors, 1)
            cursor2 = db.cursor()
            self.assertIsNotNone(cursor2)
            self.assertEqual(db.open_cursors, 2)
            del cursor2
            del cursor1

    def test_two_connections(self):
        for threadsafety in (1, 2, 3):
            db_pool = self.my_db_pool(threadsafety, 2)
            db1 = db_pool.connection()
            cursors1 = [db1.cursor() for i in range(5)]
            db2 = db_pool.connection()
            self.assertNotEqual(db1, db2)
            cursors2 = [db2.cursor() for i in range(7)]
            self.assertEqual(db1.open_cursors, 5)
            self.assertEqual(db2.open_cursors, 7)
            db1.close()
            db1 = db_pool.connection()
            self.assertNotEqual(db1, db2)
            self.assertTrue(hasattr(db1, 'cursor'))
            for i in range(3):
                cursors1.append(db1.cursor())
            self.assertEqual(db1.open_cursors, 8)
            cursors2.append(db2.cursor())
            self.assertEqual(db2.open_cursors, 8)
            del cursors2
            del cursors1

    def test_threadsafety_1(self):
        db_pool = self.my_db_pool(1, 2)
        try:
            from queue import Queue, Empty
        except ImportError:  # Python 2
            from Queue import Queue, Empty
        queue = Queue(3)

        def connection():
            queue.put(db_pool.connection())

        from threading import Thread
        threads = [Thread(target=connection).start() for i in range(3)]
        self.assertEqual(len(threads), 3)
        try:
            db1 = queue.get(1, 1)
            db2 = queue.get(1, 1)
        except TypeError:
            db1 = queue.get(1)
            db2 = queue.get(1)
        self.assertNotEqual(db1, db2)
        self.assertNotEqual(db1._con, db2._con)
        try:
            self.assertRaises(Empty, queue.get, 1, 0.1)
        except TypeError:
            self.assertRaises(Empty, queue.get, 0)
        db2.close()
        try:
            db3 = queue.get(1, 1)
        except TypeError:
            db3 = queue.get(1)
        self.assertNotEqual(db1, db3)
        self.assertNotEqual(db1._con, db3._con)

    def test_threadsafety_2(self):
        for threadsafety in (2, 3):
            dbpool = self.my_db_pool(threadsafety, 2)
            db1 = dbpool.connection()
            db2 = dbpool.connection()
            cursors = [dbpool.connection().cursor() for i in range(100)]
            self.assertEqual(db1.open_cursors, 50)
            self.assertEqual(db2.open_cursors, 50)
            del cursors


if __name__ == '__main__':
    unittest.main()
