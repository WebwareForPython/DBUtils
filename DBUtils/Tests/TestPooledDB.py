"""Test the PooledDB module.

Note:
We don't test performance here, so the test does not predicate
whether PooledDB actually will help in improving performance or not.
We also assume that the underlying SteadyDB connections are tested.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke

"""

import unittest

import DBUtils.Tests.mock_db as dbapi

from DBUtils.PooledDB import (
    PooledDB, SharedDBConnection, InvalidConnection, TooManyConnections)

__version__ = '1.3'


class TestPooledDB(unittest.TestCase):

    def test00_CheckVersion(self):
        from DBUtils import __version__ as DBUtilsVersion
        self.assertEqual(DBUtilsVersion, __version__)
        from DBUtils.PooledDB import __version__ as PooledDBVersion
        self.assertEqual(PooledDBVersion, __version__)
        self.assertEqual(PooledDB.version, __version__)

    def test01_NoThreadsafety(self):
        from DBUtils.PooledDB import NotSupportedError
        for threadsafety in (None, 0):
            dbapi.threadsafety = threadsafety
            self.assertRaises(NotSupportedError, PooledDB, dbapi)

    def test02_Threadsafety(self):
        for threadsafety in (1, 2, 3):
            dbapi.threadsafety = threadsafety
            pool = PooledDB(dbapi, 0, 0, 1)
            self.assertTrue(hasattr(pool, '_maxshared'))
            if threadsafety > 1:
                self.assertEqual(pool._maxshared, 1)
                self.assertTrue(hasattr(pool, '_shared_cache'))
            else:
                self.assertEqual(pool._maxshared, 0)
                self.assertTrue(not hasattr(pool, '_shared_cache'))

    def test03_CreateConnection(self):
        for threadsafety in (1, 2):
            dbapi.threadsafety = threadsafety
            shareable = threadsafety > 1
            pool = PooledDB(
                dbapi, 1, 1, 1, 0, False, None, None, True, None, None,
                'PooledDBTestDB', user='PooledDBTestUser')
            self.assertTrue(hasattr(pool, '_idle_cache'))
            self.assertEqual(len(pool._idle_cache), 1)
            if shareable:
                self.assertTrue(hasattr(pool, '_shared_cache'))
                self.assertEqual(len(pool._shared_cache), 0)
            else:
                self.assertTrue(not hasattr(pool, '_shared_cache'))
            self.assertTrue(hasattr(pool, '_maxusage'))
            self.assertEqual(pool._maxusage, None)
            self.assertTrue(hasattr(pool, '_setsession'))
            self.assertTrue(pool._setsession is None)
            con = pool._idle_cache[0]
            from DBUtils.SteadyDB import SteadyDBConnection
            self.assertTrue(isinstance(con, SteadyDBConnection))
            self.assertTrue(hasattr(con, '_maxusage'))
            self.assertEqual(con._maxusage, 0)
            self.assertTrue(hasattr(con, '_setsession_sql'))
            self.assertTrue(con._setsession_sql is None)
            db = pool.connection()
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 1)
            self.assertTrue(hasattr(db, '_con'))
            self.assertEqual(db._con, con)
            self.assertTrue(hasattr(db, 'cursor'))
            self.assertTrue(hasattr(db, '_usage'))
            self.assertEqual(db._usage, 0)
            self.assertTrue(hasattr(con, '_con'))
            db_con = con._con
            self.assertTrue(hasattr(db_con, 'database'))
            self.assertEqual(db_con.database, 'PooledDBTestDB')
            self.assertTrue(hasattr(db_con, 'user'))
            self.assertEqual(db_con.user, 'PooledDBTestUser')
            self.assertTrue(hasattr(db_con, 'open_cursors'))
            self.assertEqual(db_con.open_cursors, 0)
            self.assertTrue(hasattr(db_con, 'num_uses'))
            self.assertEqual(db_con.num_uses, 0)
            self.assertTrue(hasattr(db_con, 'num_queries'))
            self.assertEqual(db_con.num_queries, 0)
            cursor = db.cursor()
            self.assertEqual(db_con.open_cursors, 1)
            cursor.execute('select test')
            r = cursor.fetchone()
            cursor.close()
            self.assertEqual(db_con.open_cursors, 0)
            self.assertEqual(r, 'test')
            self.assertEqual(db_con.num_queries, 1)
            self.assertEqual(db._usage, 1)
            cursor = db.cursor()
            self.assertEqual(db_con.open_cursors, 1)
            cursor.execute('set sessiontest')
            cursor2 = db.cursor()
            self.assertEqual(db_con.open_cursors, 2)
            cursor2.close()
            self.assertEqual(db_con.open_cursors, 1)
            cursor.close()
            self.assertEqual(db_con.open_cursors, 0)
            self.assertEqual(db_con.num_queries, 1)
            self.assertEqual(db._usage, 2)
            self.assertEqual(
                db_con.session, ['rollback', 'sessiontest'])
            pool = PooledDB(dbapi, 1, 1, 1)
            self.assertEqual(len(pool._idle_cache), 1)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            db = pool.connection()
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 1)
            db.close()
            self.assertEqual(len(pool._idle_cache), 1)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            db = pool.connection(True)
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 1)
            db.close()
            self.assertEqual(len(pool._idle_cache), 1)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            db = pool.connection(False)
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            self.assertEqual(db._usage, 0)
            db_con = db._con._con
            self.assertTrue(db_con.database is None)
            self.assertTrue(db_con.user is None)
            db.close()
            self.assertEqual(len(pool._idle_cache), 1)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            db = pool.dedicated_connection()
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            self.assertEqual(db._usage, 0)
            db_con = db._con._con
            self.assertTrue(db_con.database is None)
            self.assertTrue(db_con.user is None)
            db.close()
            self.assertEqual(len(pool._idle_cache), 1)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            pool = PooledDB(dbapi, 0, 0, 0, 0, False, 3, ('set datestyle',))
            self.assertEqual(pool._maxusage, 3)
            self.assertEqual(pool._setsession, ('set datestyle',))
            con = pool.connection()._con
            self.assertEqual(con._maxusage, 3)
            self.assertEqual(con._setsession_sql, ('set datestyle',))

    def test04_CloseConnection(self):
        for threadsafety in (1, 2):
            dbapi.threadsafety = threadsafety
            shareable = threadsafety > 1
            pool = PooledDB(
                dbapi, 0, 1, 1, 0, False, None, None, True, None, None,
                'PooledDBTestDB', user='PooledDBTestUser')
            self.assertTrue(hasattr(pool, '_idle_cache'))
            self.assertEqual(len(pool._idle_cache), 0)
            db = pool.connection()
            self.assertTrue(hasattr(db, '_con'))
            con = db._con
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 1)
                self.assertTrue(hasattr(db, '_shared_con'))
                shared_con = db._shared_con
                self.assertEqual(pool._shared_cache[0], shared_con)
                self.assertTrue(hasattr(shared_con, 'shared'))
                self.assertEqual(shared_con.shared, 1)
                self.assertTrue(hasattr(shared_con, 'con'))
                self.assertEqual(shared_con.con, con)
            from DBUtils.SteadyDB import SteadyDBConnection
            self.assertTrue(isinstance(con, SteadyDBConnection))
            self.assertTrue(hasattr(con, '_con'))
            db_con = con._con
            self.assertTrue(hasattr(db_con, 'num_queries'))
            self.assertEqual(db._usage, 0)
            self.assertEqual(db_con.num_queries, 0)
            db.cursor().execute('select test')
            self.assertEqual(db._usage, 1)
            self.assertEqual(db_con.num_queries, 1)
            db.close()
            self.assertEqual(db._con, None)
            if shareable:
                self.assertEqual(db._shared_con, None)
                self.assertEqual(shared_con.shared, 0)
            self.assertRaises(InvalidConnection, getattr, db, '_usage')
            self.assertTrue(not hasattr(db_con, '_num_queries'))
            self.assertEqual(len(pool._idle_cache), 1)
            self.assertEqual(pool._idle_cache[0]._con, db_con)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            db.close()
            if shareable:
                self.assertEqual(shared_con.shared, 0)
            db = pool.connection()
            self.assertEqual(db._con, con)
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 1)
                shared_con = db._shared_con
                self.assertEqual(pool._shared_cache[0], shared_con)
                self.assertEqual(shared_con.con, con)
                self.assertEqual(shared_con.shared, 1)
            self.assertEqual(db._usage, 1)
            self.assertEqual(db_con.num_queries, 1)
            self.assertTrue(hasattr(db_con, 'database'))
            self.assertEqual(db_con.database, 'PooledDBTestDB')
            self.assertTrue(hasattr(db_con, 'user'))
            self.assertEqual(db_con.user, 'PooledDBTestUser')
            db.cursor().execute('select test')
            self.assertEqual(db_con.num_queries, 2)
            db.cursor().execute('select test')
            self.assertEqual(db_con.num_queries, 3)
            db.close()
            self.assertEqual(len(pool._idle_cache), 1)
            self.assertEqual(pool._idle_cache[0]._con, db_con)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            db = pool.connection(False)
            self.assertEqual(db._con, con)
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            db.close()
            self.assertEqual(len(pool._idle_cache), 1)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)

    def test05_CloseAll(self):
        for threadsafety in (1, 2):
            dbapi.threadsafety = threadsafety
            shareable = threadsafety > 1
            pool = PooledDB(dbapi, 10)
            self.assertEqual(len(pool._idle_cache), 10)
            pool.close()
            self.assertEqual(len(pool._idle_cache), 0)
            pool = PooledDB(dbapi, 10)
            closed = ['no']

            def close(what=closed):
                what[0] = 'yes'

            pool._idle_cache[7]._con.close = close
            self.assertEqual(closed, ['no'])
            del pool
            self.assertEqual(closed, ['yes'])
            pool = PooledDB(dbapi, 10, 10, 5)
            self.assertEqual(len(pool._idle_cache), 10)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            cache = []
            for i in range(5):
                cache.append(pool.connection())
            self.assertEqual(len(pool._idle_cache), 5)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 5)
            else:
                self.assertEqual(len(pool._idle_cache), 5)
            pool.close()
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            pool = PooledDB(dbapi, 10, 10, 5)
            closed = []

            def close_idle(what=closed):
                what.append('idle')

            def close_shared(what=closed):
                what.append('shared')

            if shareable:
                cache = []
                for i in range(5):
                    cache.append(pool.connection())
                pool._shared_cache[3].con.close = close_shared
            else:
                pool._idle_cache[7]._con.close = close_shared
            pool._idle_cache[3]._con.close = close_idle
            self.assertEqual(closed, [])
            del pool
            if shareable:
                del cache
            self.assertEqual(closed, ['idle', 'shared'])

    def test06_ShareableConnection(self):
        for threadsafety in (1, 2):
            dbapi.threadsafety = threadsafety
            shareable = threadsafety > 1
            pool = PooledDB(dbapi, 0, 1, 2)
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            db1 = pool.connection()
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 1)
            db2 = pool.connection()
            self.assertNotEqual(db1._con, db2._con)
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 2)
            db3 = pool.connection()
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 2)
                self.assertEqual(db3._con, db1._con)
                self.assertEqual(db1._shared_con.shared, 2)
                self.assertEqual(db2._shared_con.shared, 1)
            else:
                self.assertNotEqual(db3._con, db1._con)
                self.assertNotEqual(db3._con, db2._con)
            db4 = pool.connection()
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 2)
                self.assertEqual(db4._con, db2._con)
                self.assertEqual(db1._shared_con.shared, 2)
                self.assertEqual(db2._shared_con.shared, 2)
            else:
                self.assertNotEqual(db4._con, db1._con)
                self.assertNotEqual(db4._con, db2._con)
                self.assertNotEqual(db4._con, db3._con)
            db5 = pool.connection(False)
            self.assertNotEqual(db5._con, db1._con)
            self.assertNotEqual(db5._con, db2._con)
            self.assertNotEqual(db5._con, db3._con)
            self.assertNotEqual(db5._con, db4._con)
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 2)
                self.assertEqual(db1._shared_con.shared, 2)
                self.assertEqual(db2._shared_con.shared, 2)
            db5.close()
            self.assertEqual(len(pool._idle_cache), 1)
            db5 = pool.connection()
            if shareable:
                self.assertEqual(len(pool._idle_cache), 1)
                self.assertEqual(len(pool._shared_cache), 2)
                self.assertEqual(db5._shared_con.shared, 3)
            else:
                self.assertEqual(len(pool._idle_cache), 0)
            pool = PooledDB(dbapi, 0, 0, 1)
            self.assertEqual(len(pool._idle_cache), 0)
            db1 = pool.connection(False)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            db2 = pool.connection()
            if shareable:
                self.assertEqual(len(pool._shared_cache), 1)
            db3 = pool.connection()
            if shareable:
                self.assertEqual(len(pool._shared_cache), 1)
                self.assertEqual(db2._con, db3._con)
            else:
                self.assertNotEqual(db2._con, db3._con)
            del db3
            if shareable:
                self.assertEqual(len(pool._idle_cache), 0)
                self.assertEqual(len(pool._shared_cache), 1)
            else:
                self.assertEqual(len(pool._idle_cache), 1)
            del db2
            if shareable:
                self.assertEqual(len(pool._idle_cache), 1)
                self.assertEqual(len(pool._shared_cache), 0)
            else:
                self.assertEqual(len(pool._idle_cache), 2)
            del db1
            if shareable:
                self.assertEqual(len(pool._idle_cache), 2)
                self.assertEqual(len(pool._shared_cache), 0)
            else:
                self.assertEqual(len(pool._idle_cache), 3)

    def test08_MinMaxCached(self):
        for threadsafety in (1, 2):
            dbapi.threadsafety = threadsafety
            shareable = threadsafety > 1
            pool = PooledDB(dbapi, 3)
            self.assertEqual(len(pool._idle_cache), 3)
            cache = [pool.connection() for i in range(3)]
            self.assertEqual(len(pool._idle_cache), 0)
            del cache
            self.assertEqual(len(pool._idle_cache), 3)
            cache = [pool.connection() for i in range(6)]
            self.assertEqual(len(pool._idle_cache), 0)
            del cache
            self.assertEqual(len(pool._idle_cache), 6)
            pool = PooledDB(dbapi, 0, 3)
            self.assertEqual(len(pool._idle_cache), 0)
            cache = [pool.connection() for i in range(3)]
            self.assertEqual(len(pool._idle_cache), 0)
            del cache
            self.assertEqual(len(pool._idle_cache), 3)
            cache = [pool.connection() for i in range(6)]
            self.assertEqual(len(pool._idle_cache), 0)
            del cache
            self.assertEqual(len(pool._idle_cache), 3)
            pool = PooledDB(dbapi, 3, 3)
            self.assertEqual(len(pool._idle_cache), 3)
            cache = [pool.connection() for i in range(3)]
            self.assertEqual(len(pool._idle_cache), 0)
            del cache
            self.assertEqual(len(pool._idle_cache), 3)
            cache = [pool.connection() for i in range(6)]
            self.assertEqual(len(pool._idle_cache), 0)
            del cache
            self.assertEqual(len(pool._idle_cache), 3)
            pool = PooledDB(dbapi, 3, 2)
            self.assertEqual(len(pool._idle_cache), 3)
            cache = [pool.connection() for i in range(4)]
            self.assertEqual(len(pool._idle_cache), 0)
            del cache
            self.assertEqual(len(pool._idle_cache), 3)
            pool = PooledDB(dbapi, 2, 5)
            self.assertEqual(len(pool._idle_cache), 2)
            cache = [pool.connection() for i in range(10)]
            self.assertEqual(len(pool._idle_cache), 0)
            del cache
            self.assertEqual(len(pool._idle_cache), 5)
            pool = PooledDB(dbapi, 1, 2, 3)
            self.assertEqual(len(pool._idle_cache), 1)
            cache = [pool.connection(False) for i in range(4)]
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            del cache
            self.assertEqual(len(pool._idle_cache), 2)
            cache = [pool.connection() for i in range(10)]
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 3)
            del cache
            self.assertEqual(len(pool._idle_cache), 2)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            pool = PooledDB(dbapi, 1, 3, 2)
            self.assertEqual(len(pool._idle_cache), 1)
            cache = [pool.connection(False) for i in range(4)]
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            del cache
            self.assertEqual(len(pool._idle_cache), 3)
            cache = [pool.connection() for i in range(10)]
            if shareable:
                self.assertEqual(len(pool._idle_cache), 1)
                self.assertEqual(len(pool._shared_cache), 2)
            else:
                self.assertEqual(len(pool._idle_cache), 0)
            del cache
            self.assertEqual(len(pool._idle_cache), 3)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)

    def test08_MaxShared(self):
        for threadsafety in (1, 2):
            dbapi.threadsafety = threadsafety
            shareable = threadsafety > 1
            pool = PooledDB(dbapi)
            self.assertEqual(len(pool._idle_cache), 0)
            cache = [pool.connection() for i in range(10)]
            self.assertEqual(len(cache), 10)
            self.assertEqual(len(pool._idle_cache), 0)
            pool = PooledDB(dbapi, 1, 1, 0)
            self.assertEqual(len(pool._idle_cache), 1)
            cache = [pool.connection() for i in range(10)]
            self.assertEqual(len(cache), 10)
            self.assertEqual(len(pool._idle_cache), 0)
            pool = PooledDB(dbapi, 0, 0, 1)
            cache = [pool.connection() for i in range(10)]
            self.assertEqual(len(cache), 10)
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 1)
            pool = PooledDB(dbapi, 1, 1, 1)
            self.assertEqual(len(pool._idle_cache), 1)
            cache = [pool.connection() for i in range(10)]
            self.assertEqual(len(cache), 10)
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 1)
            pool = PooledDB(dbapi, 0, 0, 7)
            cache = [pool.connection(False) for i in range(3)]
            self.assertEqual(len(cache), 3)
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            cache = [pool.connection() for i in range(10)]
            self.assertEqual(len(cache), 10)
            self.assertEqual(len(pool._idle_cache), 3)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 7)

    def test09_SortShared(self):
        dbapi.threadsafety = 2
        pool = PooledDB(dbapi, 0, 4, 4)
        cache = []
        for i in range(6):
            db = pool.connection()
            db.cursor().execute('select test')
            cache.append(db)
        for i, db in enumerate(cache):
            self.assertEqual(db._shared_con.shared, 1 if 2 <= i < 4 else 2)
        cache[2].begin()
        cache[3].begin()
        db = pool.connection()
        self.assertTrue(db._con is cache[0]._con)
        db.close()
        cache[3].rollback()
        db = pool.connection()
        self.assertTrue(db._con is cache[3]._con)

    def test10_EquallyShared(self):
        for threadsafety in (1, 2):
            dbapi.threadsafety = threadsafety
            shareable = threadsafety > 1
            pool = PooledDB(dbapi, 5, 5, 5)
            self.assertEqual(len(pool._idle_cache), 5)
            for i in range(15):
                db = pool.connection(False)
                db.cursor().execute('select test')
                db.close()
            self.assertEqual(len(pool._idle_cache), 5)
            for i in range(5):
                con = pool._idle_cache[i]
                self.assertEqual(con._usage, 3)
                self.assertEqual(con._con.num_queries, 3)
            cache = []
            for i in range(35):
                db = pool.connection()
                db.cursor().execute('select test')
                cache.append(db)
                del db
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 5)
                for i in range(5):
                    con = pool._shared_cache[i]
                    self.assertEqual(con.shared, 7)
                    con = con.con
                    self.assertEqual(con._usage, 10)
                    self.assertEqual(con._con.num_queries, 10)
            del cache
            self.assertEqual(len(pool._idle_cache), 5)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)

    def test11_ManyShared(self):
        for threadsafety in (1, 2):
            dbapi.threadsafety = threadsafety
            shareable = threadsafety > 1
            pool = PooledDB(dbapi, 0, 0, 5)
            cache = []
            for i in range(35):
                db = pool.connection()
                db.cursor().execute('select test1')
                db.cursor().execute('select test2')
                db.cursor().callproc('test3')
                cache.append(db)
                del db
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 5)
                for i in range(5):
                    con = pool._shared_cache[i]
                    self.assertEqual(con.shared, 7)
                    con = con.con
                    self.assertEqual(con._usage, 21)
                    self.assertEqual(con._con.num_queries, 14)
                cache[3] = cache[8] = cache[33] = None
                cache[12] = cache[17] = cache[34] = None
                self.assertEqual(len(pool._shared_cache), 5)
                self.assertEqual(pool._shared_cache[0].shared, 7)
                self.assertEqual(pool._shared_cache[1].shared, 7)
                self.assertEqual(pool._shared_cache[2].shared, 5)
                self.assertEqual(pool._shared_cache[3].shared, 4)
                self.assertEqual(pool._shared_cache[4].shared, 6)
                for db in cache:
                    if db:
                        db.cursor().callproc('test4')
                for i in range(6):
                    db = pool.connection()
                    db.cursor().callproc('test4')
                    cache.append(db)
                    del db
                for i in range(5):
                    con = pool._shared_cache[i]
                    self.assertEqual(con.shared, 7)
                    con = con.con
                    self.assertEqual(con._usage, 28)
                    self.assertEqual(con._con.num_queries, 14)
            del cache
            if shareable:
                self.assertEqual(len(pool._idle_cache), 5)
                self.assertEqual(len(pool._shared_cache), 0)
            else:
                self.assertEqual(len(pool._idle_cache), 35)

    def test12_Rollback(self):
        for threadsafety in (1, 2):
            dbapi.threadsafety = threadsafety
            pool = PooledDB(dbapi, 0, 1)
            self.assertEqual(len(pool._idle_cache), 0)
            db = pool.connection(False)
            self.assertEqual(len(pool._idle_cache), 0)
            self.assertEqual(db._con._con.open_cursors, 0)
            cursor = db.cursor()
            self.assertEqual(db._con._con.open_cursors, 1)
            cursor.execute('set doit1')
            db.commit()
            cursor.execute('set dont1')
            cursor.close()
            self.assertEqual(db._con._con.open_cursors, 0)
            del db
            self.assertEqual(len(pool._idle_cache), 1)
            db = pool.connection(False)
            self.assertEqual(len(pool._idle_cache), 0)
            self.assertEqual(db._con._con.open_cursors, 0)
            cursor = db.cursor()
            self.assertEqual(db._con._con.open_cursors, 1)
            cursor.execute('set doit2')
            cursor.close()
            self.assertEqual(db._con._con.open_cursors, 0)
            db.commit()
            session = db._con._con.session
            db.close()
            self.assertEqual(session, [
                'doit1', 'commit', 'dont1', 'rollback',
                'doit2', 'commit', 'rollback'])

    def test13_MaxConnections(self):
        for threadsafety in (1, 2):
            dbapi.threadsafety = threadsafety
            shareable = threadsafety > 1
            pool = PooledDB(dbapi, 1, 2, 2, 3)
            self.assertTrue(hasattr(pool, '_maxconnections'))
            self.assertEqual(pool._maxconnections, 3)
            self.assertTrue(hasattr(pool, '_connections'))
            self.assertEqual(pool._connections, 0)
            self.assertEqual(len(pool._idle_cache), 1)
            cache = []
            for i in range(3):
                cache.append(pool.connection(False))
            self.assertEqual(pool._connections, 3)
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            self.assertRaises(TooManyConnections, pool.connection, 0)
            self.assertRaises(TooManyConnections, pool.connection)
            cache = []
            self.assertEqual(pool._connections, 0)
            self.assertEqual(len(pool._idle_cache), 2)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            for i in range(3):
                cache.append(pool.connection())
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(pool._connections, 2)
                self.assertEqual(len(pool._shared_cache), 2)
                cache.append(pool.connection(False))
                self.assertEqual(pool._connections, 3)
                self.assertEqual(len(pool._shared_cache), 2)
            else:
                self.assertEqual(pool._connections, 3)
            self.assertRaises(TooManyConnections, pool.connection, 0)
            if shareable:
                cache.append(pool.connection(True))
                self.assertEqual(pool._connections, 3)
            else:
                self.assertRaises(TooManyConnections, pool.connection)
            del cache
            self.assertEqual(pool._connections, 0)
            self.assertEqual(len(pool._idle_cache), 2)
            pool = PooledDB(dbapi, 0, 1, 1, 1)
            self.assertEqual(pool._maxconnections, 1)
            self.assertEqual(pool._connections, 0)
            self.assertEqual(len(pool._idle_cache), 0)
            db = pool.connection(False)
            self.assertEqual(pool._connections, 1)
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            self.assertRaises(TooManyConnections, pool.connection, 0)
            self.assertRaises(TooManyConnections, pool.connection)
            del db
            self.assertEqual(pool._connections, 0)
            self.assertEqual(len(pool._idle_cache), 1)
            cache = [pool.connection()]
            self.assertEqual(pool._connections, 1)
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 1)
                cache.append(pool.connection())
                self.assertEqual(pool._connections, 1)
                self.assertEqual(len(pool._shared_cache), 1)
                self.assertEqual(pool._shared_cache[0].shared, 2)
            else:
                self.assertRaises(TooManyConnections, pool.connection)
            self.assertRaises(TooManyConnections, pool.connection, 0)
            if shareable:
                cache.append(pool.connection(True))
                self.assertEqual(pool._connections, 1)
                self.assertEqual(len(pool._shared_cache), 1)
                self.assertEqual(pool._shared_cache[0].shared, 3)
            else:
                self.assertRaises(TooManyConnections, pool.connection, 1)
            del cache
            self.assertEqual(pool._connections, 0)
            self.assertEqual(len(pool._idle_cache), 1)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            db = pool.connection(False)
            self.assertEqual(pool._connections, 1)
            self.assertEqual(len(pool._idle_cache), 0)
            del db
            self.assertEqual(pool._connections, 0)
            self.assertEqual(len(pool._idle_cache), 1)
            pool = PooledDB(dbapi, 1, 2, 2, 1)
            self.assertEqual(pool._maxconnections, 2)
            self.assertEqual(pool._connections, 0)
            self.assertEqual(len(pool._idle_cache), 1)
            cache = []
            cache.append(pool.connection(False))
            self.assertEqual(pool._connections, 1)
            self.assertEqual(len(pool._idle_cache), 0)
            cache.append(pool.connection(False))
            self.assertEqual(pool._connections, 2)
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            self.assertRaises(TooManyConnections, pool.connection, 0)
            self.assertRaises(TooManyConnections, pool.connection)
            pool = PooledDB(dbapi, 4, 3, 2, 1, False)
            self.assertEqual(pool._maxconnections, 4)
            self.assertEqual(pool._connections, 0)
            self.assertEqual(len(pool._idle_cache), 4)
            cache = []
            for i in range(4):
                cache.append(pool.connection(False))
            self.assertEqual(pool._connections, 4)
            self.assertEqual(len(pool._idle_cache), 0)
            self.assertRaises(TooManyConnections, pool.connection, 0)
            self.assertRaises(TooManyConnections, pool.connection)
            pool = PooledDB(dbapi, 1, 2, 3, 4, False)
            self.assertEqual(pool._maxconnections, 4)
            self.assertEqual(pool._connections, 0)
            self.assertEqual(len(pool._idle_cache), 1)
            for i in range(4):
                cache.append(pool.connection())
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(pool._connections, 3)
                self.assertEqual(len(pool._shared_cache), 3)
                cache.append(pool.connection())
                self.assertEqual(pool._connections, 3)
                cache.append(pool.connection(False))
                self.assertEqual(pool._connections, 4)
            else:
                self.assertEqual(pool._connections, 4)
                self.assertRaises(TooManyConnections, pool.connection)
            self.assertRaises(TooManyConnections, pool.connection, 0)
            pool = PooledDB(dbapi, 0, 0, 3, 3, False)
            self.assertEqual(pool._maxconnections, 3)
            self.assertEqual(pool._connections, 0)
            cache = []
            for i in range(3):
                cache.append(pool.connection(False))
            self.assertEqual(pool._connections, 3)
            self.assertRaises(TooManyConnections, pool.connection, 0)
            self.assertRaises(TooManyConnections, pool.connection, 1)
            cache = []
            self.assertEqual(pool._connections, 0)
            for i in range(3):
                cache.append(pool.connection())
            self.assertEqual(pool._connections, 3)
            if shareable:
                for i in range(3):
                    cache.append(pool.connection())
                self.assertEqual(pool._connections, 3)
            else:
                self.assertRaises(TooManyConnections, pool.connection)
            self.assertRaises(TooManyConnections, pool.connection, 0)
            pool = PooledDB(dbapi, 0, 0, 3)
            self.assertEqual(pool._maxconnections, 0)
            self.assertEqual(pool._connections, 0)
            cache = []
            for i in range(10):
                cache.append(pool.connection(False))
                cache.append(pool.connection())
            if shareable:
                self.assertEqual(pool._connections, 13)
                self.assertEqual(len(pool._shared_cache), 3)
            else:
                self.assertEqual(pool._connections, 20)
            pool = PooledDB(dbapi, 1, 1, 1, 1, True)
            self.assertEqual(pool._maxconnections, 1)
            self.assertEqual(pool._connections, 0)
            self.assertEqual(len(pool._idle_cache), 1)
            db = pool.connection(False)
            self.assertEqual(pool._connections, 1)
            self.assertEqual(len(pool._idle_cache), 0)

            def connection():
                db = pool.connection()
                cursor = db.cursor()
                cursor.execute('set thread')
                cursor.close()
                db.close()

            from threading import Thread
            thread = Thread(target=connection)
            thread.start()
            thread.join(0.1)
            self.assertTrue(thread.isAlive())
            self.assertEqual(pool._connections, 1)
            self.assertEqual(len(pool._idle_cache), 0)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            session = db._con._con.session
            self.assertEqual(session, ['rollback'])
            del db
            thread.join(0.1)
            self.assertTrue(not thread.isAlive())
            self.assertEqual(pool._connections, 0)
            self.assertEqual(len(pool._idle_cache), 1)
            if shareable:
                self.assertEqual(len(pool._shared_cache), 0)
            db = pool.connection(False)
            self.assertEqual(pool._connections, 1)
            self.assertEqual(len(pool._idle_cache), 0)
            self.assertEqual(
                session, ['rollback', 'rollback', 'thread', 'rollback'])
            del db

    def test14_MaxUsage(self):
        for threadsafety in (1, 2):
            dbapi.threadsafety = threadsafety
            for maxusage in (0, 3, 7):
                pool = PooledDB(dbapi, 0, 0, 0, 1, False, maxusage)
                self.assertEqual(pool._maxusage, maxusage)
                self.assertEqual(len(pool._idle_cache), 0)
                db = pool.connection(False)
                self.assertEqual(db._con._maxusage, maxusage)
                self.assertEqual(len(pool._idle_cache), 0)
                self.assertEqual(db._con._con.open_cursors, 0)
                self.assertEqual(db._usage, 0)
                self.assertEqual(db._con._con.num_uses, 0)
                self.assertEqual(db._con._con.num_queries, 0)
                for i in range(20):
                    cursor = db.cursor()
                    self.assertEqual(db._con._con.open_cursors, 1)
                    cursor.execute('select test%i' % i)
                    r = cursor.fetchone()
                    self.assertEqual(r, 'test%i' % i)
                    cursor.close()
                    self.assertEqual(db._con._con.open_cursors, 0)
                    if maxusage:
                        j = i % maxusage + 1
                    else:
                        j = i + 1
                    self.assertEqual(db._usage, j)
                    self.assertEqual(db._con._con.num_uses, j)
                    self.assertEqual(db._con._con.num_queries, j)
                db.cursor().callproc('test')
                self.assertEqual(db._con._con.open_cursors, 0)
                self.assertEqual(db._usage, j + 1)
                self.assertEqual(db._con._con.num_uses, j + 1)
                self.assertEqual(db._con._con.num_queries, j)

    def test15_SetSession(self):
        for threadsafety in (1, 2):
            dbapi.threadsafety = threadsafety
            setsession = ('set time zone', 'set datestyle')
            pool = PooledDB(dbapi, 0, 0, 0, 1, False, None, setsession)
            self.assertEqual(pool._setsession, setsession)
            db = pool.connection(False)
            self.assertEqual(db._setsession_sql, setsession)
            self.assertEqual(
                db._con._con.session, ['time zone', 'datestyle'])
            db.cursor().execute('select test')
            db.cursor().execute('set test1')
            self.assertEqual(db._usage, 2)
            self.assertEqual(db._con._con.num_uses, 4)
            self.assertEqual(db._con._con.num_queries, 1)
            self.assertEqual(
                db._con._con.session, ['time zone', 'datestyle', 'test1'])
            db.close()
            db = pool.connection(False)
            self.assertEqual(db._setsession_sql, setsession)
            self.assertEqual(
                db._con._con.session,
                ['time zone', 'datestyle', 'test1', 'rollback'])
            db._con._con.close()
            db.cursor().execute('select test')
            db.cursor().execute('set test2')
            self.assertEqual(
                db._con._con.session, ['time zone', 'datestyle', 'test2'])

    def test16_OneThreadTwoConnections(self):
        for threadsafety in (1, 2):
            dbapi.threadsafety = threadsafety
            shareable = threadsafety > 1
            pool = PooledDB(dbapi, 2)
            db1 = pool.connection()
            for i in range(5):
                db1.cursor().execute('select test')
            db2 = pool.connection()
            self.assertNotEqual(db1, db2)
            self.assertNotEqual(db1._con, db2._con)
            for i in range(7):
                db2.cursor().execute('select test')
            self.assertEqual(db1._con._con.num_queries, 5)
            self.assertEqual(db2._con._con.num_queries, 7)
            del db1
            db1 = pool.connection()
            self.assertNotEqual(db1, db2)
            self.assertNotEqual(db1._con, db2._con)
            for i in range(3):
                db1.cursor().execute('select test')
            self.assertEqual(db1._con._con.num_queries, 8)
            db2.cursor().execute('select test')
            self.assertEqual(db2._con._con.num_queries, 8)
            pool = PooledDB(dbapi, 0, 0, 2)
            db1 = pool.connection()
            for i in range(5):
                db1.cursor().execute('select test')
            db2 = pool.connection()
            self.assertNotEqual(db1, db2)
            self.assertNotEqual(db1._con, db2._con)
            for i in range(7):
                db2.cursor().execute('select test')
            self.assertEqual(db1._con._con.num_queries, 5)
            self.assertEqual(db2._con._con.num_queries, 7)
            del db1
            db1 = pool.connection()
            self.assertNotEqual(db1, db2)
            self.assertNotEqual(db1._con, db2._con)
            for i in range(3):
                db1.cursor().execute('select test')
            self.assertEqual(db1._con._con.num_queries, 8)
            db2.cursor().execute('select test')
            self.assertEqual(db2._con._con.num_queries, 8)
            pool = PooledDB(dbapi, 0, 0, 1)
            db1 = pool.connection()
            db2 = pool.connection()
            self.assertNotEqual(db1, db2)
            if shareable:
                self.assertEqual(db1._con, db2._con)
            else:
                self.assertNotEqual(db1._con, db2._con)
            del db1
            db1 = pool.connection(False)
            self.assertNotEqual(db1, db2)
            self.assertNotEqual(db1._con, db2._con)

    def test17_ThreeThreadsTwoConnections(self):
        for threadsafety in (1, 2):
            dbapi.threadsafety = threadsafety
            pool = PooledDB(dbapi, 2, 2, 0, 2, True)
            try:
                from queue import Queue, Empty
            except ImportError:  # Python 2
                from Queue import Queue, Empty
            queue = Queue(3)

            def connection():
                try:
                    queue.put(pool.connection(), 1, 1)
                except Exception:
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
            self.assertNotEqual(db1, db2)
            db1_con = db1._con
            db2_con = db2._con
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
            pool = PooledDB(dbapi, 2, 2, 1, 2, True)
            db1 = pool.connection(False)
            db2 = pool.connection(False)
            self.assertNotEqual(db1, db2)
            db1_con = db1._con
            db2_con = db2._con
            self.assertNotEqual(db1_con, db2_con)
            Thread(target=connection).start()
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

    def test18_PingCheck(self):
        Connection = dbapi.Connection
        Connection.has_ping = True
        Connection.num_pings = 0
        dbapi.threadsafety = 2
        pool = PooledDB(dbapi, 1, 1, 0, 0, False, None, None, True, None, 0)
        db = pool.connection()
        self.assertTrue(db._con._con.valid)
        self.assertEqual(Connection.num_pings, 0)
        db._con.close()
        db.close()
        db = pool.connection()
        self.assertTrue(not db._con._con.valid)
        self.assertEqual(Connection.num_pings, 0)
        pool = PooledDB(dbapi, 1, 1, 1, 0, False, None, None, True, None, 0)
        db = pool.connection()
        self.assertTrue(db._con._con.valid)
        self.assertEqual(Connection.num_pings, 0)
        db._con.close()
        db = pool.connection()
        self.assertTrue(not db._con._con.valid)
        self.assertEqual(Connection.num_pings, 0)
        pool = PooledDB(dbapi, 1, 1, 0, 0, False, None, None, True, None, 1)
        db = pool.connection()
        self.assertTrue(db._con._con.valid)
        self.assertEqual(Connection.num_pings, 1)
        db._con.close()
        db.close()
        db = pool.connection()
        self.assertTrue(db._con._con.valid)
        self.assertEqual(Connection.num_pings, 2)
        pool = PooledDB(dbapi, 1, 1, 1, 0, False, None, None, True, None, 1)
        db = pool.connection()
        self.assertTrue(db._con._con.valid)
        self.assertEqual(Connection.num_pings, 3)
        db._con.close()
        db = pool.connection()
        self.assertTrue(db._con._con.valid)
        self.assertEqual(Connection.num_pings, 4)
        pool = PooledDB(dbapi, 1, 1, 1, 0, False, None, None, True, None, 2)
        db = pool.connection()
        self.assertTrue(db._con._con.valid)
        self.assertEqual(Connection.num_pings, 4)
        db._con.close()
        db = pool.connection()
        self.assertTrue(not db._con._con.valid)
        self.assertEqual(Connection.num_pings, 4)
        db.cursor()
        self.assertTrue(db._con._con.valid)
        self.assertEqual(Connection.num_pings, 5)
        pool = PooledDB(dbapi, 1, 1, 1, 0, False, None, None, True, None, 4)
        db = pool.connection()
        self.assertTrue(db._con._con.valid)
        self.assertEqual(Connection.num_pings, 5)
        db._con.close()
        db = pool.connection()
        self.assertTrue(not db._con._con.valid)
        self.assertEqual(Connection.num_pings, 5)
        cursor = db.cursor()
        db._con.close()
        self.assertTrue(not db._con._con.valid)
        self.assertEqual(Connection.num_pings, 5)
        cursor.execute('select test')
        self.assertTrue(db._con._con.valid)
        self.assertEqual(Connection.num_pings, 6)
        Connection.has_ping = False
        Connection.num_pings = 0

    def test19_FailedTransaction(self):
        dbapi.threadsafety = 2
        pool = PooledDB(dbapi, 0, 1, 1)
        db = pool.connection()
        cursor = db.cursor()
        db._con._con.close()
        cursor.execute('select test')
        db.begin()
        db._con._con.close()
        self.assertRaises(dbapi.InternalError, cursor.execute, 'select test')
        cursor.execute('select test')
        db.begin()
        db.cancel()
        db._con._con.close()
        cursor.execute('select test')
        pool = PooledDB(dbapi, 1, 1, 0)
        db = pool.connection()
        cursor = db.cursor()
        db._con._con.close()
        cursor.execute('select test')
        db.begin()
        db._con._con.close()
        self.assertRaises(dbapi.InternalError, cursor.execute, 'select test')
        cursor.execute('select test')
        db.begin()
        db.cancel()
        db._con._con.close()
        cursor.execute('select test')

    def test20_SharedInTransaction(self):
        dbapi.threadsafety = 2
        pool = PooledDB(dbapi, 0, 1, 1)
        db = pool.connection()
        db.begin()
        pool.connection(False)
        self.assertRaises(TooManyConnections, pool.connection)
        pool = PooledDB(dbapi, 0, 2, 2)
        db1 = pool.connection()
        db2 = pool.connection()
        self.assertTrue(db2._con is not db1._con)
        db2.close()
        db2 = pool.connection()
        self.assertTrue(db2._con is not db1._con)
        db = pool.connection()
        self.assertTrue(db._con is db1._con)
        db.close()
        db1.begin()
        db = pool.connection()
        self.assertTrue(db._con is db2._con)
        db.close()
        db2.begin()
        pool.connection(False)
        self.assertRaises(TooManyConnections, pool.connection)
        db1.rollback()
        db = pool.connection()
        self.assertTrue(db._con is db1._con)

    def test21_ResetTransaction(self):
        pool = PooledDB(dbapi, 1, 1, 0)
        db = pool.connection()
        db.begin()
        con = db._con
        self.assertTrue(con._transaction)
        self.assertEqual(con._con.session, ['rollback'])
        db.close()
        self.assertTrue(pool.connection()._con is con)
        self.assertTrue(not con._transaction)
        self.assertEqual(con._con.session, ['rollback'] * 3)
        pool = PooledDB(dbapi, 1, 1, 0, reset=False)
        db = pool.connection()
        db.begin()
        con = db._con
        self.assertTrue(con._transaction)
        self.assertEqual(con._con.session, [])
        db.close()
        self.assertTrue(pool.connection()._con is con)
        self.assertTrue(not con._transaction)
        self.assertEqual(con._con.session, ['rollback'])


