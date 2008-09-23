"""Test the SteadyPg module.

Note:
We do not test the real PyGreSQL module, but we just
mock the basic connection functionality of that module.
We assume that the PyGreSQL module will detect lost
connections correctly and set the status flag accordingly.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke

"""

__version__ = '0.9.4'
__revision__ = "$Rev$"
__date__ = "$Date$"


import sys

# This module also serves as a mock object for the pg API module:

sys.modules['pg'] = sys.modules[__name__]

class Error(StandardError): pass
class DatabaseError(Error): pass
class InternalError(DatabaseError): pass
class ProgrammingError(DatabaseError): pass


def connect(*args, **kwargs):
	return pgConnection(*args, **kwargs)


class pgConnection:
	"""The underlying pg API connection class."""

	def __init__(self, dbname=None, user=None):
		self.db = dbname
		self.user = user
		self.num_queries = 0
		self.session = []
		if dbname == 'error':
			self.status = 0
			self.valid = 0
			raise InternalError
		self.status = 1
		self.valid = 1

	def close(self):
		if not self.valid:
			raise InternalError
		self.num_queries = 0
		self.session = []
		self.status = 0
		self.valid = 0

	def reset(self):
		self.num_queries = 0
		self.session = []
		self.status = 1
		self.valid = 1

	def query(self, qstr):
		if not self.valid:
			raise InternalError
		if qstr.startswith('select '):
			self.num_queries += 1
			return qstr[7:]
		elif qstr.startswith('set '):
			self.session.append(qstr[4:])
			return None
		else:
			raise ProgrammingError


class DB:
	"""Wrapper class for the pg API connection class."""

	def __init__(self, *args, **kw):
		self.db = connect(*args, **kw)
		self.dbname = self.db.db
		self.__args = args, kw

	def __getattr__(self, name):
		if self.db:
			return getattr(self.db, name)
		else:
			raise InternalError

	def close(self):
		if self.db:
			self.db.close()
			self.db = None
		else:
			raise InternalError

	def reopen(self):
		if self.db:
			self.close()
		try:
			self.db = connect(*self.__args[0], **self.__args[1])
		except Exception:
			self.db = None
			raise

	def query(self, qstr):
		if not self.db:
			raise InternalError
		return self.db.query(qstr)

	def get_tables(self):
		if not self.db:
			raise InternalError
		return 'test'


import unittest
sys.path.insert(1, '../..')
from DBUtils.SteadyPg import SteadyPgConnection


