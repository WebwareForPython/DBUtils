"""Test the SteadyPg module.

Note:
We do not test the real PyGreSQL module, but we just
mock the basic connection functionality of that module.
We assume that the PyGreSQL module will detect lost
connections correctly and set the status flag accordingly.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke

"""

import unittest
import sys

import DBUtils.Tests.mock_pg as pg

from DBUtils.SteadyPg import SteadyPgConnection

__version__ = '1.3'


class TestSteadyPg(unittest.TestCase):

    def test0_CheckVersion(self):
        from DBUtils import __version__ as DBUtilsVersion
        self.assertEqual(DBUtilsVersion, __version__)
        from DBUtils.SteadyPg import __version__ as SteadyPgVersion
        self.assertEqual(SteadyPgVersion, __version__)
        self.assertEqual(SteadyPgConnection.version, __version__)

    def test1_MockedConnection(self):
        PgConnection = pg.DB
        db = PgConnection(
            'SteadyPgTestDB', user='SteadyPgTestUser')
        self.assertTrue(hasattr(db, 'db'))
        self.assertTrue(hasattr(db.db, 'status'))
        self.assertTrue(db.db.status)
        self.assertTrue(hasattr(db.db, 'query'))
        self.assertTrue(hasattr(db.db, 'close'))
        self.assertTrue(not hasattr(db.db, 'reopen'))
        self.assertTrue(hasattr(db, 'reset'))
        self.assertTrue(hasattr(db.db, 'num_queries'))
        self.assertTrue(hasattr(db.db, 'session'))
        self.assertTrue(not hasattr(db.db, 'get_tables'))
        self.assertTrue(hasattr(db.db, 'db'))
        self.assertEqual(db.db.db, 'SteadyPgTestDB')
        self.assertTrue(hasattr(db.db, 'user'))
        self.assertEqual(db.db.user, 'SteadyPgTestUser')
        self.assertTrue(hasattr(db, 'query'))
        self.assertTrue(hasattr(db, 'close'))
        self.assertTrue(hasattr(db, 'reopen'))
        self.assertTrue(hasattr(db, 'reset'))
        self.assertTrue(hasattr(db, 'num_queries'))
        self.assertTrue(hasattr(db, 'session'))
        self.assertTrue(hasattr(db, 'get_tables'))
        self.assertTrue(hasattr(db, 'dbname'))
        self.assertEqual(db.dbname, 'SteadyPgTestDB')
        self.assertTrue(hasattr(db, 'user'))
        self.assertEqual(db.user, 'SteadyPgTestUser')
        for i in range(3):
            self.assertEqual(db.num_queries, i)
            self.assertEqual(
                db.query('select test%d' % i), 'test%d' % i)
        self.assertTrue(db.db.status)
        db.reopen()
        self.assertTrue(db.db.status)
        self.assertEqual(db.num_queries, 0)
        self.assertEqual(db.query('select test4'), 'test4')
        self.assertEqual(db.get_tables(), 'test')
        db.close()
        try:
            status = db.db.status
        except AttributeError:
            status = False
        self.assertTrue(not status)
        self.assertRaises(pg.InternalError, db.close)
        self.assertRaises(pg.InternalError, db.query, 'select test')
        self.assertRaises(pg.InternalError, db.get_tables)

    def test2_BrokenConnection(self):
        self.assertRaises(TypeError, SteadyPgConnection, 'wrong')
        db = SteadyPgConnection(dbname='ok')
        InternalError = sys.modules[db._con.__module__].InternalError
        for i in range(3):
            db.close()
        del db
        self.assertRaises(InternalError, SteadyPgConnection, dbname='error')

    def test3_Close(self):
        for closeable in (False, True):
            db = SteadyPgConnection(closeable=closeable)
            self.assertTrue(db._con.db and db._con.valid)
            db.close()
            self.assertTrue(
                closeable ^ (db._con.db is not None and db._con.valid))
            db.close()
            self.assertTrue(
                closeable ^ (db._con.db is not None and db._con.valid))
            db._close()
            self.assertTrue(not db._con.db or not db._con.valid)
            db._close()
            self.assertTrue(not db._con.db or not db._con.valid)

    def test4_Connection(self):
        db = SteadyPgConnection(
            0, None, 1, 'SteadyPgTestDB', user='SteadyPgTestUser')
        self.assertTrue(hasattr(db, 'db'))
        self.assertTrue(hasattr(db, '_con'))
        self.assertEqual(db.db, db._con.db)
        self.assertTrue(hasattr(db, '_usage'))
        self.assertEqual(db._usage, 0)
        self.assertTrue(hasattr(db.db, 'status'))
        self.assertTrue(db.db.status)
        self.assertTrue(hasattr(db.db, 'query'))
        self.assertTrue(hasattr(db.db, 'close'))
        self.assertTrue(not hasattr(db.db, 'reopen'))
        self.assertTrue(hasattr(db.db, 'reset'))
        self.assertTrue(hasattr(db.db, 'num_queries'))
        self.assertTrue(hasattr(db.db, 'session'))
        self.assertTrue(hasattr(db.db, 'db'))
        self.assertEqual(db.db.db, 'SteadyPgTestDB')
        self.assertTrue(hasattr(db.db, 'user'))
        self.assertEqual(db.db.user, 'SteadyPgTestUser')
        self.assertTrue(not hasattr(db.db, 'get_tables'))
        self.assertTrue(hasattr(db, 'query'))
        self.assertTrue(hasattr(db, 'close'))
        self.assertTrue(hasattr(db, 'reopen'))
        self.assertTrue(hasattr(db, 'reset'))
        self.assertTrue(hasattr(db, 'num_queries'))
        self.assertTrue(hasattr(db, 'session'))
        self.assertTrue(hasattr(db, 'dbname'))
        self.assertEqual(db.dbname, 'SteadyPgTestDB')
        self.assertTrue(hasattr(db, 'user'))
        self.assertEqual(db.user, 'SteadyPgTestUser')
        self.assertTrue(hasattr(db, 'get_tables'))
        for i in range(3):
            self.assertEqual(db._usage, i)
            self.assertEqual(db.num_queries, i)
            self.assertEqual(
                db.query('select test%d' % i), 'test%d' % i)
        self.assertTrue(db.db.status)
        self.assertEqual(db.get_tables(), 'test')
        self.assertTrue(db.db.status)
        self.assertEqual(db._usage, 4)
        self.assertEqual(db.num_queries, 3)
        db.reopen()
        self.assertTrue(db.db.status)
        self.assertEqual(db._usage, 0)
        self.assertEqual(db.num_queries, 0)
        self.assertEqual(db.query('select test'), 'test')
        self.assertTrue(db.db.status)
        self.assertTrue(hasattr(db._con, 'status'))
        self.assertTrue(db._con.status)
        self.assertTrue(hasattr(db._con, 'close'))
        self.assertTrue(hasattr(db._con, 'query'))
        db.close()
        try:
            status = db.db.status
        except AttributeError:
            status = False
        self.assertTrue(not status)
        self.assertTrue(hasattr(db._con, 'close'))
        self.assertTrue(hasattr(db._con, 'query'))
        InternalError = sys.modules[db._con.__module__].InternalError
        self.assertRaises(InternalError, db._con.close)
        self.assertRaises(InternalError, db._con.query, 'select test')
        self.assertEqual(db.query('select test'), 'test')
        self.assertTrue(db.db.status)
        self.assertEqual(db._usage, 1)
        self.assertEqual(db.num_queries, 1)
        db.db.status = False
        self.assertTrue(not db.db.status)
        self.assertEqual(db.query('select test'), 'test')
        self.assertTrue(db.db.status)
        self.assertEqual(db._usage, 1)
        self.assertEqual(db.num_queries, 1)
        db.db.status = False
        self.assertTrue(not db.db.status)
        self.assertEqual(db.get_tables(), 'test')
        self.assertTrue(db.db.status)
        self.assertEqual(db._usage, 1)
        self.assertEqual(db.num_queries, 0)

    def test5_ConnectionContextHandler(self):
        db = SteadyPgConnection(
            0, None, 1, 'SteadyPgTestDB', user='SteadyPgTestUser')
        self.assertEqual(db.session, [])
        with db:
            db.query('select test')
        self.assertEqual(db.session, ['begin', 'commit'])
        try:
            with db:
                db.query('error')
        except pg.ProgrammingError:
            error = True
        else:
            error = False
        self.assertTrue(error)
        self.assertEqual(
            db._con.session, ['begin', 'commit', 'begin', 'rollback'])

    def test6_ConnectionMaxUsage(self):
        db = SteadyPgConnection(10)
        for i in range(100):
            r = db.query('select test%d' % i)
            self.assertEqual(r, 'test%d' % i)
            self.assertTrue(db.db.status)
            j = i % 10 + 1
            self.assertEqual(db._usage, j)
            self.assertEqual(db.num_queries, j)
        for i in range(100):
            r = db.get_tables()
            self.assertEqual(r, 'test')
            self.assertTrue(db.db.status)
            j = i % 10 + 1
            self.assertEqual(db._usage, j)
            self.assertEqual(db.num_queries, 0)
        for i in range(10):
            if i == 7:
                db.db.status = False
            r = db.query('select test%d' % i)
            self.assertEqual(r, 'test%d' % i)
            j = i % 7 + 1
            self.assertEqual(db._usage, j)
            self.assertEqual(db.num_queries, j)
        for i in range(10):
            if i == 5:
                db.db.status = False
            r = db.get_tables()
            self.assertEqual(r, 'test')
            j = (i + (3 if i < 5 else -5)) % 10 + 1
            self.assertEqual(db._usage, j)
            j = 3 if i < 5 else 0
            self.assertEqual(db.num_queries, j)
        db.close()
        self.assertEqual(db.query('select test1'), 'test1')
        self.assertEqual(db._usage, 1)
        self.assertEqual(db.num_queries, 1)
        db.reopen()
        self.assertEqual(db._usage, 0)
        self.assertEqual(db.num_queries, 0)
        self.assertEqual(db.query('select test2'), 'test2')
        self.assertEqual(db._usage, 1)
        self.assertEqual(db.num_queries, 1)

    def test7_ConnectionSetSession(self):
        db = SteadyPgConnection(3, ('set time zone', 'set datestyle'))
        self.assertTrue(hasattr(db, 'num_queries'))
        self.assertEqual(db.num_queries, 0)
        self.assertTrue(hasattr(db, 'session'))
        self.assertEqual(tuple(db.session), ('time zone', 'datestyle'))
        for i in range(11):
            db.query('select test')
        self.assertEqual(db.num_queries, 2)
        self.assertEqual(db.session, ['time zone', 'datestyle'])
        db.query('set test')
        self.assertEqual(db.num_queries, 2)
        self.assertEqual(db.session, ['time zone', 'datestyle', 'test'])
        db.query('select test')
        self.assertEqual(db.num_queries, 1)
        self.assertEqual(db.session, ['time zone', 'datestyle'])
        db.close()
        db.query('set test')
        self.assertEqual(db.num_queries, 0)
        self.assertEqual(db.session, ['time zone', 'datestyle', 'test'])

    def test8_Begin(self):
        for closeable in (False, True):
            db = SteadyPgConnection(closeable=closeable)
            db.begin()
            self.assertEqual(db.session, ['begin'])
            db.query('select test')
            self.assertEqual(db.num_queries, 1)
            db.close()
            db.query('select test')
            self.assertEqual(db.num_queries, 1)
            db.begin()
            self.assertEqual(db.session, ['begin'])
            db.db.close()
            self.assertRaises(pg.InternalError, db.query, 'select test')
            self.assertEqual(db.num_queries, 0)
            db.query('select test')
            self.assertEqual(db.num_queries, 1)
            self.assertEqual(db.begin('select sql:begin'), 'sql:begin')
            self.assertEqual(db.num_queries, 2)

    def test9_End(self):
        for closeable in (False, True):
            db = SteadyPgConnection(closeable=closeable)
            db.begin()
            db.query('select test')
            db.end()
            self.assertEqual(db.session, ['begin', 'end'])
            db.db.close()
            db.query('select test')
            self.assertEqual(db.num_queries, 1)
            self.assertEqual(db.begin('select sql:end'), 'sql:end')
            self.assertEqual(db.num_queries, 2)
            db.begin()
            db.query('select test')
            db.commit()
            self.assertEqual(db.session, ['begin', 'commit'])
            db.db.close()
            db.query('select test')
            self.assertEqual(db.num_queries, 1)
            self.assertEqual(db.begin('select sql:commit'), 'sql:commit')
            self.assertEqual(db.num_queries, 2)
            db.begin()
            db.query('select test')
            db.rollback()
            self.assertEqual(db.session, ['begin', 'rollback'])
            db.db.close()
            db.query('select test')
            self.assertEqual(db.num_queries, 1)
            self.assertEqual(db.begin('select sql:rollback'), 'sql:rollback')
            self.assertEqual(db.num_queries, 2)


if __name__ == '__main__':
    unittest.main()
