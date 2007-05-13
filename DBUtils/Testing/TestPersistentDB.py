"""Test the PersistentDB module.

Note:
We don't test performance here, so the test does not predicate
whether PersistentDB actually will help in improving performance or not.
We also assume that the underlying SteadyDB connections are tested.

Copyright and credit info:

* This test was contributed by Christoph Zwerschke

"""

__version__ = '0.9.2'
__revision__ = "$Rev$"
__date__ = "$Date$"


import sys
import unittest

sys.path.insert(1, '../..')
# The TestSteadyDB module serves as a mock object for the DB-API 2 module:
from DBUtils.Testing import TestSteadyDB as dbapi
from DBUtils.PersistentDB import PersistentDB


class TestPersistentDB(unittest.TestCase):

	def setUp(self):
		dbapi.threadsafety = 1

	def test0_CheckVersion(self):
		TestPersistentDBVersion = __version__
		from DBUtils.PersistentDB import __version__ as PersistentDBVersion
		self.assertEqual(PersistentDBVersion, TestPersistentDBVersion)

	def test1_NoThreadsafety(self):
		from DBUtils.PersistentDB import NotSupportedError
		for dbapi.threadsafety in (None, 0):
			self.assertRaises(NotSupportedError, PersistentDB, dbapi)

	def test2_PersistentDBClose(self):
		for closeable in (0, 1):
			persist = PersistentDB(dbapi)
			persist._closeable = closeable
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

	def test3_PersistentDBThreads(self):
		numThreads = 3
		persist = PersistentDB(dbapi)
		persist._closeable = 1
		from Queue import Queue, Empty
		queryQueue, resultQueue = [], []
		for i in range(numThreads):
			queryQueue.append(Queue(1))
			resultQueue.append(Queue(1))
		def runQueries(i):
			this_db = persist.connection()
			while 1:
				try:
					q = queryQueue[i].get(1, 1)
				except Empty:
					q = None
				if not q: break
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
				resultQueue[i].put(r, 1, 0.1)
			db.close()
		from threading import Thread
		threads = []
		for i in range(numThreads):
			thread = Thread(target=runQueries, args=(i,))
			threads.append(thread)
			thread.start()
		for i in range(numThreads):
			queryQueue[i].put('ping', 1, 0.1)
		for i in range(numThreads):
			r = resultQueue[i].get(1, 0.1)
			self.assertEqual(r, '%d(0): ok - thread alive' % i)
			self.assert_(threads[i].isAlive())
		for i in range(numThreads):
			for j in range(i + 1):
				queryQueue[i].put('select test%d' % j, 1, 0.1)
				r = resultQueue[i].get(1, 0.1)
				self.assertEqual(r, '%d(%d): test%d' % (i, j + 1, j))
		queryQueue[1].put('select test4', 1, 0.1)
		r = resultQueue[1].get(1, 0.1)
		self.assertEqual(r, '1(3): test4')
		queryQueue[1].put('close', 1, 0.1)
		r = resultQueue[1].get(1, 0.1)
		self.assertEqual(r, '1(0): ok - connection closed')
		for j in range(2):
			queryQueue[1].put('select test%d' % j, 1, 0.1)
			r = resultQueue[1].get(1, 0.1)
			self.assertEqual(r, '1(%d): test%d' % (j + 1, j))
		for i in range(numThreads):
			self.assert_(threads[i].isAlive())
			queryQueue[i].put('ping', 1, 0.1)
		for i in range(numThreads):
			r = resultQueue[i].get(1, 0.1)
			self.assertEqual(r, '%d(%d): ok - thread alive' % (i, i + 1))
			self.assert_(threads[i].isAlive())
		for i in range(numThreads):
			queryQueue[i].put(None, 1, 1)

	def test4_PersistentDBMaxUsage(self):
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

	def test5_PersistentDBSetSession(self):
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


if __name__ == '__main__':
	unittest.main()
