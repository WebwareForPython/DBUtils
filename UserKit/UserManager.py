import types
from MiscUtils import NoDefault
from User import User


class UserManager:
	"""
	A UserManager manages a set of users including authentication, indexing and persistence. Keep in mind that UserManager is abstract; you will always use one of the concrete subclasses (but please read the rest of this doc string):
		* UserManagerToFile
		* UserManagerToMiddleKit


	You can create a user through the manager (preferred):
		user = manager.createUser(name, password)

	Or directly through the user class:
		user = RoleUser(manager, name, password)
		manager.addUser(user)

	The manager tracks users by whether or not they are "active" (e.g., logged in) and indexes them by:
		* user serial number
		* external user id
		* user name

	These methods provide access to the users by these keys:
		def userForSerialNum(self, serialNum, default=NoDefault)
		def userForExternalId(self, extId, default=NoDefault)
		def userForName(self, name, default=NoDefault)


	UserManager provides convenient methods for iterating through the various users. Each method returns an object that can be used in a for loop and asked for its len():
		def users(self)
		def activeUsers(self)
		def inactiveUsers(self)


	You can authenticate a user by passing the user object and attempted password to login(). If the authentication is successful, then login() returns the User, otherwise it returns None:

		user = mgr.userForExternalId(externalId)
		if mgr.login(user, password):
			self.doSomething()

	As a convenience, you can authenticate by passing the serialNum, externalId or name of the user:

		def loginSerialNum(self, serialNum, password):
		def loginExternalId(self, externalId, password):
		def loginName(self, userName, password):


	The user will automatically log out after a period of inactivity (see below), or you can make it happen with:
		def logout(self, user):


	There are three user states that are important to the manager:
		* modified
		* cached
		* authenticated or "active"

	A modified user is one whose data has changed and eventually requires storage to a persistent location. A cached user is a user whose data resides in memory (regardless of the other states). An active user has been authenticated (e.g., their username and password were checked) and has not yet logged out or timed out.

	The manager keeps three timeouts, expressed in minutes, to:
		* save modified users after a period of time following the first unsaved modification
		* push users out of memory after a period of inactivity
		* deactive (e.g., log out) users after a period of inactivity

	The methods for	managing these values deal with the timeouts as number-of-minutes. The default values and the methods are:
		* 20  modifiedUserTimeout()  setModifiedUserTimeout()
		* 20  cachedUserTimeout()    setCachedUserTimeout()
		* 20  activeUserTimeout()    setActiveUserTimeout()

	@@ 2001-02-16 ce: Should we take out "User" in the names of the above 6 methods? Maybe it's redundant.

	Subclasses of UserManager provide persistence such as to the file system or a MiddleKit store. Subclasses must implement all methods that raise AbstractError's. Subclasses typically override (while still invoking super) addUser().

	Subclasses should ensure "uniqueness" of users. For example, invoking any of the userForSomething() methods repeatedly should always return the same user instance for a given key. Without uniqueness, consistency issues could arise with users that are modified.

	Please read the method doc strings and other class documentation to fully understand UserKit.
	"""


	## Init ##

	def __init__(self, userClass=None):
		if userClass is None:
			self._userClass = None
		else:
			self.setUserClass(userClass)
		self._cachedUsers = []
		self._cachedUsersBySerialNum = {}
		self.setModifiedUserTimeout(20)
		self.setCachedUserTimeout(20)
		self.setActiveUserTimeout(20)
		self._numActive = 0

	def shutDown(self):
		""" Performs any tasks necessary to shut down the user manager. Subclasses may override and must invoke super as their *last* step. """
		pass


	## Settings ##

	def userClass(self):
		""" Returns the userClass, which is used by createUser. The default value is UserKit.User.User. """
		if self._userClass is None:
			from User import User
			self.setUserClass(User)
		return self._userClass

	def setUserClass(self, userClass):
		""" Sets the userClass, which cannot be None and must inherit from User. See also: userClass(). """
		from User import User
		assert issubclass(userClass, User)
		self._userClass = userClass

	def modifiedUserTimeout(self):
		return self._modifiedUserTimeout

	def setModifiedUserTimeout(self, value):
		self._modifiedUserTimeout = value

	def cachedUserTimeout(self):
		return self._cachedUserTimeout

	def setCachedUserTimeout(self, value):
		self._cachedUserTimeout = value

	def activeUserTimeout(self):
		return self._activeUserTimeout

	def setActiveUserTimeout(self, value):
		self._activeUserTimeout = value


	## Basic user access ##

	def createUser(self, name, password, userClass=None):
		"""
		Returns a newly created user that is added to the manager. If userClass is not specified, the manager's default user class is instantiated.
		This not imply that the user is logged in.
		This method invokes self.addUser().
		See also: userClass(), setUserClass()
		"""
		if userClass is None:
			userClass = self.userClass()
		user = userClass(manager=self, name=name, password=password)
		self.addUser(user)
		return user

	def addUser(self, user):
		assert isinstance(user, User)
		self._cachedUsers.append(user)
		assert not self._cachedUsersBySerialNum.has_key(user.serialNum())
		self._cachedUsersBySerialNum[user.serialNum()] = user

	def userForSerialNum(self, serialNum, default=NoDefault):
		""" Returns the user with the given serialNum, pulling that user record into memory if needed. """
		raise AbstractError, self.__class__

	def userForExternalId(self, externalId, default=NoDefault):
		""" Returns the user with the given external id, pulling that user record into memory if needed. """
		raise AbstractError, self.__class__

	def userForName(self, name, default=NoDefault):
		""" Returns the user with the given name, pulling that user record into memory if needed. """
		raise AbstractError, self.__class__

	def users(self):
		""" Returns a list of all users (regardless of login status). """
		raise AbstractError, self.__class__

	def numActiveUsers(self):
		""" Returns the number of active users, e.g., users that are logged in. """
		return self._numActive

	def activeUsers(self):
		""" Returns a list of all active users. """
		raise AbstractError, self.__class__

	def inactiveUsers(self):
		raise AbstractError, self.__class__


	## Logging in and out ##

	def login(self, user, password):
		""" Returns the user if the login is successful, otherwise returns None. """
		assert isinstance(user, User)
		result = user.login(password, fromMgr=1)
		if result:
			self._numActive += 1
		return result

	def logout(self, user):
		assert isinstance(user, User)
		user.logout(fromMgr=1)
		self._numActive -= 1

	def loginSerialNum(self, serialNum, password):
		user = self.userForSerialNum(serialNum, None)
		if user:
			return self.login(user, password)
		else:
			return None

	def loginExternalId(self, externalId, password):
		user = self.userForExternalId(externalId, None)
		if user:
			return self.login(user, password)
		else:
			return None

	def loginName(self, userName, password):
		user = self.userForName(userName, None)
		if user:
			return self.login(user, password)
		else:
			return None


	## Cached ##

	def clearCache(self):
		"""
		Clears the cache of the manager. Use with extreme caution. If your program maintains a reference to a user object, but the manager loads in a new copy later on, then consistency problems could occur.
		The most popular use of this method is in the regression test suite.
		"""
		self._cachedUsers = []
		self._cachedUsersBySerialNum = {}
