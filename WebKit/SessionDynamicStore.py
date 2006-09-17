from SessionStore import SessionStore
import SessionMemoryStore, SessionFileStore
import os, time, threading

debug = 0

class SessionDynamicStore(SessionStore):
	"""Stores the session in Memory and Files.

	This can be used either in a persistent app server or a cgi framework.

	To use this Session Store, set SessionStore in Application.config
	to 'Dynamic'. Other variables which can be set in Application.config are:

	'MaxDynamicMemorySessions', which sets the maximum number of sessions
	that can be in the Memory SessionStore at one time. Default is 10,000.

	'DynamicSessionTimeout', which sets the default time for a session to stay
	in memory with no activity. Default is 15 minutes. When specifying this in
	Application.config, use minutes.

	"""


	## Init ##

	def __init__(self, app):
		# Create both a file store and a memory store
		SessionStore.__init__(self, app)
		self._fileStore = SessionFileStore.SessionFileStore(app)
		self._memoryStore = SessionMemoryStore.SessionMemoryStore(
			app, restoreFiles=0)
		self._memoryStore.clear()  #fileStore will have the files on disk

		# moveToFileInterval specifies after what period of time
		# a session is automatically moved to file
		self._moveToFileInterval = self.application().setting(
			'DynamicSessionTimeout', 15) * 60

		# maxDynamicMemorySessions is what the user actually sets
		# in Application.config
		self._maxDynamicMemorySessions = self.application().setting(
			'MaxDynamicMemorySessions', 10000)

		# Used to keep track of sweeping the file store
		self._fileSweepCount = 0

		# Create a re-entrant lock for thread synchronization. The lock is used
		# to protect all code that modifies the contents of the file store and
		# all code that moves sessions between the file and memory stores, and
		# is also used to protect code that searches in the file store for a
		# session. Using the lock in this way avoids a bug that used to be in
		#this code, where a session was temporarily neither in the file store
		# nor in the memory store while it was being moved from file to memory.
		self._lock = threading.RLock()

		if debug:
			print "SessionDynamicStore Initialized"

	## Access ##

	def __len__(self):
		self._lock.acquire()
		try:
			return len(self._memoryStore) + len(self._fileStore)
		finally:
			self._lock.release()

	def __getitem__(self, key):
		# First try to grab the session from the memory store without locking,
		# for efficiency. Only if that fails do we acquire the lock and look
		# in the file store.
		try:
			return self._memoryStore[key]
		except KeyError:
			self._lock.acquire()
			try:
				if self._fileStore.has_key(key):
					self.MovetoMemory(key)
				#let it raise a KeyError otherwise
				return self._memoryStore[key]
			finally:
				self._lock.release()


	def __setitem__(self, key, item):
		self._memoryStore[key] = item
		# @@ 2001-12-11 gat: Seems like a waste of time to attempt to delete the
		# session from the file store on every single write operation. I see no
		# harm in commenting out the rest of this method.
		#	try:
		#		del self._fileStore[key]
		#	except KeyError:
		#		pass

	def __delitem__(self, key):
		self._lock.acquire()
		try:
			try:
				del self._memoryStore[key]
			except KeyError:
				pass
			try:
				del self._fileStore[key]
			except KeyError:
				pass
		finally:
			self._lock.release()

	def has_key(self, key):
		# First try to find the session in the memory store without locking,
		# for efficiency.  Only if that fails do we acquire the lock and
		# look in the file store.
		if self._memoryStore.has_key(key):
			return 1
		self._lock.acquire()
		try:
			return self._memoryStore.has_key(key) or self._fileStore.has_key(key)
		finally:
			self._lock.release()

	def keys(self):
		self._lock.acquire()
		try:
			return self._memoryStore.keys() + self._fileStore.keys()
		finally:
			self._lock.release()

	def clear(self):
		self._lock.acquire()
		try:
			self._memoryStore.clear()
			self._fileStore.clear()
		finally:
			self._lock.release()

	def setdefault(self, key, default):
		self._lock.acquire()
		try:
			try:
				return self[key]
			except KeyError:
				self[key] = default
				return default
		finally:
			self._lock.release()

	def MovetoMemory(self, key):
		self._lock.acquire()
		try:
			global debug
			if debug: print ">> Moving %s to Memory" % key
			self._memoryStore[key] = self._fileStore[key]
			self._fileStore.removeKey(key)
		finally:
			self._lock.release()

	def MovetoFile(self, key):
		self._lock.acquire()
		try:
			global debug
			if debug: print ">> Moving %s to File" % key
			self._fileStore[key] = self._memoryStore[key]
			del self._memoryStore[key]
		finally:
			self._lock.release()

	def setEncoderDecoder(self, encoder, decoder):
		# @@ 2002-11-26 jdh: # propogate the encoder/decoder to the
		# underlying SessionFileStore
		self._fileStore.setEncoderDecoder(encoder, decoder)
		SessionStore.setEncoderDecoder(self,encoder,decoder)

	## Application support ##

	def storeSession(self, session):
		pass

	def storeAllSessions(self):
		self._lock.acquire()
		try:
			for i in self._memoryStore.keys():
				self.MovetoFile(i)
		finally:
			self._lock.release()

	def cleanStaleSessions(self, task=None):
		"""Clean stale sessions.

		Called by the Application to tell this store to clean out all sessions
		that have exceeded their lifetime.
		We want to have their native class functions handle it, though.

		Ideally, intervalSweep would be run more often than the
		cleanStaleSessions functions for the actual stores.
		This may need to wait until we get the TaskKit in place, though.

		The problem is the FileStore.cleanStaleSessions can take a while to run.
		So here, we only run the file sweep every fourth time.

		"""
		if debug: print "Session Sweep started"
		try:
			if self._fileSweepCount == 0:
				self._fileStore.cleanStaleSessions(task)
			self._memoryStore.cleanStaleSessions(task)
		except KeyError:
			pass
		if self._fileSweepCount < 4:
			self._fileSweepCount = self._fileSweepCount + 1
		else:
			self._fileSweepCount = 0
		# Now move sessions from memory to file as necessary:
		self.intervalSweep()


