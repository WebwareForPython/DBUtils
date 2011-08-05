"""Test the SteadyDB module.

Note:
We do not test any real DB-API 2 module, but we just
mock the basic DB-API 2 connection functionality.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke

"""

__version__ = '1.0'
__revision__ = "$Rev$"
__date__ = "$Date$"


import sys

# This module also serves as a mock object for the DB-API 2 module:

dbapi = sys.modules[__name__]

threadsafety = 2

class Error(StandardError): pass
class DatabaseError(Error): pass
class OperationalError(DatabaseError): pass
class InternalError(DatabaseError): pass
class ProgrammingError(DatabaseError): pass


def connect(database=None, user=None):
    return Connection(database, user)


class Connection:

    def __init__(self, database=None, user=None):
        self.database = database
        self.user = user
        self.valid = False
        if database == 'error':
            raise OperationalError
        self.open_cursors = 0
        self.num_uses = 0
        self.num_queries = 0
        self.session = []
        self.valid = True

    def close(self):
        if not self.valid:
            raise InternalError
        self.open_cursors = 0
        self.num_uses = 0
        self.num_queries = 0
        self.session = []
        self.valid = False

    def commit(self):
        self.session.append('commit')

    def rollback(self):
        self.session.append('rollback')

    def cursor(self, name=None):
        if not self.valid:
            raise InternalError
        return Cursor(self, name)


class Cursor:

    def __init__(self, con, name=None):
        self.con = con
        self.valid = False
        if name == 'error':
            raise OperationalError
        self.result = None
        con.open_cursors += 1
        self.valid = True

    def close(self):
        if not self.valid:
            raise InternalError
        self.con.open_cursors -= 1
        self.valid = False

    def execute(self, operation):
        if not self.valid or not self.con.valid:
            raise InternalError
        self.con.num_uses += 1
        if operation.startswith('select '):
            self.con.num_queries += 1
            self.result = operation[7:]
        elif operation.startswith('set '):
            self.con.session.append(operation[4:])
            self.result = None
        else:
            raise ProgrammingError

    def fetchone(self):
        if not self.valid:
            raise InternalError
        result = self.result
        self.result = None
        return result

    def callproc(self, procname):
        if not self.valid or not self.con.valid:
            raise InternalError
        self.con.num_uses += 1

    def __del__(self):
        if self.valid:
            self.close()


import unittest

sys.path.insert(1, '../..')
from DBUtils.SteadyDB import connect as SteadyDBconnect
from DBUtils.SteadyDB import SteadyDBConnection, SteadyDBCursor


