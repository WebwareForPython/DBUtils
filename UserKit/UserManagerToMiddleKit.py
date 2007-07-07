"""
UserManagerToMiddleKit.py
"""

from UserManager import UserManager
from MiscUtils import NoDefault
import os
from MiddleKit.Run.ObjectStore import UnknownObjectError


class UserManagerToMiddleKit(UserManager):
	"""
	UserManagerToMiddleKit stores the users in a given MiddleKit object store.

	However, the manager itself does not keep any information there. This might
	change in the future.

	In your MiddleKit model, your User class should have the attributes: name,
	password and externalId; all of type string. The max len for external id
	should be at least 14. You can decide what you like for the others. Only
	name and password have to be required.

	Then you must edit User.py so that:
		* In addition to inheriting GenUser, it also inherits UserKit.User
		* It invokes both base class' __init__()s
		* The __init__ takes manager, name and password, and passes them on.

		from UserKit.User import User

		class User(GenUser, User):

			def __init__(self, manager=None, name=None, password=None):
				GenUser.__init__(self)
				User.__init__(self, manager, name, password)

	If your user class is called something other than 'User', then you must pass it to the store:

		from MyUser import MyUser
		userMgr = UserManagerToMiddleKit(userClass=MyUser, store=store)
	"""


	## Init ##

	def __init__(self, userClass=None, store=None, useSQL=None):
		"""
		@@ 2001-02-18 ce: docs
		"""
		# If no userClass was specified, try to pull 'User'
		# out of the object model.
		if userClass is None:
			userClass = store.model().klass('User', None)

		UserManager.__init__(self, userClass)

		if store is None:
			from MiddleKit.ObjectStore.Store import Store
			store = Store
		assert store, 'MiddleKit store is None.'
		self._store = store

		# If the user didn't say whether or not to useSQL, then
		# we'll check if this looks like a SQLObjectStore. If so,
		# then using SQL server side queries will speed up our
		# operation:
		if useSQL is None:
			useSQL = getattr(self._store, 'executeSQL') is not None
		self._useSQL = useSQL

		# _saveNewUsers: if true, then we do a store.saveChanges()
		# whenever a new user is added. This helps with the
		# integrity of accessors like users().
		# @@ 2001-02-18 ce: But perhaps that's a problem because
		# manager is not a MiddleKit object...
		self._saveNewUsers = 1


	## MiddleKit specifics ##

	def loadUser(self, serialNum, default=NoDefault):
		try:
			user = self._store.fetchObject(self._userClass, serialNum, default)
		except UnknownObjectError:
			raise KeyError, serialNum
		if user is default:
			return default
		else:
			self._cachedUsers.append(user)
			self._cachedUsersBySerialNum[serialNum] = user
			return user


	## UserManager customizations ##

	def setUserClass(self, userClass):
		""" Overridden to verify that our userClass is really a MiddleObject. """
		from MiddleKit.Run.MiddleObject import MiddleObject
		assert issubclass(userClass, MiddleObject)
		UserManager.setUserClass(self, userClass)


	## UserManager concrete methods ##

	def addUser(self, user):
		self._store.addObject(user)
		if self._saveNewUsers:
			self._store.saveChanges()
		UserManager.addUser(self, user)

	def userForSerialNum(self, id, default=NoDefault):
		user = self._cachedUsersBySerialNum.get(id, None)
		if user is not None:
			return user
		return self.loadUser(id, default)

	def userForExternalId(self, externalId, default=NoDefault):
		for user in self._cachedUsers:
			if user.externalId() == externalId:
				return user
		if self._useSQL:
			users = self._store.fetchObjectsOfClass(self._userClass, clauses='where externalId=%r' % externalId)
			if users:
				assert len(users) == 1
				return users[0]
		else:
			for user in self.users():
				if user.externalId() == externalId:
					return user
		if default is NoDefault:
			raise KeyError, externalId
		else:
			return default

	def userForName(self, name, default=NoDefault):
		for user in self._cachedUsers:
			if user.name() == name:
				return user
		if self._useSQL:
			users = self._store.fetchObjectsOfClass(self._userClass, clauses='where name=%r' % name)
			if users:
				assert len(users) == 1
				return users[0]
		else:
			for user in self.users():
				if user.name() == name:
					return user
		if default is NoDefault:
			raise KeyError, name
		else:
			return default

	def users(self):
		return self._store.fetchObjectsOfClass(self._userClass)

	def activeUsers(self):
		# @@ 2001-02-17 ce: this ultimately does a fetch every time,
		# which sucks if we already have the user in memory.
		# this is really an MK issue regarding caching of objects
		# and perhaps a SQL database issue as well.
		return [user for user in self.users() if user.isActive()]

	def inactiveUsers(self):
		return [user for user in self.users() if not user.isActive()]
