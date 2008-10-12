"""Test the PersistentDB module.

Note:
We don't test performance here, so the test does not predicate
whether PersistentDB actually will help in improving performance or not.
We also assume that the underlying SteadyDB connections are tested.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke

"""

__version__ = '1.0rc1'
__revision__ = "$Rev$"
__date__ = "$Date$"


import sys
import unittest

sys.path.insert(1, '../..')
# The TestSteadyDB module serves as a mock object for the DB-API 2 module:
from DBUtils import ThreadingLocal
from DBUtils.Testing import TestSteadyDB as dbapi
from DBUtils.PersistentDB import PersistentDB


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

	def test2_PersistentDBClose(self):
		for closeable in (False, True):
			persist = PersistentDB(dbapi, closeable=closeable)
			db = persist.connection()
			self.assert_(db._con.valid)
			db.close()
			self.assert_(closeable ^ db._con.valid)
			db.close()
			self.assert_(closeable ^ db._con.valid)
			db._close()
			self.assert_(not db._con.valid)
			db._close()
			self.assert_(not db._con.valid)

	def test3_PersistentDBConnection(self):
		persist = PersistentDB(dbapi)
		db = persist.connection()
		db_con = db._con
		self.assert_(db_con.database is None)
		self.assert_(db_con.user is None)
		db2 = persist.connection()
		self.assertEqual(db, db2)
		db3 = persist.dedicated_connection()
		self.assertEqual(db, db3)
		db3.close()
		db2.close()
		db.close()

	def test4_PersistentDBThreads(self):
		numThreads = 3
		persist = PersistentDB(dbapi, closeable=True)
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
			self.assert_(threads[i].isAlive())
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
			self.assert_(threads[i].isAlive())
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
			self.assert_(threads[i].isAlive())
		for i in range(numThreads):
			try:
				queryQueue[i].put(None, 1, 1)
			except TypeError:
				queryQueue[i].put(None, 1)

	def test5_PersistentDBMaxUsage(self):
		persist = PersistentDB(dbapi, 20)
		db = persist.connection()
		self.assertEqual(db._maxusage, 20)
		for i in range(100):
			cursor = db.cursor()
			cursor.execute('select test%d' % i)
			r = cursor.fetchone()
			cursor.close()
			self.assertEqual(r, 'test%d' % i)
			self.assert_(db._con.valid)
			j = i % 20 + 1
			self.assertEqual(db._usage, j)
			self.assertEqual(db._con.num_uses, j)
			self.assertEqual(db._con.num_queries, j)

	def test6_PersistentDBSetSession(self):
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

	def test7_PersistentDBThreadLocal(self):
		persist = PersistentDB(dbapi)
		self.assert_(isinstance(persist.thread, ThreadingLocal.local))
		class threadlocal:
			pass
		persist = PersistentDB(dbapi, threadlocal=threadlocal)
		self.assert_(isinstance(persist.thread, threadlocal))


if __name__ == '__main__':
	unittest.main()
