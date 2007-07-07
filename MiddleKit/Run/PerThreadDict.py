import thread


class PerThreadDict:
	"""Per-thread dictionary.

	PerThreadDict behaves like a normal dict, but changes to it are kept
	track of on a per-thread basis.  So if thread A adds a key/value pair
	to the dict, only thread A sees that item.  There are a few non-standard
	methods (clear, isEmpty), too.

	This is implementated by keeping a dictionary of dictionaries; one for
	each thread. The implementation is not a complete dict wrapper; only
	some methods are implemented. If more methods are needed, see UserDict
	(in the standard Python lib) for inspiration.

	"""

	def __init__(self):
		self.data = {}

	def __repr__(self): return repr(self.data)

	def __setitem__(self, key, item, gettid=thread.get_ident):
		threadid = gettid()
		try:
			dict = self.data[threadid]
		except KeyError:
			dict = self.data[threadid] = {}
		dict[key] = item

	def clear(self, allThreads=0, gettid=thread.get_ident):
		if allThreads:
			self.data = {}
		else:
			threadid = gettid()
			try:
				self.data[threadid].clear()
			except KeyError:
				pass

	def isEmpty(self):
		for l in self.data.values():
			if l:
				return 0
		return 1

	def values(self, allThreads=0, gettid=thread.get_ident):
		if allThreads:
			r = []
			for l in self.data.values():
				r.extend(l.values())
			return r
		else:
			threadid = gettid()
			try:
				return self.data[threadid].values()
			except:
				return []

	def __len__(self, gettid=thread.get_ident):
		threadid = gettid()
		try:
			return len(self.data[threadid])
		except KeyError:
			return 0


class NonThreadedDict:
	"""Non-threaded dictionary.

	NonThreadedDict behaves like a normal dict.  It's only purpose is
	to provide a compatible interface to PerThreadDict, so that they
	can be used interchangeably.

	"""

	def __init__(self):
		self.data = {}

	def __repr__(self):
		return repr(self.data)

	def __setitem__(self, key, item):
		self.data[key] = item

	def clear(self, allThreads=0):
		self.data.clear()

	def isEmpty(self):
		return len(self.data) == 0

	def values(self, allThreads=0):
		return self.data.values()

	def __len__(self):
		return len(self.data)


if __name__ == '__main__':
	# just a few tests used in development
	def addItems():
		global d
		d[4] = 'four'
		d[5] = 'five'
	global d
	d = PerThreadDict()
	for i in d.values():
		print i
	d[1] = 'one'
	assert len(d) == 1
	d[2] = 'two'
	d[3] = 'three'
	assert len(d) == 3
	for i in d.values():
		print i
	from threading import Thread
	t = Thread(target=addItems)
	t.start()
	t.join()
	assert len(d) == 3
	assert len(d.values()) == 3
	assert len(d.values(allThreads=1)) == 5
	d.clear()
	assert len(d.values(allThreads=1)) == 2
	d.clear(allThreads=1)
	assert len(d.values(allThreads=1)) == 0
