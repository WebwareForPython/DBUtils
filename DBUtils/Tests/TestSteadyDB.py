"""Test the SteadyDB module.

Note:
We do not test any real DB-API 2 module, but we just
mock the basic DB-API 2 connection functionality.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke

"""

import sys

__version__ = '1.2'

# This module also serves as a mock object for the DB-API 2 module:
dbapi = sys.modules[__name__]

threadsafety = 2


class Error(Exception):
    pass


class DatabaseError(Error):
    pass


class OperationalError(DatabaseError):
    pass


class InternalError(DatabaseError):
    pass


class ProgrammingError(DatabaseError):
    pass


def connect(database=None, user=None):
    return Connection(database, user)


class Connection:

    has_ping = False
    num_pings = 0

    def __init__(self, database=None, user=None):
        self.database = database
        self.user = user
        self.valid = False
        if database == 'error':
            raise OperationalError
        self.open_cursors = 0
        self.num_uses = 0
        self.num_queries = 0
        self.num_pings = 0
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
        if not self.valid:
            raise InternalError
        self.session.append('commit')

    def rollback(self):
        if not self.valid:
            raise InternalError
        self.session.append('rollback')

    def ping(self):
        cls = self.__class__
        cls.num_pings += 1
        if not cls.has_ping:
            raise AttributeError
        if not self.valid:
            raise OperationalError

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
        self.inputsizes = []
        self.outputsizes = {}
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
        elif operation == 'get sizes':
            self.result = (self.inputsizes, self.outputsizes)
            self.inputsizes = []
            self.outputsizes = {}
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

    def setinputsizes(self, sizes):
        if not self.valid:
            raise InternalError
        self.inputsizes = sizes

    def setoutputsize(self, size, column=None):
        if not self.valid:
            raise InternalError
        self.outputsizes[column] = size

    def __del__(self):
        if self.valid:
            self.close()


import unittest

sys.path.insert(1, '../..')
from DBUtils.SteadyDB import connect as SteadyDBconnect
from DBUtils.SteadyDB import SteadyDBConnection, SteadyDBCursor


