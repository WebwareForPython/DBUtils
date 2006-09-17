#!/usr/bin/env python
import FixPath
from glob import glob
from DataTable import DataTable
from profile import Profile
import sys, time


class BenchDataTable:

	def __init__(self, profile=1, runTestSuite=1):
		self._shouldProfile = profile
		self._shouldRunTestSuite = runTestSuite
		self._iters = 200

	def main(self):
		if len(sys.argv)>1 and sys.argv[1].lower().startswith('prof'):
			self._shouldProfile = 1
		if self._shouldRunTestSuite:
			from TestDataTable import main
			main()
		start = time.time()
		if self._shouldProfile:
			prof = Profile()
			prof.runcall(self._main)
			filename = '%s.pstats' % self.__class__.__name__
			prof.dump_stats(filename)
			print 'Wrote', filename
		else:
			self._main()
		duration = time.time() - start
		print '%.1f secs' % duration

	def _main(self):
		for name in glob('Sample*.csv'):
			self.benchFileNamed(name)

	def benchFileNamed(self, name):
		contents = open(name).read()
		for x in xrange(self._iters):
			# we duplicate lines to reduce the overhead of the loop
			dt = DataTable()
			dt.readString(contents)

			dt = DataTable()
			dt.readString(contents)

			dt = DataTable()
			dt.readString(contents)

			dt = DataTable()
			dt.readString(contents)

			dt = DataTable()
			dt.readString(contents)

			dt = DataTable()
			dt.readString(contents)

			dt = DataTable()
			dt.readString(contents)

			dt = DataTable()
			dt.readString(contents)


if __name__=='__main__':
	BenchDataTable().main()
