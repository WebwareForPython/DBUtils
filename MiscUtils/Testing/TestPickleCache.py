"""
def readPickleCache(filename, pickleVersion=1, source=None, verbose=None):
	PickleCacheReader().read(filename, pickleVersion, source, verbose)

def writePickleCache(data, filename, pickleVersion=1, source=None, verbose=None):
	PickleCacheWriter().write(data, filename, pickleVersion, source, verbose)
"""

import unittest
import os
import time
from MiscUtils.PickleCache import *

# the directory that this file is in:
# from FixPath import progDir
progPath = os.path.join(os.getcwd(), __file__)
progDir = os.path.dirname(progPath)
assert os.path.basename(progDir) == 'Testing' and \
	os.path.basename(os.path.dirname(progDir)) == 'MiscUtils', \
	'Test needs to run in Testing/MiscUtils.'


class TestPickleCache(unittest.TestCase):

	def test(self):
		# print 'Testing PickleCache...'
		iterations = 2
		for iter in range(iterations):
			# print 'Iteration', iter + 1
			self.oneIterTest()
		# print 'Success.'

	def oneIterTest(self):
		sourcePath = self._sourcePath = os.path.join(progDir, 'foo.dict')
		picklePath = self._picklePath = PickleCache().picklePath(sourcePath)
		self.remove(picklePath) # make sure we're clean
		data = self._data = {'x': 1}
		self.writeSource()
		try:
			# test 1: no pickle cache yet
			assert readPickleCache(sourcePath) is None
			self.writePickle()
			if havePython22OrGreater:
				# test 2: correctness
				assert readPickleCache(sourcePath) == data, \
					repr(readPickleCache(sourcePath))
				# test 3: wrong pickle version
				assert readPickleCache(sourcePath, pickleVersion=2) is None
				self.writePickle() # restore
				# test 4: wrong data source
				assert readPickleCache(sourcePath, source='notTest') is None
				self.writePickle() # restore
				# test 5: wrong Python version
				try:
					saveVersion = sys.version_info
					sys.version_info = (sys.version_info[0] + 1,) \
						+ sys.version_info[1:]
					assert readPickleCache(sourcePath) is None
					self.writePickle() # restore
				finally:
					sys.version_info = saveVersion
				# test 6: source is newer
				self.remove(picklePath)
				self.writePickle()
				# we have to allow for the granularity of getmtime()
				# (see the comment in the docstring of PickleCache.py)
				time.sleep(2)
				self.writeSource()
				assert readPickleCache(sourcePath) is None
				self.writePickle() # restore
		finally:
			self.remove(sourcePath)
			self.remove(picklePath)

	def remove(self, filename):
		try:
			os.remove(filename)
		except OSError:
			pass

	def writeSource(self):
		f = open(self._sourcePath, 'w')
		f.write(str(self._data))
		f.close()

	def writePickle(self):
		assert not os.path.exists(self._picklePath)
		writePickleCache(self._data, self._sourcePath, pickleVersion=1, source='test')
		if havePython22OrGreater:
			assert os.path.exists(self._picklePath)


if __name__ == '__main__':
	TestPickleCache().test()
