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

import DBUtils.Tests.mock_db as dbapi

from DBUtils import SimplePooledDB

__version__ = '1.3'


def versionString(version):
    """Create version string."""
    ver = [str(v) for v in version]
    numbers, rest = ver[:2 if ver[2] == '0' else 3], ver[3:]
    return '.'.join(numbers) + '-'.join(rest)


class TestSimplePooledDB(unittest.TestCase):

    def my_dbpool(self, mythreadsafety, maxConnections):
        threadsafety = dbapi.threadsafety
        dbapi.threadsafety = mythreadsafety
        try:
            return SimplePooledDB.PooledDB(
                dbapi, maxConnections,
                'SimplePooledDBTestDB', 'SimplePooledDBTestUser')
        finally:
            dbapi.threadsafety = threadsafety

    def test0_check_version(self):
        from DBUtils import __version__ as DBUtilsVersion
        self.assertEqual(DBUtilsVersion, __version__)
        from DBUtils.Properties import version
        self.assertEqual(versionString(version), __version__)
        self.assertEqual(SimplePooledDB.__version__, __version__)
        self.assertEqual(SimplePooledDB.PooledDB.version, __version__)

    def test1_no_threadsafety(self):
        for threadsafety in (None, -1, 0, 4):
            self.assertRaises(
                SimplePooledDB.NotSupportedError,
                self.my_dbpool, threadsafety, 1)

    def test2_create_connection(self):
        for threadsafety in (1, 2, 3):
            dbpool = self.my_dbpool(threadsafety, 1)
            db = dbpool.connection()
            self.assertTrue(hasattr(db, 'cursor'))
            self.assertTrue(hasattr(db, 'open_cursors'))
            self.assertEqual(db.open_cursors, 0)
            self.assertTrue(hasattr(db, 'database'))
            self.assertEqual(db.database, 'SimplePooledDBTestDB')
            self.assertTrue(hasattr(db, 'user'))
            self.assertEqual(db.user, 'SimplePooledDBTestUser')
            cursor = db.cursor()
            self.assertEqual(db.open_cursors, 1)
            del cursor

    def test3_close_connection(self):
        for threadsafety in (1, 2, 3):
            dbpool = self.my_dbpool(threadsafety, 1)
            db = dbpool.connection()
            self.assertEqual(db.open_cursors, 0)
            cursor1 = db.cursor()
            self.assertEqual(db.open_cursors, 1)
            db.close()
            self.assertTrue(not hasattr(db, 'open_cursors'))
            db = dbpool.connection()
            self.assertTrue(hasattr(db, 'database'))
            self.assertEqual(db.database, 'SimplePooledDBTestDB')
            self.assertTrue(hasattr(db, 'user'))
            self.assertEqual(db.user, 'SimplePooledDBTestUser')
            self.assertEqual(db.open_cursors, 1)
            cursor2 = db.cursor()
            self.assertEqual(db.open_cursors, 2)
            del cursor2
            del cursor1

    def test4_two_connections(self):
        for threadsafety in (1, 2, 3):
            dbpool = self.my_dbpool(threadsafety, 2)
            db1 = dbpool.connection()
            cursors1 = [db1.cursor() for i in range(5)]
            db2 = dbpool.connection()
            self.assertNotEqual(db1, db2)
            cursors2 = [db2.cursor() for i in range(7)]
            self.assertEqual(db1.open_cursors, 5)
            self.assertEqual(db2.open_cursors, 7)
            db1.close()
            db1 = dbpool.connection()
            self.assertNotEqual(db1, db2)
            self.assertTrue(hasattr(db1, 'cursor'))
            for i in range(3):
                cursors1.append(db1.cursor())
            self.assertEqual(db1.open_cursors, 8)
            cursors2.append(db2.cursor())
            self.assertEqual(db2.open_cursors, 8)
            del cursors2
            del cursors1

    def test5_threadsafety_1(self):
        dbpool = self.my_dbpool(1, 2)
        try:
            from queue import Queue, Empty
        except ImportError:  # Python 2
            from Queue import Queue, Empty
        queue = Queue(3)

        def connection():
            queue.put(dbpool.connection())

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

    def test6_threadsafety_2(self):
        for threadsafety in (2, 3):
            dbpool = self.my_dbpool(threadsafety, 2)
            db1 = dbpool.connection()
            db2 = dbpool.connection()
            cursors = [dbpool.connection().cursor() for i in range(100)]
            self.assertEqual(db1.open_cursors, 50)
            self.assertEqual(db2.open_cursors, 50)
            del cursors


if __name__ == '__main__':
    unittest.main()
