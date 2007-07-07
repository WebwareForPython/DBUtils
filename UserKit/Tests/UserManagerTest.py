"""
This module tests UserManagers in different permutations.
UserManagers can save their data to files, or to a MiddleKit database.
For MiddleKit, the database can be MySQL, PostgreSQL and MSSQL.

To run these tests:
	cd Webware
	python AllTests.py UserKit.Tests.UserManagerTest.makeTestSuite
"""

import os, sys
import logging
import unittest
import shutil

import UserKit
import AllTests

_log = logging.getLogger(__name__)

TEST_CODE_DIR = os.path.dirname(__file__) # e.g. ".../Webware/UserKit/Tests"


class UserManagerTest(unittest.TestCase):

	def setUp(self):
		from UserKit.UserManager import UserManager
		self._mgr = UserManager()

	def checkSettings(self):
		mgr = self._mgr
		value = 5.1
		mgr.setModifiedUserTimeout(value)
		assert mgr.modifiedUserTimeout() == value
		mgr.setCachedUserTimeout(value)
		assert mgr.cachedUserTimeout() == value
		mgr.setActiveUserTimeout(value)
		assert mgr.activeUserTimeout() == value

	def checkUserClass(self):
		mgr = self._mgr
		from UserKit.User import User
		class SubUser(User): pass
		mgr.setUserClass(SubUser)
		assert mgr.userClass() == SubUser, \
			"We should be able to set a custom user class."
		class Poser: pass
		self.assertRaises(Exception, mgr.setUserClass, Poser), \
			"Setting a customer user class that doesn't extend UserKit.User should fail."

	def tearDown(self):
		self._mgr.shutDown()
		self._mgr = None


class _UserManagerToSomewhereTest(UserManagerTest):
	"""
	This abstract class provides some tests that all user managers should pass.
	Subclasses are responsible for overriding setUp() and tearDown() for which
	they should invoke super.
	"""

	def setUp(self):
		pass # nothing for no

	def tearDown(self):
		self._mgr = None

	def testBasics(self):
		mgr = self._mgr
		user = self._user = mgr.createUser('foo', 'bar')
		assert user.manager() == mgr
		assert user.name() == 'foo'
		assert user.password() == 'bar'
		assert not user.isActive()
		assert mgr.userForSerialNum(user.serialNum()) == user
		assert mgr.userForExternalId(user.externalId()) == user
		assert mgr.userForName(user.name()) == user
		externalId = user.externalId() # for use later in testing

		users = mgr.users()
		assert len(users) == 1
		assert users[0] == user, 'users[0]=%r, user=%r' % (users[0], user)
		assert len(mgr.activeUsers()) == 0
		assert len(mgr.inactiveUsers()) == 1

		# login
		user2 = mgr.login(user, 'bar')
		assert user == user2
		assert user.isActive()
		assert len(mgr.activeUsers()) == 1
		assert len(mgr.inactiveUsers()) == 0

		# logout
		user.logout()
		assert not user.isActive()
		assert mgr.numActiveUsers() == 0

		# login via user
		result = user.login('bar')
		assert result == user
		assert user.isActive()
		assert mgr.numActiveUsers() == 1

		# logout via user
		user.logout()
		assert not user.isActive()
		assert mgr.numActiveUsers() == 0

		# login a 2nd time, but with bad password
		user.login('bar')
		user.login('rab')
		assert not user.isActive()
		assert mgr.numActiveUsers() == 0

		# Check that we can access the user when he is not cached
		mgr.clearCache()
		user = mgr.userForSerialNum(1)
		assert user
		assert user.password() == 'bar'

		if 0: # @@ 2001-04-15 ce: doesn't work yet
			mgr.clearCache()
			user = self._mgr.userForExternalId(externalId)
			assert user
			assert user.password() == 'bar'

		mgr.clearCache()
		user = self._mgr.userForName('foo')
		assert user
		assert user.password() == 'bar'

	def testUserAccess(self):
		mgr = self._mgr
		user = mgr.createUser('foo', 'bar')

		assert mgr.userForSerialNum(user.serialNum()) == user
		assert mgr.userForExternalId(user.externalId()) == user
		assert mgr.userForName(user.name()) == user

		self.assertRaises(KeyError, mgr.userForSerialNum, 1000)
		self.assertRaises(KeyError, mgr.userForExternalId, 'asdf')
		self.assertRaises(KeyError, mgr.userForName, 'asdf')

		assert mgr.userForSerialNum(1000, 1) == 1
		assert mgr.userForExternalId('asdf', 1) == 1
		assert mgr.userForName('asdf', 1) == 1

	def testDuplicateUser(self):
		mgr = self._mgr
		user = self._user = mgr.createUser('foo', 'bar')
		self.assertRaises(AssertionError, mgr.createUser, 'foo', 'bar')
		userClass = mgr.userClass()
		self.assertRaises(AssertionError, userClass, mgr, 'foo', 'bar')