# It's OK for a session to moved from memory to file or vice versa in between
# the time we get the keys and the time we actually ask for the session's
# access time. It may take a while for the fileStore sweep to get completed.


	def intervalSweep(self):
		"""The session sweeper interval function.

		The interval function moves sessions from memory to file
		and can be run more often than the full cleanStaleSessions function.

		"""
		global debug
		if debug:
			print "Starting interval Sweep at %s" % time.ctime(time.time())
			print "Memory Sessions: %s   FileSessions: %s" % (
				len(self._memoryStore), len(self._fileStore))
			print "maxDynamicMemorySessions = %s" % self._maxDynamicMemorySessions
			print "moveToFileInterval = %s" % self._moveToFileInterval

		now = time.time()

		delta = now - self._moveToFileInterval
		for i in self._memoryStore.keys():
			try:
				if self._memoryStore[i].lastAccessTime() < delta:
					self.MovetoFile(i)
			except KeyError:
				pass

		if len(self._memoryStore) > self._maxDynamicMemorySessions:
			keys = self.memoryKeysInAccessTimeOrder()
			excess = len(self._memoryStore) - self._maxDynamicMemorySessions
			if debug:
				print excess, "sessions beyond the limit"
			for i in keys[:excess]:
				try:
					self.MovetoFile(i)
				except KeyError:
					pass

		if debug:
			print "Finished interval Sweep at %s" % time.ctime(time.time())
			print "Memory Sessions: %s   FileSessions: %s" % (
				len(self._memoryStore), len(self._fileStore))


	def memoryKeysInAccessTimeOrder(self):
		"""Return memory store's keys in ascending order of last access time."""
		# This sorting technique is faster than using a comparison function.
		accessTimeAndKeys = []
		for key in self._memoryStore.keys():
			try:
				accessTimeAndKeys.append((self._memoryStore[key].lastAccessTime(), key))
			except KeyError:
				pass
		accessTimeAndKeys.sort()
		keys = []
		for accessTime, key in accessTimeAndKeys:
			keys.append(key)
		return keys
