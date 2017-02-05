"""Test the SimplePooledPg module.

Note:
We don't test performance here, so the test does not predicate
whether SimplePooledPg actually will help in improving performance or not.


Copyright and credit info:

* This test was contributed by Christoph Zwerschke

"""

import sys
import unittest

__version__ = '1.2'

# This module also serves as a mock object for the pg API module:
sys.modules['pg'] = sys.modules[__name__]


class DB:

    def __init__(self, dbname, user):
        self.dbname = dbname
        self.user = user
        self.num_queries = 0

    def close(self):
        self.num_queries = 0

    def query(self):
        self.num_queries += 1


sys.path.insert(1, '../..')
from DBUtils import SimplePooledPg


class TestSimplePooledPg(unittest.TestCase):

    def my_dbpool(self, maxConnections):
        return SimplePooledPg.PooledPg(maxConnections,
            'SimplePooledPgTestDB', 'SimplePooledPgTestUser')

    def test0_check_version(self):
        from DBUtils import __version__ as DBUtilsVersion
        self.assertEqual(DBUtilsVersion, __version__)
        self.assertEqual(SimplePooledPg.__version__, __version__)
        self.assertEqual(SimplePooledPg.PooledPg.version, __version__)

    def test1_create_connection(self):
        dbpool = self.my_dbpool(1)
        db = dbpool.connection()
        self.assertTrue(hasattr(db, 'query'))
        self.assertTrue(hasattr(db, 'num_queries'))
        self.assertEqual(db.num_queries, 0)
        self.assertTrue(hasattr(db, 'dbname'))
        self.assertEqual(db.dbname, 'SimplePooledPgTestDB')
        self.assertTrue(hasattr(db, 'user'))
        self.assertEqual(db.user, 'SimplePooledPgTestUser')
        db.query()
        self.assertEqual(db.num_queries, 1)

    def test2_close_connection(self):
        dbpool = self.my_dbpool(1)
        db = dbpool.connection()
        self.assertEqual(db.num_queries, 0)
        db.query()
        self.assertEqual(db.num_queries, 1)
        db.close()
        self.assertTrue(not hasattr(db, 'num_queries'))
        db = dbpool.connection()
        self.assertTrue(hasattr(db, 'dbname'))
        self.assertEqual(db.dbname, 'SimplePooledPgTestDB')
        self.assertTrue(hasattr(db, 'user'))
        self.assertEqual(db.user, 'SimplePooledPgTestUser')
        self.assertEqual(db.num_queries, 1)
        db.query()
        self.assertEqual(db.num_queries, 2)

    def test3_two_connections(self):
        dbpool = self.my_dbpool(2)
        db1 = dbpool.connection()
        for i in range(5):
            db1.query()
        db2 = dbpool.connection()
        self.assertNotEqual(db1, db2)
        self.assertNotEqual(db1._con, db2._con)
        for i in range(7):
            db2.query()
        self.assertEqual(db1.num_queries, 5)
        self.assertEqual(db2.num_queries, 7)
        db1.close()
        db1 = dbpool.connection()
        self.assertNotEqual(db1, db2)
        self.assertNotEqual(db1._con, db2._con)
        self.assertTrue(hasattr(db1, 'query'))
        for i in range(3):
            db1.query()
        self.assertEqual(db1.num_queries, 8)
        db2.query()
        self.assertEqual(db2.num_queries, 8)

    def test4_threads(self):
        dbpool = self.my_dbpool(2)
        try:
            from Queue import Queue, Empty
        except ImportError:  # Python 3
            from queue import Queue, Empty
        queue = Queue(3)
        def connection():
            queue.put(dbpool.connection())
        from threading import Thread
        thread1 = Thread(target=connection).start()
        thread2 = Thread(target=connection).start()
        thread3 = Thread(target=connection).start()
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


if __name__ == '__main__':
    unittest.main()