class UserManagerToFileTest(_UserManagerToSomewhereTest):

	def setUp(self):
		_UserManagerToSomewhereTest.setUp(self)
		from UserKit.UserManagerToFile import UserManagerToFile
		self._mgr = UserManagerToFile()
		self.setUpUserDir(self._mgr)

	def setUpUserDir(self, mgr):
		path = 'Users'
		if os.path.exists(path):
			shutil.rmtree(path, ignore_errors=1)
		os.mkdir(path)
		mgr.setUserDir(path)

	def tearDown(self):
		path = 'Users'
		if os.path.exists(path):
			shutil.rmtree(path, ignore_errors=1)
		_UserManagerToSomewhereTest.tearDown(self)


class UserManagerToMiddleKitTest(_UserManagerToSomewhereTest):

	def write(self, text):
		self._output.append(text)

	def setUp(self):
		_UserManagerToSomewhereTest.setUp(self)

		self._output = []
		self._stdout, self._stderr = sys.stdout, sys.stderr
		sys.stdout = sys.stderr = self
		try:

			# Generate Python and SQL from our test MiddleKit Model
			from MiddleKit.Design.Generate import Generate

			generator = Generate()

			modelFileName = os.path.join(TEST_CODE_DIR, 'UserManagerTest.mkmodel')
			generationDir = os.path.join(TEST_CODE_DIR, 'mk_MySQL')

			# _log.debug('model: %s',modelFileName)
			# @@ 2001-02-18 ce: woops: hard coding MySQL

			args = 'Generate.py --db MySQL --model %s --outdir %s' % (
				modelFileName, generationDir)
			Generate().main(args.split())

			create_sql = os.path.join(generationDir, 'GeneratedSQL', 'Create.sql')

			assert os.path.exists(create_sql), \
				'The generation process should create some SQL files.'
			assert os.path.exists(os.path.join(generationDir, 'UserForMKTest.py')), \
				'The generation process should create some Python files.'

			self._mysqlTestInfo = AllTests.config().setting('mysqlTestInfo')
			# _log.info('mysqlTestInfo=%s', self._mysqlTestInfo)

			# Create our test database using info from AllTests.config

			self._mysqlClient = self._mysqlTestInfo['mysqlClient']
			mysqlClientName = os.path.basename(self._mysqlClient)
			assert mysqlClientName == 'mysql' or mysqlClientName == 'mysql.exe'
			self._mysqlClient = ' '.join([self._mysqlClient] + ['--%s="%s"' % s
					for s in self._mysqlTestInfo['DatabaseArgs'].items() if s[1]])
			executeSqlCmd = '%s < %s' % (self._mysqlClient, create_sql)

			# _log.debug('running: %s', executeSqlCmd)
			f = os.popen(executeSqlCmd)
			self._output.append(f.read())
			if f.close():
				raise OSError, 'Error running: %s' % executeSqlCmd

			# Create store, and connect to database

			from MiddleKit.Run.MySQLObjectStore import MySQLObjectStore

			store = MySQLObjectStore(**self._mysqlTestInfo['DatabaseArgs'])
			store.readModelFileNamed(modelFileName)

			from MiddleKit.Run.MiddleObject import MiddleObject
			from UserKit.UserManagerToMiddleKit import UserManagerToMiddleKit
			from UserKit.Tests.mk_MySQL.UserForMKTest import UserForMKTest
			assert issubclass(UserForMKTest, MiddleObject)
			from UserKit.User import User
			if User not in UserForMKTest.__bases__:
				UserForMKTest.__bases__ += (User,)
			assert issubclass(UserForMKTest, MiddleObject)

			def __init__(self, manager, name, password):
				base1 = self.__class__.__bases__[0]
				base2 = self.__class__.__bases__[1]
				base1.__init__(self)
				base2.__init__(self, manager=manager, name=name, password=password)

			UserForMKTest.__init__ = __init__
			self._mgr = self.userManagerClass()(userClass=UserForMKTest, store=store)

		except:
			sys.stdout, sys.stderr = self._stdout, self._stderr
			print "Error in %s.SetUp." % self.__class__.__name__
			print ''.join(self._output)
			raise
		else:
			sys.stdout, sys.stderr = self._stdout, self._stderr

	def testUserClass(self):
		pass

	def userManagerClass(self):
		from UserKit.UserManagerToMiddleKit import UserManagerToMiddleKit
		return UserManagerToMiddleKit

	def tearDown(self):
		self._output = []
		self._stdout, self._stderr = sys.stdout, sys.stderr
		sys.stdout = sys.stderr = self

		try:
			# clean out generated files
			path = os.path.join(TEST_CODE_DIR, 'mk_MySQL')
			if os.path.exists(path):
				shutil.rmtree(path, ignore_errors=1)

			# Drop tables from database
			sqlDropTables = "drop table UserForMKTest, _MKClassIds"

			db = self._mysqlTestInfo['database']

			executeSqlCmd = '%s %s -e "%s"' % (self._mysqlClient, db, sqlDropTables)

			# _log.debug('running: %s', executeSqlCmd)
			f = os.popen(executeSqlCmd)
			self._output.append(f.read())
			if f.close():
				raise OSError, 'Error running: %s' % executeSqlCmd

		except:
			sys.stdout, sys.stderr = self._stdout, self._stderr
			print "Error in %s.SetUp." % self.__class__.__name__
			print ''.join(self._output)
			raise
		else:
			sys.stdout, sys.stderr = self._stdout, self._stderr

		_UserManagerToSomewhereTest.tearDown(self)


