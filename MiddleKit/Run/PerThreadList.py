#from UserListimport UserList
#from UserDict import UserDict

import thread


class PerThreadList:
	"""Per-thread list.

	PerThreadList behaves like a normal list, but changes to it are kept
	track of on a per-thread basis.  So if thread A appends an item to
	the list, only thread A sees that item.  There are a few non-standard
	methods (clear, isEmpty), too.

	This is implementated by keeping a dictionary of lists; one for each
	thread. The implementation is not a complete list wrapper; only some
	methods are implemented. If more methods are needed, see UserList
	(in the standard Python lib) for inspiration.

	"""

	def __init__(self):
		self.data = {}

	def append(self, item, gettid=thread.get_ident):
		threadid = gettid()
		try:
			self.data[threadid].append(item)
		except KeyError:
			self.data[threadid] = [item]

	def extend(self, list, gettid=thread.get_ident):
		threadid = gettid()
		try:
			self.data[threadid].extend(list)
		except KeyError:
			self.data[threadid] = list

	def clear(self, allThreads=0, gettid=thread.get_ident):
		"""Erases the list, either for the current thread or for all threads.

		We need this method, because it obviously won't work for user code
		to do: list = [].

		"""
		if allThreads:
			self.data = {}
		else:
			threadid = gettid()
			try:
				self.data[threadid] = []
			except:
				pass

	def items(self, allThreads=0, gettid=thread.get_ident):
		if allThreads:
			items = []
			for l in self.data.values():
				items.extend(l)
			return items
		else:
			threadid = gettid()
			try:
				return self.data[threadid]
			except KeyError:
				return []

	def isEmpty(self, gettid=thread.get_ident):
		"""Test if the list is empty for all threads."""
		for l in self.data.values():
			if l:
				return 0
		return 1

	def __len__(self, gettid=thread.get_ident):
		threadid = gettid()
		try:
			return len(self.data[threadid])
		except KeyError:
			return 0

	def __getitem__(self,  i, gettid=thread.get_ident):
		threadid = gettid()
		if self.data.has_key(threadid):
			return self.data[threadid][i]
		else:
			return [][i]


class NonThreadedList:
	"""Non-threaded list.

	NonThreadedList behaves like a normal list.  It's only purpose is
	to provide a compatible interface to PerThreadList, so that they
	can be used interchangeably.

	"""

	def __init__(self):
		self.data = []

	def append(self, item):
		self.data.append(item)

	def extend(self, list):
		self.data.extend(list)

	def items(self, allThreads=0):
		return self.data

	def clear(self, allThreads=0):
		"""Erases the list.

		We need this method, because it obviously won't work for user code
		to do: list = [].

		"""
		self.data = []

	def __len__(self):
		return len(self.data)

	def __getitem__(self, i):
		return self.data[i]

	def isEmpty(self):
		"""Test if the list is empty for all threads."""
		return len(self.data) == 0


if __name__ == '__main__':
	# just a few tests used in development
	def addItems():
		global l
		l.append(1)
		l.append(2)
	global l
	l = PerThreadList()
	for i in l:
		print i
	l.append(1)
	assert len(l) == 1
	l.append(2)
	l.append(3)
	assert len(l) == 3
	for i in l:
		print i
	from threading import Thread
	t = Thread(target=addItems)
	t.start()
	t.join()
	assert len(l) == 3
	assert len(l.items()) == 3
	assert len(l.items(allThreads=1)) == 5
	l.clear()
	assert len(l.items(allThreads=1)) == 2
	l.clear(allThreads=1)
	assert len(l.items(allThreads=1)) == 0