class TestSharedDBConnection(unittest.TestCase):

    def test01_CreateConnection(self):
        db_con = dbapi.connect()
        con = SharedDBConnection(db_con)
        self.assertEqual(con.con, db_con)
        self.assertEqual(con.shared, 1)

    def test01_ShareAndUnshare(self):
        con = SharedDBConnection(dbapi.connect())
        self.assertEqual(con.shared, 1)
        con.share()
        self.assertEqual(con.shared, 2)
        con.share()
        self.assertEqual(con.shared, 3)
        con.unshare()
        self.assertEqual(con.shared, 2)
        con.unshare()
        self.assertEqual(con.shared, 1)

    def test02_Comparison(self):
        con1 = SharedDBConnection(dbapi.connect())
        con1.con._transaction = False
        con2 = SharedDBConnection(dbapi.connect())
        con2.con._transaction = False
        self.assertTrue(con1 == con2)
        self.assertTrue(con1 <= con2)
        self.assertTrue(con1 >= con2)
        self.assertTrue(not con1 != con2)
        self.assertTrue(not con1 < con2)
        self.assertTrue(not con1 > con2)
        con2.share()
        self.assertTrue(not con1 == con2)
        self.assertTrue(con1 <= con2)
        self.assertTrue(not con1 >= con2)
        self.assertTrue(con1 != con2)
        self.assertTrue(con1 < con2)
        self.assertTrue(not con1 > con2)
        con1.con._transaction = True
        self.assertTrue(not con1 == con2)
        self.assertTrue(not con1 <= con2)
        self.assertTrue(con1 >= con2)
        self.assertTrue(con1 != con2)
        self.assertTrue(not con1 < con2)
        self.assertTrue(con1 > con2)


if __name__ == '__main__':
    unittest.main()
