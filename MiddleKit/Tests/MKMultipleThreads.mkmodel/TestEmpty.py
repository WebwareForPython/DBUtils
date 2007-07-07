from threading import Thread, Semaphore, Event
from Person import Person
import time

# from Python docs on random module
def create_generators(num, delta, firstseed=None):
	"""Return list of num distinct generators.
	Each generator has its own unique segment of delta elements
	from Random.random()'s full period.
	Seed the first generator with optional arg firstseed (default
	is None, to seed from current time).
	"""

	from random import Random
	g = Random(firstseed)
	result = [g]
	for i in range(num - 1):
		laststate = g.getstate()
		g = Random()
		g.setstate(laststate)
		g.jumpahead(delta)
		result.append(g)
	return result


def test(store):
	"""
	This tests that the ObjectStore can track new, changed and deleted objects
	on a per-thread basis, so that one thread calling store.saveChanges() doesn't
	commit objects which a different thread added.
	"""

	# store.hasChangesForCurrentThread()
	# store.saveAllChanges()

	class Worker(Thread):

		def __init__(self, store, random, saveEvent, cycles):
			Thread.__init__(self)
			self._store = store
			self._random = random
			self._numCycles = cycles
			self._saveEvent = saveEvent
			self._finished = Semaphore(0)

		def waitUntilFinished(self):
			""" Called by a different thread to wait until this thread is finished. """
			self._finished.acquire()

		def waitRandom(self):
			delay = self._random.uniform(0, 2)
			self.debug('sleeping %.02f seconds' % delay)
			time.sleep(delay)

		def debug(self, msg):
			print '%s: %s' % (self.getName(), msg)

		def create(self):
			""" create and add an object to the store """
			store = self._store
			p = Person()
			p.setId('bob')
			p.setFirstName('Robert')
			store.addObject(p)
			self.waitRandom()
			assert store.hasChangesForCurrentThread()
			store.saveChanges()
			assert p.isInStore()
			assert not store.hasChangesForCurrentThread()
			return p

		def modify(self, p):
			""" modify an object, then save the changes to the store """
			store = self._store
			p.setFirstName('bobbie')
			p.setFirstName('Roberta')
			self.waitRandom()
			assert p.isInStore()
			assert p.isChanged()
			assert store.hasChangesForCurrentThread()
			store.saveChanges()
			assert not p.isChanged()
			assert not store.hasChangesForCurrentThread()

		def delete(self, p):
			""" delete an object, then save the changes to the store """
			store = self._store
			store.deleteObject(p)
			self.waitRandom()
			assert p.isInStore()
			assert store.hasChangesForCurrentThread()
			store.saveChanges()
			assert not store.hasChangesForCurrentThread()


		def run(self):
			for i in range(self._numCycles):
				p = self.create()
				self.modify(p)
				self.delete(p)

			# now create and modify an object, but don't save
			p = self.create()
			p.setFirstName('bobbie')
			p.setFirstName('Roberta')

			self._finished.release() # signal the main thread that we're done
			self.debug('waiting for main thread to save changes')
			self._saveEvent.wait()	# wait until the main thread has saved all changes
			assert not p.isChanged(), "Modifications didn't get saved."
			assert not self._store.hasChangesForCurrentThread()


	numthreads = 5
	workers = []
	gens = create_generators(numthreads, 1000000)
	allsaved = Event()
	for i in range(0, numthreads):
		t = Worker(store, gens[i], allsaved, 10)
		t.start()
		workers.append(t)

	for t in workers:
		t.waitUntilFinished()
	print 'main thread: saving all changes'
	store.saveAllChanges()
	allsaved.set()
	assert not store.hasChanges()

	for t in workers:
		t.join()