class RoleUserManagerToFileTest(UserManagerToFileTest):

	def setUp(self):
		UserManagerToFileTest.setUp(self)
		from UserKit.RoleUserManagerToFile import RoleUserManagerToFile as umClass
		self._mgr = umClass()
		self.setUpUserDir(self._mgr)


class RoleUserManagerToMiddleKitTest(UserManagerToMiddleKitTest):

	def userManagerClass(self):
		from UserKit.RoleUserManagerToMiddleKit import RoleUserManagerToMiddleKit
		return RoleUserManagerToMiddleKit


def makeTestSuite():
	testClasses = [
		UserManagerTest, UserManagerToFileTest, RoleUserManagerToFileTest]

	# See if AllTests.conf has been configured for MySQL
	if AllTests.config().setting('hasMysql'):
		mysqlTestInfo = AllTests.config().setting('mysqlTestInfo')
		_log.info('Adding MySQL tests for UserKit.')
		# Add paths for MySQL-python driver
		numBadPaths = AllTests.checkAndAddPaths(mysqlTestInfo['extraSysPath'])
		# Add the tests that require MySQL
		testClasses.extend([UserManagerToMiddleKitTest, RoleUserManagerToMiddleKitTest])
	else:
		_log.info('Skipping MySQL tests. MySQL is not configured in AllTests.config.')

	make = unittest.makeSuite
	tests = [unittest.makeSuite(klass) for klass in testClasses]
	return unittest.TestSuite(tests)
