#!/usr/bin/env python

"""AllTests.py - This module runs the automated tests in all the components.

To run specific test cases, pass one or more names of package/module names
on the command line which contain the test cases to be run.

Usage:
	python AllTests.py                  - Runs all the unittests
	python AllTests.py mypackage.MyFile - Runs the tests in 'mypackage/MyFile'

This module also has a test-wide configuration file which can be accessed by
the function AllTests.config().

"""


alltestnames = [

	'WebUtils.Tests.TestHTMLTag.makeTestSuite',

	'MiscUtils.Testing.TestCSVParser.CSVParserTests',
	'MiscUtils.Testing.TestNamedValueAccess.makeTestSuite',
	'MiscUtils.Testing.TestError.TestError',
	'MiscUtils.Testing.TestFuncs.TestFuncs',
	'MiscUtils.Testing.TestPickleCache.TestPickleCache',
	'MiscUtils.Testing.TestDataTable.TestDataTable',
	'MiscUtils.Testing.TestDictForArgs',

	'WebKit.Tests.Basic.Test',

	'TaskKit.Tests.Test.makeTestSuite',

	'PSP.Tests.PSPUtilsTest',
	'PSP.Tests.CompileTest',

	'UserKit.Tests.ExampleTest',
	'UserKit.Tests.Test',
	'UserKit.Tests.UserManagerTest.makeTestSuite',

]

try:
	import unittest
except ImportError: # Python < 2.1
	print "This module needs the Python unittest package (PyUnit)"
	print "available at http://pyunit.sourceforge.net"
	raise
try:
	import logging
except ImportError: # Python < 2.3
	print "This module needs the Python logging system"
	print "available at http://www.red-dove.com/python_logging.html"
	raise
try:
	True, False
except NameError: # Python < 2.3
	True, False = 1, 0

import sys, os, site
from MiscUtils.Configurable import Configurable

_alltestConfig = None
_log = logging.getLogger(__name__)


class _AllTestsConfig(Configurable):
	"""Configuration for tests.

	E.g. which DBs to test, where to find DB utilities.

	If individual tests need some configuration, put it here so it
	is easy for a new user to configure all the tests in one place.

	"""

	_defaultConfig = '''
{	# Edit this file to activate more tests

	# Turn on tests that use MySQL?
	'hasMysql': False,

	# If hasMysql is true, then these are used to connect:
	'mysqlTestInfo' : {

		# Where is MySQLdb lib located?
		# 'extraSysPath': ['/somewhere/MySQL-python-1.2.2/build/lib'],
		'extraSysPath': [],

		# Where is the MySQL client located (if not on the path)?
		# 'mysqlClient': '/usr/local/mysql/bin/mysql',
		# 'mysqlClient': 'c:/progra~1/mysql/mysqls~1.0/bin/mysql.exe',
		'mysqlClient': 'mysql',

		# The name of the MySQL database to be used:
		'database': 'test', # Test case uses this,
		# but UserManagerTest.mkmodel/Settings.config also defines it.

		# This is passed to MySQLObjectStore():
		'DatabaseArgs': {
			'host': 'localhost',
			'port': 3306,
			'user': 'test', # should have all database privileges
			'passwd': '',
		},
	}
}
'''

	def configFilename(self):
		theFilename = os.path.join(os.path.dirname(__file__), 'AllTests.config')
		# The first time we are run, write a new configuration file.
		if not os.path.exists(theFilename):
			_log.info(' Creating new configuration file at "%s".'
				' You can customize it to run more tests.', theFilename)
			fp = open(theFilename, 'w')
			fp.write(_AllTestsConfig._defaultConfig)
			fp.close()
		return theFilename

	def defaultConfig(self):
		default = eval(_AllTestsConfig._defaultConfig)
		return default

def config():
	"""Return singleton of configuration file."""
	global _alltestConfig
	if _alltestConfig is None:
		_alltestConfig = _AllTestsConfig()
	return _alltestConfig


def checkAndAddPaths(listOfPaths):
	"""Check paths.

	Pass me a list of paths, and I will check that each one exists and
	add it to sys.paths. This is used by tests which need to use some
	required library such as database drivers.

	"""
	numBadPaths = 0
	for p in listOfPaths:
		p = os.path.abspath(p)
		if os.path.exists(p):
			site.addsitedir(p)
		else:
			numBadPaths += 1
			print 'WARNING: Trying to add paths to sys.path,'
			print '  but could not find "%s".' % p
	return numBadPaths # 0 = all were found


if __name__ == '__main__':
	# Configure logging
	logging.basicConfig() # default level is WARN
	print
	print
	# If no arguments are given, all of the test cases are run.
	if len(sys.argv) == 1:
		testnames = alltestnames
		verbosity = 2
		logging.getLogger().setLevel(logging.INFO)
		print 'Loading all Webware Tests...'
	else:
		testnames = sys.argv[1:]
		# Turn up verbosity and logging level
		verbosity = 3
		logging.getLogger().setLevel(logging.DEBUG)
		print 'Loading tests %s...' % testnames

	tests = unittest.TestSuite()

	# We could just use defaultTestLoader.loadTestsFromNames(),
	# but it doesn't give a good error message when it cannot load a test.
	# So we load all tests individually and raise appropriate exceptions.
	for t in testnames:
		try:
			tests.addTest(unittest.defaultTestLoader.loadTestsFromName(t))
		except Exception:
			print 'ERROR: Skipping tests from "%s".' % t
			try:
				__import__(t) # just try to import the test after loadig failed
			except ImportError:
				print 'Could not import the test module.'
			else:
				print 'Could not load the test suite.'
			from traceback import print_exc
			print_exc()

	print
	print 'Running the tests...'
	unittest.TextTestRunner(verbosity=verbosity).run(tests)