class TestSteadyDB(unittest.TestCase):

    def test0_CheckVersion(self):
        from DBUtils import __version__ as DBUtilsVersion
        self.assertEqual(DBUtilsVersion, __version__)
        from DBUtils.SteadyDB import __version__ as SteadyDBVersion
        self.assertEqual(SteadyDBVersion, __version__)
        self.assertEqual(SteadyDBConnection.version, __version__)

    def test1_MockedDBConnection(self):
        db = connect('SteadyDBTestDB',
            user='SteadyDBTestUser')
        self.assert_(hasattr(db, 'database'))
        self.assertEqual(db.database, 'SteadyDBTestDB')
        self.assert_(hasattr(db, 'user'))
        self.assertEqual(db.user, 'SteadyDBTestUser')
        self.assert_(hasattr(db, 'cursor'))
        self.assert_(hasattr(db, 'close'))
        self.assert_(hasattr(db, 'open_cursors'))
        self.assert_(hasattr(db, 'num_uses'))
        self.assert_(hasattr(db, 'num_queries'))
        self.assert_(hasattr(db, 'session'))
        self.assert_(hasattr(db, 'valid'))
        self.assert_(db.valid)
        self.assertEqual(db.open_cursors, 0)
        for i in range(3):
            cursor = db.cursor()
            self.assertEqual(db.open_cursors, 1)
            cursor.close()
            self.assertEqual(db.open_cursors, 0)
        cursor = []
        for i in range(3):
            cursor.append(db.cursor())
            self.assertEqual(db.open_cursors, i + 1)
        del cursor
        self.assertEqual(db.open_cursors, 0)
        cursor = db.cursor()
        self.assert_(hasattr(cursor, 'execute'))
        self.assert_(hasattr(cursor, 'fetchone'))
        self.assert_(hasattr(cursor, 'callproc'))
        self.assert_(hasattr(cursor, 'close'))
        self.assert_(hasattr(cursor, 'valid'))
        self.assert_(cursor.valid)
        self.assertEqual(db.open_cursors, 1)
        for i in range(3):
            self.assertEqual(db.num_uses, i)
            self.assertEqual(db.num_queries, i)
            cursor.execute('select test%d' % i)
            self.assertEqual(cursor.fetchone(), 'test%d' % i)
        self.assert_(cursor.valid)
        self.assertEqual(db.open_cursors, 1)
        for i in range(4):
            cursor.callproc('test')
        cursor.close()
        self.assert_(not cursor.valid)
        self.assertEqual(db.open_cursors, 0)
        self.assertEqual(db.num_uses, 7)
        self.assertEqual(db.num_queries, 3)
        self.assertRaises(InternalError, cursor.close)
        self.assertRaises(InternalError, cursor.execute, 'select test')
        self.assert_(db.valid)
        db.close()
        self.assert_(not db.valid)
        self.assertEqual(db.num_uses, 0)
        self.assertEqual(db.num_queries, 0)
        self.assertRaises(InternalError, db.close)
        self.assertRaises(InternalError, db.cursor)

    def test2_BrokenDBConnection(self):
        self.assertRaises(TypeError, SteadyDBConnection, None)
        self.assertRaises(TypeError, SteadyDBCursor, None)
        db = SteadyDBconnect(dbapi, database='ok')
        for i in range(3):
            db.close()
        del db
        self.assertRaises(OperationalError, SteadyDBconnect,
            dbapi, database='error')
        db = SteadyDBconnect(dbapi, database='ok')
        cursor = db.cursor()
        for i in range(3):
            cursor.close()
        cursor = db.cursor('ok')
        for i in range(3):
            cursor.close()
        self.assertRaises(OperationalError, db.cursor, 'error')

    def test3_SteadyDBClose(self):
        for closeable in (False, True):
            db = SteadyDBconnect(dbapi, closeable=closeable)
            self.assert_(db._con.valid)
            db.close()
            self.assert_(closeable ^ db._con.valid)
            db.close()
            self.assert_(closeable ^ db._con.valid)
            db._close()
            self.assert_(not db._con.valid)
            db._close()
            self.assert_(not db._con.valid)

    def test4_SteadyDBConnection(self):
        db = SteadyDBconnect(dbapi, 0, None, None, 1,
            'SteadyDBTestDB', user='SteadyDBTestUser')
        self.assert_(isinstance(db, SteadyDBConnection))
        self.assert_(hasattr(db, '_con'))
        self.assert_(hasattr(db, '_usage'))
        self.assertEqual(db._usage, 0)
        self.assert_(hasattr(db._con, 'valid'))
        self.assert_(db._con.valid)
        self.assert_(hasattr(db._con, 'cursor'))
        self.assert_(hasattr(db._con, 'close'))
        self.assert_(hasattr(db._con, 'open_cursors'))
        self.assert_(hasattr(db._con, 'num_uses'))
        self.assert_(hasattr(db._con, 'num_queries'))
        self.assert_(hasattr(db._con, 'session'))
        self.assert_(hasattr(db._con, 'database'))
        self.assertEqual(db._con.database, 'SteadyDBTestDB')
        self.assert_(hasattr(db._con, 'user'))
        self.assertEqual(db._con.user, 'SteadyDBTestUser')
        self.assert_(hasattr(db, 'cursor'))
        self.assert_(hasattr(db, 'close'))
        self.assertEqual(db._con.open_cursors, 0)
        for i in range(3):
            cursor = db.cursor()
            self.assertEqual(db._con.open_cursors, 1)
            cursor.close()
            self.assertEqual(db._con.open_cursors, 0)
        cursor = []
        for i in range(3):
            cursor.append(db.cursor())
            self.assertEqual(db._con.open_cursors, i + 1)
        del cursor
        self.assertEqual(db._con.open_cursors, 0)
        cursor = db.cursor()
        self.assert_(hasattr(cursor, 'execute'))
        self.assert_(hasattr(cursor, 'fetchone'))
        self.assert_(hasattr(cursor, 'callproc'))
        self.assert_(hasattr(cursor, 'close'))
        self.assert_(hasattr(cursor, 'valid'))
        self.assert_(cursor.valid)
        self.assertEqual(db._con.open_cursors, 1)
        for i in range(3):
            self.assertEqual(db._usage, i)
            self.assertEqual(db._con.num_uses, i)
            self.assertEqual(db._con.num_queries, i)
            cursor.execute('select test%d' % i)
            self.assertEqual(cursor.fetchone(), 'test%d' % i)
        self.assert_(cursor.valid)
        self.assertEqual(db._con.open_cursors, 1)
        for i in range(4):
            cursor.callproc('test')
        cursor.close()
        self.assert_(not cursor.valid)
        self.assertEqual(db._con.open_cursors, 0)
        self.assertEqual(db._usage, 7)
        self.assertEqual(db._con.num_uses, 7)
        self.assertEqual(db._con.num_queries, 3)
        cursor.close()
        cursor.execute('select test8')
        self.assert_(cursor.valid)
        self.assertEqual(db._con.open_cursors, 1)
        self.assertEqual(cursor.fetchone(), 'test8')
        self.assertEqual(db._usage, 8)
        self.assertEqual(db._con.num_uses, 8)
        self.assertEqual(db._con.num_queries, 4)
        self.assert_(db._con.valid)
        db.close()
        self.assert_(not db._con.valid)
        self.assertEqual(db._con.open_cursors, 0)
        self.assertEqual(db._usage, 8)
        self.assertEqual(db._con.num_uses, 0)
        self.assertEqual(db._con.num_queries, 0)
        self.assertRaises(InternalError, db._con.close)
        db.close()
        self.assertRaises(InternalError, db._con.cursor)
        cursor = db.cursor()
        self.assert_(db._con.valid)
        cursor.execute('select test11')
        self.assertEqual(cursor.fetchone(), 'test11')
        cursor.execute('select test12')
        self.assertEqual(cursor.fetchone(), 'test12')
        cursor.callproc('test')
        self.assertEqual(db._usage, 3)
        self.assertEqual(db._con.num_uses, 3)
        self.assertEqual(db._con.num_queries, 2)
        cursor2 = db.cursor()
        self.assertEqual(db._con.open_cursors, 2)
        cursor2.execute('select test13')
        self.assertEqual(cursor2.fetchone(), 'test13')
        self.assertEqual(db._con.num_queries, 3)
        db.close()
        self.assertEqual(db._con.open_cursors, 0)
        self.assertEqual(db._con.num_queries, 0)
        cursor = db.cursor()
        self.assert_(cursor.valid)
        cursor.callproc('test')
        cursor._cursor.valid = False
        self.assert_(not cursor.valid)
        self.assertRaises(InternalError, cursor._cursor.callproc, 'test')
        cursor.callproc('test')
        self.assert_(cursor.valid)
        cursor._cursor.callproc('test')
        self.assertEqual(db._usage, 2)
        self.assertEqual(db._con.num_uses, 3)
        db._con.valid = cursor._cursor.valid = False
        cursor.callproc('test')
        self.assert_(cursor.valid)
        self.assertEqual(db._usage, 1)
        self.assertEqual(db._con.num_uses, 1)
        cursor.execute('set doit')
        db.commit()
        cursor.execute('set dont')
        db.rollback()
        self.assertEqual(db._con.session,
            ['doit', 'commit', 'dont', 'rollback'])

    def test5_SteadyDBConnectionCreatorFunction(self):
        db1 = SteadyDBconnect(dbapi, 0, None, None, 1,
            'SteadyDBTestDB', user='SteadyDBTestUser')
        db2 = SteadyDBconnect(connect, 0, None, None, 1,
            'SteadyDBTestDB', user='SteadyDBTestUser')
        self.assertEqual(db1.dbapi(), db2.dbapi())
        self.assertEqual(db1.threadsafety(), db2.threadsafety())
        self.assertEqual(db1._creator, db2._creator)
        self.assertEqual(db1._args, db2._args)
        self.assertEqual(db1._kwargs, db2._kwargs)
        db2.close()
        db1.close()

    def test6_SteadyDBConnectionMaxUsage(self):
        db = SteadyDBconnect(dbapi, 10)
        cursor = db.cursor()
        for i in range(100):
            cursor.execute('select test%d' % i)
            r = cursor.fetchone()
            self.assertEqual(r, 'test%d' % i)
            self.assert_(db._con.valid)
            j = i % 10 + 1
            self.assertEqual(db._usage, j)
            self.assertEqual(db._con.num_uses, j)
            self.assertEqual(db._con.num_queries, j)
        self.assertEqual(db._con.open_cursors, 1)
        for i in range(100):
            cursor.callproc('test')
            self.assert_(db._con.valid)
            j = i % 10 + 1
            self.assertEqual(db._usage, j)
            self.assertEqual(db._con.num_uses, j)
            self.assertEqual(db._con.num_queries, 0)
        for i in range(10):
            if i == 7:
                db._con.valid = cursor._cursor.valid = False
            cursor.execute('select test%d' % i)
            r = cursor.fetchone()
            self.assertEqual(r, 'test%d' % i)
            j = i % 7 + 1
            self.assertEqual(db._usage, j)
            self.assertEqual(db._con.num_uses, j)
            self.assertEqual(db._con.num_queries, j)
        for i in range(10):
            if i == 5:
                db._con.valid = cursor._cursor.valid = False
            cursor.callproc('test')
            j = (i + (i < 5 and 3 or -5)) % 10 + 1
            self.assertEqual(db._usage, j)
            self.assertEqual(db._con.num_uses, j)
            j = i < 5 and 3 or 0
            self.assertEqual(db._con.num_queries, j)
        db.close()
        cursor.execute('select test1')
        self.assertEqual(cursor.fetchone(), 'test1')
        self.assertEqual(db._usage, 1)
        self.assertEqual(db._con.num_uses, 1)
        self.assertEqual(db._con.num_queries, 1)

    def test7_SteadyDBConnectionSetSession(self):
        db = SteadyDBconnect(dbapi, 3, ('set time zone', 'set datestyle'))
        self.assert_(hasattr(db, '_usage'))
        self.assertEqual(db._usage, 0)
        self.assert_(hasattr(db._con, 'open_cursors'))
        self.assertEqual(db._con.open_cursors, 0)
        self.assert_(hasattr(db._con, 'num_uses'))
        self.assertEqual(db._con.num_uses, 2)
        self.assert_(hasattr(db._con, 'num_queries'))
        self.assertEqual(db._con.num_queries, 0)
        self.assert_(hasattr(db._con, 'session'))
        self.assertEqual(tuple(db._con.session), ('time zone', 'datestyle'))
        for i in range(11):
            db.cursor().execute('select test')
        self.assertEqual(db._con.open_cursors, 0)
        self.assertEqual(db._usage, 2)
        self.assertEqual(db._con.num_uses, 4)
        self.assertEqual(db._con.num_queries, 2)
        self.assertEqual(db._con.session, ['time zone', 'datestyle'])
        db.cursor().execute('set test')
        self.assertEqual(db._con.open_cursors, 0)
        self.assertEqual(db._usage, 3)
        self.assertEqual(db._con.num_uses, 5)
        self.assertEqual(db._con.num_queries, 2)
        self.assertEqual(db._con.session, ['time zone', 'datestyle', 'test'])
        db.cursor().execute('select test')
        self.assertEqual(db._con.open_cursors, 0)
        self.assertEqual(db._usage, 1)
        self.assertEqual(db._con.num_uses, 3)
        self.assertEqual(db._con.num_queries, 1)
        self.assertEqual(db._con.session, ['time zone', 'datestyle'])
        db.cursor().execute('set test')
        self.assertEqual(db._con.open_cursors, 0)
        self.assertEqual(db._usage, 2)
        self.assertEqual(db._con.num_uses, 4)
        self.assertEqual(db._con.num_queries, 1)
        self.assertEqual(db._con.session, ['time zone', 'datestyle', 'test'])
        db.cursor().execute('select test')
        self.assertEqual(db._con.open_cursors, 0)
        self.assertEqual(db._usage, 3)
        self.assertEqual(db._con.num_uses, 5)
        self.assertEqual(db._con.num_queries, 2)
        self.assertEqual(db._con.session, ['time zone', 'datestyle', 'test'])
        db.close()
        db.cursor().execute('set test')
        self.assertEqual(db._con.open_cursors, 0)
        self.assertEqual(db._usage, 1)
        self.assertEqual(db._con.num_uses, 3)
        self.assertEqual(db._con.num_queries, 0)
        self.assertEqual(db._con.session, ['time zone', 'datestyle', 'test'])
        db.close()
        db.cursor().execute('select test')
        self.assertEqual(db._con.open_cursors, 0)
        self.assertEqual(db._usage, 1)
        self.assertEqual(db._con.num_uses, 3)
        self.assertEqual(db._con.num_queries, 1)
        self.assertEqual(db._con.session, ['time zone', 'datestyle'])

    def test8_SteadyDBConnectionFailures(self):
        db = SteadyDBconnect(dbapi)
        db.close()
        db.cursor()
        db = SteadyDBconnect(dbapi, failures=InternalError)
        db.close()
        db.cursor()
        db = SteadyDBconnect(dbapi, failures=OperationalError)
        db.close()
        self.assertRaises(InternalError, db.cursor)
        db = SteadyDBconnect(dbapi,
            failures=(OperationalError, InternalError))
        db.close()
        db.cursor()


if __name__ == '__main__':
    unittest.main()
