"""Test the SimplePooledPg module.

Note:
We don't test performance here, so the test does not predicate
whether SimplePooledPg actually will help in improving performance or not.


Copyright and credit info:

* This test was contributed by Christoph Zwerschke

"""

import unittest

import DBUtils.Tests.mock_pg  # noqa

from DBUtils import SimplePooledPg

__version__ = '1.3'


class TestSimplePooledPg(unittest.TestCase):

    def my_dbpool(self, maxConnections):
        return SimplePooledPg.PooledPg(
            maxConnections, 'SimplePooledPgTestDB', 'SimplePooledPgTestUser')

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
        db.query('select 1')
        self.assertEqual(db.num_queries, 1)

    def test2_close_connection(self):
        dbpool = self.my_dbpool(1)
        db = dbpool.connection()
        self.assertEqual(db.num_queries, 0)
        db.query('select 1')
        self.assertEqual(db.num_queries, 1)
        db.close()
        self.assertTrue(not hasattr(db, 'num_queries'))
        db = dbpool.connection()
        self.assertTrue(hasattr(db, 'dbname'))
        self.assertEqual(db.dbname, 'SimplePooledPgTestDB')
        self.assertTrue(hasattr(db, 'user'))
        self.assertEqual(db.user, 'SimplePooledPgTestUser')
        self.assertEqual(db.num_queries, 1)
        db.query('select 1')
        self.assertEqual(db.num_queries, 2)

    def test3_two_connections(self):
        dbpool = self.my_dbpool(2)
        db1 = dbpool.connection()
        for i in range(5):
            db1.query('select 1')
        db2 = dbpool.connection()
        self.assertNotEqual(db1, db2)
        self.assertNotEqual(db1._con, db2._con)
        for i in range(7):
            db2.query('select 1')
        self.assertEqual(db1.num_queries, 5)
        self.assertEqual(db2.num_queries, 7)
        db1.close()
        db1 = dbpool.connection()
        self.assertNotEqual(db1, db2)
        self.assertNotEqual(db1._con, db2._con)
        self.assertTrue(hasattr(db1, 'query'))
        for i in range(3):
            db1.query('select 1')
        self.assertEqual(db1.num_queries, 8)
        db2.query('select 1')
        self.assertEqual(db2.num_queries, 8)

    def test4_threads(self):
        dbpool = self.my_dbpool(2)
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


if __name__ == '__main__':
    unittest.main()
