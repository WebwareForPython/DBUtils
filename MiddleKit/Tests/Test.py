#!/usr/bin/env python
import time
startTime = time.time()

import os, sys
from TestCommon import *
from glob import glob


class RunError(Exception):
	"""
	Raised by Test.run() if the process exits with a non-zero status, which indicates an error.
	"""
	pass

class Test:

	## Init ##

	def __init__(self):
		pass


	## Customization ##

	def modelNames(self):
		return self._modelNames


	## Testing ##

	def main(self, args=sys.argv):
		# The tests are listed explicitly rather than scanning for them (via glob) in order to perform them in a certain order (simplest to most complex)
		self.readArgs(args)
		results = []
		for self._modelName in self.modelNames():
			print '*** %s ***\n' % self._modelName
			if not self._modelName.endswith('.mkmodel'):
				self._modelName += '.mkmodel'
			didFail = 0
			try:
				if self.canRun():
					# support multiple config files for testing
					configFilenames = glob(os.path.join(self._modelName, 'Settings*.config'))
					if configFilenames:
						configFilenames = [os.path.basename(p) for p in configFilenames]
					else:
						configFilenames = ['Settings.config']
					for configFilename in configFilenames:
						self.runCompletePath(configFilename)
				else:
					didFail = '       skipped'
			except RunError:
				didFail = '*** FAILED ***'
			results.append((self._modelName, didFail))

		self.printInfo()
		self.printResults(results)

		# print duration for curiosity's sake
		print
		duration = time.time() - startTime
		print '%.0f seconds' % (duration)

	def readArgs(self, args):
		if len(args)>1:
			self._modelNames = args[1:]
		else:
			self._modelNames = '''
				MKBasic MKNone MKString MKDateTime MKEnums MKDefaultMinMax
				MKTypeValueChecking MKInheritance MKInheritanceAbstract
				MKList MKObjRef MKObjRefReuse MKDelete MKDeleteMark
				MKMultipleStores MKMultipleThreads
				MKModelInh1 MKModelInh2 MKModelInh3
				MKExcel
			'''.split()

	def canRun(self):
		path = os.path.join(self._modelName, 'CanRun.py')
		if os.path.exists(path):
			file = open(path)
			names = {}
			exec file in names
			assert names.has_key('CanRun'), 'expecting a CanRun() function'
			return names['CanRun']()
		else:
			return 1

	def runCompletePath(self, configFilename='Settings.config'):
		self._configFilename = configFilename
		self.testDesign()
		self.testEmpty()
		self.insertSamples()
		self.testSamples()
		rmdir(workDir)
		print '\n'

	def testEmpty(self):
		"""
		Run all TestEmpty*.py files in the model, in alphabetical order by name.
		"""
		names = glob(os.path.join(self._modelName, 'TestEmpty*.py'))
		if names:
			names.sort()
			for name in names:
				self.createDatabase()
				self.testRun(os.path.basename(name), deleteData=0)
		else:
			self.createDatabase()

	def testSamples(self):
		self.testRun('TestSamples.py', deleteData=0)

	def testRun(self, pyFile, deleteData):
		if os.path.exists(os.path.join(self._modelName, pyFile)):
			print '%s:' % pyFile
			self.run('python TestRun.py %s %s %s delete=%i' % (self._modelName, self._configFilename, pyFile, deleteData))
		else:
			print 'NO %s TO TEST.' % pyFile

	def testDesign(self):
		self.run('python TestDesign.py %s %s' % (self._modelName, self._configFilename))

	def createDatabase(self):
		filename = workDir + '/GeneratedSQL/Create.sql'
		filename = os.path.normpath(filename)
		cmd = '%s < %s' % (sqlCommand, filename)
		self.run(cmd)

	def insertSamples(self):
		self.createDatabase()
		filename = workDir + '/GeneratedSQL/InsertSamples.sql'
		filename = os.path.normpath(filename)
		if os.path.exists(filename):
			cmd = '%s < %s' % (sqlCommand, filename)
			self.run(cmd)

	def printInfo(self):
		print
		print 'SYSTEM INFO'
		print '-----------'
		print 'sys.version =', sys.version
		print 'sys.platform =', sys.platform
		print 'os.name =', os.name
		if hasattr(sys, 'getwindowsversion'):
			print 'sys.getwindowsversion() =', sys.getwindowsversion()
		print 'os.getcwd() =', os.getcwd()
		print 'dbName =', dbName
		if sqlVersionCommand:
			self.run(sqlVersionCommand)

		# Since Test.py runs things via os.system() it won't actually have the DB API module loaded.
		# But that's really desireable so its version number can be printed out, so import the store:
		objStoreName = dbName + 'ObjectStore'
		values = {}
		exec 'import MiddleKit.Run.'+objStoreName in values

		out = sys.stdout
		out.write('modules with versions:\n')
		modules = [m for m in sys.modules.values() if m is not None and m.__name__!='sys']
		modules.sort(lambda a, b: cmp(a.__name__, b.__name__))
		for mod in modules:
			ver = getattr(mod, 'version', None)
			verInfo = getattr(mod, 'version_info', None)
			if ver or verInfo:
				out.write('    %s' % mod.__name__)
				if verInfo:
					out.write(', %s' % (verInfo,))
				if ver:
					out.write(', %r' % ver)
				out.write(', %s' % getattr(mod, '__file__', '(built-in)'))
				out.write('\n')

	def printResults(self, results):
		"""
		Summarize the results of each test.
		"""
		print
		print 'RESULTS'
		print '-------'
		for name, outcome in results:
			if not outcome:
				outcome = '     succeeded'
			print outcome, name


	## Self utility ##

	def run(self, cmd):
		"""
		Self utility method to run a system command. If the command
		has a non-zero exit status, raises RunError. Otherwise,
		returns 0.

		Note that on Windows ME, os.system() always returns 0 even if
		the program was a Python program that exited via sys.exit(1) or
		an uncaught exception. On Windows XP Pro SP 1, this problem
		does not occur. Windows ME has plenty of other problems as
		well; avoid it.
		"""
		print '<cmd>', cmd
		sys.stdout.flush()
		sys.stderr.flush()
		returnCode = os.system(cmd)
		sys.stdout.flush()
		sys.stderr.flush()

		if returnCode:
			raise RunError, returnCode

		#print '>> RETURN CODE =', returnCode
		return returnCode


if __name__=='__main__':
	Test().main()
