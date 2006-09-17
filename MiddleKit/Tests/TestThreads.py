from Test import Test
import threading


class TestThreads(Test):

	def __init__(self):
		Test.__init__(self)
		self._numObjects = 64
		self._numThreads = [1, 2, 4, 8, 16, 32]
		self._numReads   = 32

	def timedMain(self):
		import time
		start = time.time()
		self.main()
		end = time.time()
		duration = end - start
		print
		print 'secs: %0.2f' % duration
		print 'mins: %0.2f' % (duration/60.0)

	def readArgs(self, args):
		self._modelNames = ['MKBasic']

	def testEmpty(self):
		self.createDatabase()
		self.createStore()
		self.createObjects()
		self.testConcurrentReads()

	def createStore(self):
		from MiddleKit.Run.MySQLObjectStore import MySQLObjectStore
		self._store = MySQLObjectStore()
		self._store.readModelFileNamed(self._modelName)

	def createObjects(self):
		from Thing import Thing
		for i in range(self._numObjects):
			t = Thing()
			t.setB(1)
			t.setI(2)
			t.setL(3)
			t.setF(4.0)
			t.setS('five')
			self._store.addObject(t)
		self._store.saveChanges()
		things = self._store.fetchObjectsOfClass('Thing')
		assert len(things)==self._numObjects, '%i, %i' % (len(things), self._numObjects)

	def testConcurrentReads(self):
		for numThreads in self._numThreads:
			print '>> numThreads:', numThreads
			self.testReaderThreads(numThreads)

	def testReaderThreads(self, numThreads):

		class Reader(threading.Thread):

			def __init__(self, store, numReads):
				threading.Thread.__init__(self)
				self._store = store
				self._numReads = numReads

			def run(self):
				store = self._store
				for i in range(self._numReads):
					#print '%x:%03i' % (id(self), i),
					objects = store.fetchObjectsOfClass('Thing')

		threads = []
		for i in range(numThreads):
			thread = Reader(self._store, self._numReads)
			threads.append(thread)

		for thread in threads:
			thread.start()

		for thread in threads:
			thread.join()

	def testSamples(self):
		"""
		We do all our necessary testing in testEmpty() so we override
		this method to pass.
		"""
		pass


if __name__=='__main__':
	import sys
	sys.setcheckinterval(100)
	TestThreads().timedMain()
