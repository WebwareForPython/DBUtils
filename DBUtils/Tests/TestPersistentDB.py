"""Test the PersistentDB module.

Note:
We don't test performance here, so the test does not predicate
whether PersistentDB actually will help in improving performance or not.
We also assume that the underlying SteadyDB connections are tested.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke

"""

import unittest

import DBUtils.Tests.mock_db as dbapi

from DBUtils.PersistentDB import PersistentDB, local

__version__ = '1.3'


class TestPersistentDB(unittest.TestCase):

    def setUp(self):
        dbapi.threadsafety = 1

    def test0_CheckVersion(self):
        from DBUtils import __version__ as DBUtilsVersion
        self.assertEqual(DBUtilsVersion, __version__)
        from DBUtils.PersistentDB import __version__ as PersistentDBVersion
        self.assertEqual(PersistentDBVersion, __version__)
        self.assertEqual(PersistentDB.version, __version__)

    def test1_NoThreadsafety(self):
        from DBUtils.PersistentDB import NotSupportedError
        for dbapi.threadsafety in (None, 0):
            self.assertRaises(NotSupportedError, PersistentDB, dbapi)

    def test2_Close(self):
        for closeable in (False, True):
            persist = PersistentDB(dbapi, closeable=closeable)
            db = persist.connection()
            self.assertTrue(db._con.valid)
            db.close()
            self.assertTrue(closeable ^ db._con.valid)
            db.close()
            self.assertTrue(closeable ^ db._con.valid)
            db._close()
            self.assertTrue(not db._con.valid)
            db._close()
            self.assertTrue(not db._con.valid)

    def test3_Connection(self):
        persist = PersistentDB(dbapi)
        db = persist.connection()
        db_con = db._con
        self.assertTrue(db_con.database is None)
        self.assertTrue(db_con.user is None)
        db2 = persist.connection()
        self.assertEqual(db, db2)
        db3 = persist.dedicated_connection()
        self.assertEqual(db, db3)
        db3.close()
        db2.close()
        db.close()

    def test4_Threads(self):
        numThreads = 3
        persist = PersistentDB(dbapi, closeable=True)
        try:
            from queue import Queue, Empty
        except ImportError:  # Python 2
            from Queue import Queue, Empty
        queryQueue, resultQueue = [], []
        for i in range(numThreads):
            queryQueue.append(Queue(1))
            resultQueue.append(Queue(1))

        def runQueries(i):
            this_db = persist.connection()
            while 1:
                try:
                    try:
                        q = queryQueue[i].get(1, 1)
                    except TypeError:
                        q = queryQueue[i].get(1)
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
                    resultQueue[i].put(r, 1, 1)
                except TypeError:
                    resultQueue[i].put(r, 1)
            db.close()

        from threading import Thread
        threads = []
        for i in range(numThreads):
            thread = Thread(target=runQueries, args=(i,))
            threads.append(thread)
            thread.start()
        for i in range(numThreads):
            try:
                queryQueue[i].put('ping', 1, 1)
            except TypeError:
                queryQueue[i].put('ping', 1)
        for i in range(numThreads):
            try:
                r = resultQueue[i].get(1, 1)
            except TypeError:
                r = resultQueue[i].get(1)
            self.assertEqual(r, '%d(0): ok - thread alive' % i)
            self.assertTrue(threads[i].isAlive())
        for i in range(numThreads):
            for j in range(i + 1):
                try:
                    queryQueue[i].put('select test%d' % j, 1, 1)
                    r = resultQueue[i].get(1, 1)
                except TypeError:
                    queryQueue[i].put('select test%d' % j, 1)
                    r = resultQueue[i].get(1)
                self.assertEqual(r, '%d(%d): test%d' % (i, j + 1, j))
        try:
            queryQueue[1].put('select test4', 1, 1)
        except TypeError:
            queryQueue[1].put('select test4', 1)
        try:
            r = resultQueue[1].get(1, 1)
        except TypeError:
            r = resultQueue[1].get(1)
        self.assertEqual(r, '1(3): test4')
        try:
            queryQueue[1].put('close', 1, 1)
            r = resultQueue[1].get(1, 1)
        except TypeError:
            queryQueue[1].put('close', 1)
            r = resultQueue[1].get(1)
        self.assertEqual(r, '1(3): ok - connection closed')
        for j in range(2):
            try:
                queryQueue[1].put('select test%d' % j, 1, 1)
                r = resultQueue[1].get(1, 1)
            except TypeError:
                queryQueue[1].put('select test%d' % j, 1)
                r = resultQueue[1].get(1)
            self.assertEqual(r, '1(%d): test%d' % (j + 1, j))
        for i in range(numThreads):
            self.assertTrue(threads[i].isAlive())
            try:
                queryQueue[i].put('ping', 1, 1)
            except TypeError:
                queryQueue[i].put('ping', 1)
        for i in range(numThreads):
            try:
                r = resultQueue[i].get(1, 1)
            except TypeError:
                r = resultQueue[i].get(1)
            self.assertEqual(r, '%d(%d): ok - thread alive' % (i, i + 1))
            self.assertTrue(threads[i].isAlive())
        for i in range(numThreads):
            try:
                queryQueue[i].put(None, 1, 1)
            except TypeError:
                queryQueue[i].put(None, 1)

    def test5_MaxUsage(self):
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

    def test6_SetSession(self):
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

    def test7_ThreadLocal(self):
        persist = PersistentDB(dbapi)
        self.assertTrue(isinstance(persist.thread, local))

        class threadlocal:
            pass

        persist = PersistentDB(dbapi, threadlocal=threadlocal)
        self.assertTrue(isinstance(persist.thread, threadlocal))

    def test8_PingCheck(self):
        Connection = dbapi.Connection
        Connection.has_ping = True
        Connection.num_pings = 0
        persist = PersistentDB(dbapi, 0, None, None, 0, True)
        db = persist.connection()
        self.assertTrue(db._con.valid)
        self.assertEqual(Connection.num_pings, 0)
        db.close()
        db = persist.connection()
        self.assertTrue(not db._con.valid)
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
        self.assertTrue(not db._con.valid)
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
        self.assertTrue(not db._con.valid)
        self.assertEqual(Connection.num_pings, 3)
        cursor = db.cursor()
        db._con.close()
        self.assertTrue(not db._con.valid)
        self.assertEqual(Connection.num_pings, 3)
        cursor.execute('select test')
        self.assertTrue(db._con.valid)
        self.assertEqual(Connection.num_pings, 4)
        Connection.has_ping = False
        Connection.num_pings = 0

    def test9_FailedTransaction(self):
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


if __name__ == '__main__':
    unittest.main()