class TestSteadyDB(unittest.TestCase):

    def test00_CheckVersion(self):
        from DBUtils import __version__ as DBUtilsVersion
        self.assertEqual(DBUtilsVersion, __version__)
        from DBUtils.SteadyDB import __version__ as SteadyDBVersion
        self.assertEqual(SteadyDBVersion, __version__)
        self.assertEqual(SteadyDBConnection.version, __version__)

    def test01_MockedConnection(self):
        db = connect('SteadyDBTestDB',
            user='SteadyDBTestUser')
        db.__class__.has_ping = False
        db.__class__.num_pings = 0
        self.assertTrue(hasattr(db, 'database'))
        self.assertEqual(db.database, 'SteadyDBTestDB')
        self.assertTrue(hasattr(db, 'user'))
        self.assertEqual(db.user, 'SteadyDBTestUser')
        self.assertTrue(hasattr(db, 'cursor'))
        self.assertTrue(hasattr(db, 'close'))
        self.assertTrue(hasattr(db, 'open_cursors'))
        self.assertTrue(hasattr(db, 'num_uses'))
        self.assertTrue(hasattr(db, 'num_queries'))
        self.assertTrue(hasattr(db, 'session'))
        self.assertTrue(hasattr(db, 'valid'))
        self.assertTrue(db.valid)
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
        self.assertTrue(hasattr(cursor, 'execute'))
        self.assertTrue(hasattr(cursor, 'fetchone'))
        self.assertTrue(hasattr(cursor, 'callproc'))
        self.assertTrue(hasattr(cursor, 'close'))
        self.assertTrue(hasattr(cursor, 'valid'))
        self.assertTrue(cursor.valid)
        self.assertEqual(db.open_cursors, 1)
        for i in range(3):
            self.assertEqual(db.num_uses, i)
            self.assertEqual(db.num_queries, i)
            cursor.execute('select test%d' % i)
            self.assertEqual(cursor.fetchone(), 'test%d' % i)
        self.assertTrue(cursor.valid)
        self.assertEqual(db.open_cursors, 1)
        for i in range(4):
            cursor.callproc('test')
        cursor.close()
        self.assertTrue(not cursor.valid)
        self.assertEqual(db.open_cursors, 0)
        self.assertEqual(db.num_uses, 7)
        self.assertEqual(db.num_queries, 3)
        self.assertRaises(InternalError, cursor.close)
        self.assertRaises(InternalError, cursor.execute, 'select test')
        self.assertTrue(db.valid)
        self.assertTrue(not db.__class__.has_ping)
        self.assertEqual(db.__class__.num_pings, 0)
        self.assertRaises(AttributeError, db.ping)
        self.assertEqual(db.__class__.num_pings, 1)
        db.__class__.has_ping = True
        self.assertTrue(db.ping() is None)
        self.assertEqual(db.__class__.num_pings, 2)
        db.close()
        self.assertTrue(not db.valid)
        self.assertEqual(db.num_uses, 0)
        self.assertEqual(db.num_queries, 0)
        self.assertRaises(InternalError, db.close)
        self.assertRaises(InternalError, db.cursor)
        self.assertRaises(OperationalError, db.ping)
        self.assertEqual(db.__class__.num_pings, 3)
        db.__class__.has_ping = False
        db.__class__.num_pings = 0

    def test02_BrokenConnection(self):
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

    def test03_Close(self):
        for closeable in (False, True):
            db = SteadyDBconnect(dbapi, closeable=closeable)
            self.assertTrue(db._con.valid)
            db.close()
            self.assertTrue(closeable ^ db._con.valid)
            db.close()
            self.assertTrue(closeable ^ db._con.valid)
            db._close()
            self.assertTrue(not db._con.valid)
            db._close()
            self.assertTrue(not db._con.valid)

    def test04_Connection(self):
        db = SteadyDBconnect(dbapi, 0, None, None, None, True,
            'SteadyDBTestDB', user='SteadyDBTestUser')
        self.assertTrue(isinstance(db, SteadyDBConnection))
        self.assertTrue(hasattr(db, '_con'))
        self.assertTrue(hasattr(db, '_usage'))
        self.assertEqual(db._usage, 0)
        self.assertTrue(hasattr(db._con, 'valid'))
        self.assertTrue(db._con.valid)
        self.assertTrue(hasattr(db._con, 'cursor'))
        self.assertTrue(hasattr(db._con, 'close'))
        self.assertTrue(hasattr(db._con, 'open_cursors'))
        self.assertTrue(hasattr(db._con, 'num_uses'))
        self.assertTrue(hasattr(db._con, 'num_queries'))
        self.assertTrue(hasattr(db._con, 'session'))
        self.assertTrue(hasattr(db._con, 'database'))
        self.assertEqual(db._con.database, 'SteadyDBTestDB')
        self.assertTrue(hasattr(db._con, 'user'))
        self.assertEqual(db._con.user, 'SteadyDBTestUser')
        self.assertTrue(hasattr(db, 'cursor'))
        self.assertTrue(hasattr(db, 'close'))
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
        self.assertTrue(hasattr(cursor, 'execute'))
        self.assertTrue(hasattr(cursor, 'fetchone'))
        self.assertTrue(hasattr(cursor, 'callproc'))
        self.assertTrue(hasattr(cursor, 'close'))
        self.assertTrue(hasattr(cursor, 'valid'))
        self.assertTrue(cursor.valid)
        self.assertEqual(db._con.open_cursors, 1)
        for i in range(3):
            self.assertEqual(db._usage, i)
            self.assertEqual(db._con.num_uses, i)
            self.assertEqual(db._con.num_queries, i)
            cursor.execute('select test%d' % i)
            self.assertEqual(cursor.fetchone(), 'test%d' % i)
        self.assertTrue(cursor.valid)
        self.assertEqual(db._con.open_cursors, 1)
        for i in range(4):
            cursor.callproc('test')
        cursor.close()
        self.assertTrue(not cursor.valid)
        self.assertEqual(db._con.open_cursors, 0)
        self.assertEqual(db._usage, 7)
        self.assertEqual(db._con.num_uses, 7)
        self.assertEqual(db._con.num_queries, 3)
        cursor.close()
        cursor.execute('select test8')
        self.assertTrue(cursor.valid)
        self.assertEqual(db._con.open_cursors, 1)
        self.assertEqual(cursor.fetchone(), 'test8')
        self.assertEqual(db._usage, 8)
        self.assertEqual(db._con.num_uses, 8)
        self.assertEqual(db._con.num_queries, 4)
        self.assertTrue(db._con.valid)
        db.close()
        self.assertTrue(not db._con.valid)
        self.assertEqual(db._con.open_cursors, 0)
        self.assertEqual(db._usage, 8)
        self.assertEqual(db._con.num_uses, 0)
        self.assertEqual(db._con.num_queries, 0)
        self.assertRaises(InternalError, db._con.close)
        db.close()
        self.assertRaises(InternalError, db._con.cursor)
        cursor = db.cursor()
        self.assertTrue(db._con.valid)
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
        self.assertTrue(cursor.valid)
        cursor.callproc('test')
        cursor._cursor.valid = False
        self.assertTrue(not cursor.valid)
        self.assertRaises(InternalError, cursor._cursor.callproc, 'test')
        cursor.callproc('test')
        self.assertTrue(cursor.valid)
        cursor._cursor.callproc('test')
        self.assertEqual(db._usage, 2)
        self.assertEqual(db._con.num_uses, 3)
        db._con.valid = cursor._cursor.valid = False
        cursor.callproc('test')
        self.assertTrue(cursor.valid)
        self.assertEqual(db._usage, 1)
        self.assertEqual(db._con.num_uses, 1)
        cursor.execute('set doit')
        db.commit()
        cursor.execute('set dont')
        db.rollback()
        self.assertEqual(db._con.session,
            ['doit', 'commit', 'dont', 'rollback'])

    def test05_ConnectionCreatorFunction(self):
        db1 = SteadyDBconnect(dbapi, 0, None, None, None, True,
            'SteadyDBTestDB', user='SteadyDBTestUser')
        db2 = SteadyDBconnect(connect, 0, None, None, None, True,
            'SteadyDBTestDB', user='SteadyDBTestUser')
        self.assertEqual(db1.dbapi(), db2.dbapi())
        self.assertEqual(db1.threadsafety(), db2.threadsafety())
        self.assertEqual(db1._creator, db2._creator)
        self.assertEqual(db1._args, db2._args)
        self.assertEqual(db1._kwargs, db2._kwargs)
        db2.close()
        db1.close()

    def test06_ConnectionMaxUsage(self):
        db = SteadyDBconnect(dbapi, 10)
        cursor = db.cursor()
        for i in range(100):
            cursor.execute('select test%d' % i)
            r = cursor.fetchone()
            self.assertEqual(r, 'test%d' % i)
            self.assertTrue(db._con.valid)
            j = i % 10 + 1
            self.assertEqual(db._usage, j)
            self.assertEqual(db._con.num_uses, j)
            self.assertEqual(db._con.num_queries, j)
        self.assertEqual(db._con.open_cursors, 1)
        for i in range(100):
            cursor.callproc('test')
            self.assertTrue(db._con.valid)
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
            j = (i + (3 if i < 5 else -5)) % 10 + 1
            self.assertEqual(db._usage, j)
            self.assertEqual(db._con.num_uses, j)
            j = 3 if i < 5 else 0
            self.assertEqual(db._con.num_queries, j)
        db.close()
        cursor.execute('select test1')
        self.assertEqual(cursor.fetchone(), 'test1')
        self.assertEqual(db._usage, 1)
        self.assertEqual(db._con.num_uses, 1)
        self.assertEqual(db._con.num_queries, 1)

    def test07_ConnectionSetSession(self):
        db = SteadyDBconnect(dbapi, 3, ('set time zone', 'set datestyle'))
        self.assertTrue(hasattr(db, '_usage'))
        self.assertEqual(db._usage, 0)
        self.assertTrue(hasattr(db._con, 'open_cursors'))
        self.assertEqual(db._con.open_cursors, 0)
        self.assertTrue(hasattr(db._con, 'num_uses'))
        self.assertEqual(db._con.num_uses, 2)
        self.assertTrue(hasattr(db._con, 'num_queries'))
        self.assertEqual(db._con.num_queries, 0)
        self.assertTrue(hasattr(db._con, 'session'))
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

    def test08_ConnectionFailures(self):
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

    def test09_ConnectionFailureError(self):
        db = SteadyDBconnect(dbapi)
        cursor = db.cursor()
        db.close()
        cursor.execute('select test')
        cursor = db.cursor()
        db.close()
        self.assertRaises(ProgrammingError, cursor.execute, 'error')

    def test10_ConnectionSetSizes(self):
        db = SteadyDBconnect(dbapi)
        cursor = db.cursor()
        cursor.execute('get sizes')
        result = cursor.fetchone()
        self.assertEqual(result, ([], {}))
        cursor.setinputsizes([7, 42, 6])
        cursor.setoutputsize(9)
        cursor.setoutputsize(15, 3)
        cursor.setoutputsize(42, 7)
        cursor.execute('get sizes')
        result = cursor.fetchone()
        self.assertEqual(result, ([7, 42, 6], {None: 9, 3: 15, 7: 42}))
        cursor.execute('get sizes')
        result = cursor.fetchone()
        self.assertEqual(result, ([], {}))
        cursor.setinputsizes([6, 42, 7])
        cursor.setoutputsize(7)
        cursor.setoutputsize(15, 3)
        cursor.setoutputsize(42, 9)
        db.close()
        cursor.execute('get sizes')
        result = cursor.fetchone()
        self.assertEqual(result, ([6, 42, 7], {None: 7, 3: 15, 9: 42}))

    def test11_ConnectionPingCheck(self):
        Connection.has_ping = False
        Connection.num_pings = 0
        db = SteadyDBconnect(dbapi)
        db.cursor().execute('select test')
        self.assertEqual(Connection.num_pings, 0)
        db.close()
        db.cursor().execute('select test')
        self.assertEqual(Connection.num_pings, 0)
        self.assertTrue(db._ping_check() is None)
        self.assertEqual(Connection.num_pings, 1)
        db = SteadyDBconnect(dbapi, ping=7)
        db.cursor().execute('select test')
        self.assertEqual(Connection.num_pings, 2)
        db.close()
        db.cursor().execute('select test')
        self.assertEqual(Connection.num_pings, 2)
        self.assertTrue(db._ping_check() is None)
        self.assertEqual(Connection.num_pings, 2)
        Connection.has_ping = True
        db = SteadyDBconnect(dbapi)
        db.cursor().execute('select test')
        self.assertEqual(Connection.num_pings, 2)
        db.close()
        db.cursor().execute('select test')
        self.assertEqual(Connection.num_pings, 2)
        self.assertTrue(db._ping_check())
        self.assertEqual(Connection.num_pings, 3)
        db = SteadyDBconnect(dbapi, ping=1)
        db.cursor().execute('select test')
        self.assertEqual(Connection.num_pings, 3)
        db.close()
        db.cursor().execute('select test')
        self.assertEqual(Connection.num_pings, 3)
        self.assertTrue(db._ping_check())
        self.assertEqual(Connection.num_pings, 4)
        db.close()
        self.assertTrue(db._ping_check())
        self.assertEqual(Connection.num_pings, 5)
        db = SteadyDBconnect(dbapi, ping=7)
        db.cursor().execute('select test')
        self.assertEqual(Connection.num_pings, 7)
        db.close()
        db.cursor().execute('select test')
        self.assertEqual(Connection.num_pings, 9)
        db = SteadyDBconnect(dbapi, ping=3)
        self.assertEqual(Connection.num_pings, 9)
        db.cursor()
        self.assertEqual(Connection.num_pings, 10)
        db.close()
        cursor = db.cursor()
        self.assertEqual(Connection.num_pings, 11)
        cursor.execute('select test')
        self.assertEqual(Connection.num_pings, 11)
        db = SteadyDBconnect(dbapi, ping=5)
        self.assertEqual(Connection.num_pings, 11)
        db.cursor()
        self.assertEqual(Connection.num_pings, 11)
        db.close()
        cursor = db.cursor()
        self.assertEqual(Connection.num_pings, 11)
        cursor.execute('select test')
        self.assertEqual(Connection.num_pings, 12)
        db.close()
        cursor = db.cursor()
        self.assertEqual(Connection.num_pings, 12)
        cursor.execute('select test')
        self.assertEqual(Connection.num_pings, 13)
        db = SteadyDBconnect(dbapi, ping=7)
        self.assertEqual(Connection.num_pings, 13)
        db.cursor()
        self.assertEqual(Connection.num_pings, 14)
        db.close()
        cursor = db.cursor()
        self.assertEqual(Connection.num_pings, 15)
        cursor.execute('select test')
        self.assertEqual(Connection.num_pings, 16)
        db.close()
        cursor = db.cursor()
        self.assertEqual(Connection.num_pings, 17)
        cursor.execute('select test')
        self.assertEqual(Connection.num_pings, 18)
        db.close()
        cursor.execute('select test')
        self.assertEqual(Connection.num_pings, 20)
        Connection.has_ping = False
        Connection.num_pings = 0

    def test12_BeginTransaction(self):
        db = SteadyDBconnect(dbapi, database='ok')
        cursor = db.cursor()
        cursor.close()
        cursor.execute('select test12')
        self.assertEqual(cursor.fetchone(), 'test12')
        db.begin()
        cursor = db.cursor()
        cursor.close()
        self.assertRaises(InternalError, cursor.execute, 'select test12')
        cursor.execute('select test12')
        self.assertEqual(cursor.fetchone(), 'test12')
        db.close()
        db.begin()
        self.assertRaises(InternalError, cursor.execute, 'select test12')
        cursor.execute('select test12')
        self.assertEqual(cursor.fetchone(), 'test12')
        db.begin()
        self.assertRaises(ProgrammingError, cursor.execute, 'error')
        cursor.close()
        cursor.execute('select test12')
        self.assertEqual(cursor.fetchone(), 'test12')

    def test13_WithBeginExtension(self):
        db = SteadyDBconnect(dbapi, database='ok')
        db._con._begin_called_with = None
        def begin(a, b=None, c=7):
            db._con._begin_called_with = (a, b, c)
        db._con.begin = begin
        db.begin(42, 6)
        cursor = db.cursor()
        cursor.execute('select test13')
        self.assertEqual(cursor.fetchone(), 'test13')
        self.assertEqual(db._con._begin_called_with, (42, 6, 7))

    def test14_CancelTransaction(self):
        db = SteadyDBconnect(dbapi, database='ok')
        cursor = db.cursor()
        db.begin()
        cursor.execute('select test14')
        self.assertEqual(cursor.fetchone(), 'test14')
        db.cancel()
        cursor.execute('select test14')
        self.assertEqual(cursor.fetchone(), 'test14')

    def test15_WithCancelExtension(self):
        db = SteadyDBconnect(dbapi, database='ok')
        db._con._cancel_called = None
        def cancel():
            db._con._cancel_called = 'yes'
        db._con.cancel = cancel
        db.begin()
        cursor = db.cursor()
        cursor.execute('select test15')
        self.assertEqual(cursor.fetchone(), 'test15')
        db.cancel()
        self.assertEqual(db._con._cancel_called, 'yes')

    def test16_ResetTransaction(self):
        db = SteadyDBconnect(dbapi, database='ok')
        db.begin()
        self.assertTrue(not db._con.session)
        db.close()
        self.assertTrue(not db._con.session)
        db = SteadyDBconnect(dbapi, database='ok', closeable=False)
        db.begin()
        self.assertTrue(not db._con.session)
        db.close()
        self.assertEqual(db._con.session, ['rollback'])

    def test17_CommitError(self):
        db = SteadyDBconnect(dbapi, database='ok')
        db.begin()
        self.assertTrue(not db._con.session)
        self.assertTrue(db._con.valid)
        db.commit()
        self.assertEqual(db._con.session, ['commit'])
        self.assertTrue(db._con.valid)
        db.begin()
        db._con.valid = False
        con = db._con
        self.assertRaises(InternalError, db.commit)
        self.assertTrue(not db._con.session)
        self.assertTrue(db._con.valid)
        self.assertTrue(con is not db._con)
        db.begin()
        self.assertTrue(not db._con.session)
        self.assertTrue(db._con.valid)
        db.commit()
        self.assertEqual(db._con.session, ['commit'])
        self.assertTrue(db._con.valid)

    def test18_RollbackError(self):
        db = SteadyDBconnect(dbapi, database='ok')
        db.begin()
        self.assertTrue(not db._con.session)
        self.assertTrue(db._con.valid)
        db.rollback()
        self.assertEqual(db._con.session, ['rollback'])
        self.assertTrue(db._con.valid)
        db.begin()
        db._con.valid = False
        con = db._con
        self.assertRaises(InternalError, db.rollback)
        self.assertTrue(not db._con.session)
        self.assertTrue(db._con.valid)
        self.assertTrue(con is not db._con)
        db.begin()
        self.assertTrue(not db._con.session)
        self.assertTrue(db._con.valid)
        db.rollback()
        self.assertEqual(db._con.session, ['rollback'])
        self.assertTrue(db._con.valid)


if __name__ == '__main__':
    unittest.main()