class TestSteadyPg(unittest.TestCase):

	def test0_CheckVersion(self):
		TestSteadyPgVersion = __version__
		from DBUtils.SteadyPg import __version__ as SteadyPgVersion
		self.assertEqual(SteadyPgVersion, TestSteadyPgVersion)
		self.assertEqual(SteadyPgVersion, SteadyPgConnection.version)

	def test1_MockedPgConnection(self):
		PgConnection = DB
		db = PgConnection('SteadyPgTestDB',
			user='SteadyPgTestUser')
		self.assert_(hasattr(db, 'db'))
		self.assert_(hasattr(db.db, 'status'))
		self.assert_(db.db.status)
		self.assert_(hasattr(db.db, 'query'))
		self.assert_(hasattr(db.db, 'close'))
		self.assert_(not hasattr(db.db, 'reopen'))
		self.assert_(hasattr(db, 'reset'))
		self.assert_(hasattr(db.db, 'num_queries'))
		self.assert_(hasattr(db.db, 'session'))
		self.assert_(not hasattr(db.db, 'get_tables'))
		self.assert_(hasattr(db.db, 'db'))
		self.assertEqual(db.db.db, 'SteadyPgTestDB')
		self.assert_(hasattr(db.db, 'user'))
		self.assertEqual(db.db.user, 'SteadyPgTestUser')
		self.assert_(hasattr(db, 'query'))
		self.assert_(hasattr(db, 'close'))
		self.assert_(hasattr(db, 'reopen'))
		self.assert_(hasattr(db, 'reset'))
		self.assert_(hasattr(db, 'num_queries'))
		self.assert_(hasattr(db, 'session'))
		self.assert_(hasattr(db, 'get_tables'))
		self.assert_(hasattr(db, 'dbname'))
		self.assertEqual(db.dbname, 'SteadyPgTestDB')
		self.assert_(hasattr(db, 'user'))
		self.assertEqual(db.user, 'SteadyPgTestUser')
		for i in range(3):
			self.assertEqual(db.num_queries, i)
			self.assertEqual(db.query('select test%d' % i),
				'test%d' % i)
		self.assert_(db.db.status)
		db.reopen()
		self.assert_(db.db.status)
		self.assertEqual(db.num_queries, 0)
		self.assertEqual(db.query('select test4'), 'test4')
		self.assertEqual(db.get_tables(), 'test')
		db.close()
		try:
			status = db.db.status
		except AttributeError:
			status = 0
		self.assert_(not status)
		self.assertRaises(InternalError, db.close)
		self.assertRaises(InternalError, db.query, 'select test')
		self.assertRaises(InternalError, db.get_tables)

	def test2_BrokenPgConnection(self):
		db = SteadyPgConnection(dbname='ok')
		InternalError = sys.modules[db._con.__module__].InternalError
		for i in range(3):
			db.close()
		del db
		self.assertRaises(InternalError, SteadyPgConnection,
			dbname='error')

	def test3_SteadyPgClose(self):
		for closeable in (0, 1):
			db = SteadyPgConnection(closeable=closeable)
			self.assert_(db._con.db and db._con.valid)
			db.close()
			self.assert_(closeable ^
				(db._con.db is not None and db._con.valid))
			db.close()
			self.assert_(closeable ^
				(db._con.db is not None and db._con.valid))
			db._close()
			self.assert_(not db._con.db or not db._con.valid)
			db._close()
			self.assert_(not db._con.db or not db._con.valid)

	def test4_SteadyPgConnection(self):
		db = SteadyPgConnection(0, None, 1,
			'SteadyPgTestDB', user='SteadyPgTestUser')
		self.assert_(hasattr(db, 'db'))
		self.assert_(hasattr(db, '_con'))
		self.assertEqual(db.db, db._con.db)
		self.assert_(hasattr(db, '_usage'))
		self.assertEqual(db._usage, 0)
		self.assert_(hasattr(db.db, 'status'))
		self.assert_(db.db.status)
		self.assert_(hasattr(db.db, 'query'))
		self.assert_(hasattr(db.db, 'close'))
		self.assert_(not hasattr(db.db, 'reopen'))
		self.assert_(hasattr(db.db, 'reset'))
		self.assert_(hasattr(db.db, 'num_queries'))
		self.assert_(hasattr(db.db, 'session'))
		self.assert_(hasattr(db.db, 'db'))
		self.assertEqual(db.db.db, 'SteadyPgTestDB')
		self.assert_(hasattr(db.db, 'user'))
		self.assertEqual(db.db.user, 'SteadyPgTestUser')
		self.assert_(not hasattr(db.db, 'get_tables'))
		self.assert_(hasattr(db, 'query'))
		self.assert_(hasattr(db, 'close'))
		self.assert_(hasattr(db, 'reopen'))
		self.assert_(hasattr(db, 'reset'))
		self.assert_(hasattr(db, 'num_queries'))
		self.assert_(hasattr(db, 'session'))
		self.assert_(hasattr(db, 'dbname'))
		self.assertEqual(db.dbname, 'SteadyPgTestDB')
		self.assert_(hasattr(db, 'user'))
		self.assertEqual(db.user, 'SteadyPgTestUser')
		self.assert_(hasattr(db, 'get_tables'))
		for i in range(3):
			self.assertEqual(db._usage, i)
			self.assertEqual(db.num_queries, i)
			self.assertEqual(db.query('select test%d' % i),
				'test%d' % i)
		self.assert_(db.db.status)
		self.assertEqual(db.get_tables(), 'test')
		self.assert_(db.db.status)
		self.assertEqual(db._usage, 4)
		self.assertEqual(db.num_queries, 3)
		db.reopen()
		self.assert_(db.db.status)
		self.assertEqual(db._usage, 0)
		self.assertEqual(db.num_queries, 0)
		self.assertEqual(db.query('select test'), 'test')
		self.assert_(db.db.status)
		self.assert_(hasattr(db._con, 'status'))
		self.assert_(db._con.status)
		self.assert_(hasattr(db._con, 'close'))
		self.assert_(hasattr(db._con, 'query'))
		db.close()
		try:
			status = db.db.status
		except AttributeError:
			status = 0
		self.assert_(not status)
		self.assert_(hasattr(db._con, 'close'))
		self.assert_(hasattr(db._con, 'query'))
		InternalError = sys.modules[db._con.__module__].InternalError
		self.assertRaises(InternalError, db._con.close)
		self.assertRaises(InternalError, db._con.query, 'select test')
		self.assertEqual(db.query('select test'), 'test')
		self.assert_(db.db.status)
		self.assertEqual(db._usage, 1)
		self.assertEqual(db.num_queries, 1)
		db.db.status = 0
		self.assert_(not db.db.status)
		self.assertEqual(db.query('select test'), 'test')
		self.assert_(db.db.status)
		self.assertEqual(db._usage, 1)
		self.assertEqual(db.num_queries, 1)
		db.db.status = 0
		self.assert_(not db.db.status)
		self.assertEqual(db.get_tables(), 'test')
		self.assert_(db.db.status)
		self.assertEqual(db._usage, 1)
		self.assertEqual(db.num_queries, 0)

	def test5_SteadyPgConnectionMaxUsage(self):
		db = SteadyPgConnection(10)
		for i in range(100):
			r = db.query('select test%d' % i)
			self.assertEqual(r, 'test%d' % i)
			self.assert_(db.db.status)
			j = i % 10 + 1
			self.assertEqual(db._usage, j)
			self.assertEqual(db.num_queries, j)
		for i in range(100):
			r = db.get_tables()
			self.assertEqual(r, 'test')
			self.assert_(db.db.status)
			j = i % 10 + 1
			self.assertEqual(db._usage, j)
			self.assertEqual(db.num_queries, 0)
		for i in range(10):
			if i == 7:
				db.db.status = 0
			r = db.query('select test%d' % i)
			self.assertEqual(r, 'test%d' % i)
			j = i % 7 + 1
			self.assertEqual(db._usage, j)
			self.assertEqual(db.num_queries, j)
		for i in range(10):
			if i == 5:
				db.db.status = 0
			r = db.get_tables()
			self.assertEqual(r, 'test')
			j = (i + (i < 5 and 3 or -5)) % 10 + 1
			self.assertEqual(db._usage, j)
			j = i < 5 and 3 or 0
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

	def test6_SteadyPgConnectionSetSession(self):
		db = SteadyPgConnection(3, ('set time zone', 'set datestyle'))
		self.assert_(hasattr(db, 'num_queries'))
		self.assertEqual(db.num_queries, 0)
		self.assert_(hasattr(db, 'session'))
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


if __name__ == '__main__':
	unittest.main()
