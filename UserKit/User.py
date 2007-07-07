from MiscUtils import NoDefault
from MiscUtils.Funcs import uniqueId
import time


class User:
	"""
	@@ 2001-02-19 ce: docs
	"""


	## Init ##

	def __init__(self, manager=None, name=None, password=None):
		self._creationTime = time.time()

		self._manager = None
		self._name = None
		self._password = None
		self._isActive = 0
		self._externalId = None

		if name is not None:
			self.setName(name)
		if manager is not None:
			self.setManager(manager)
		if password is not None:
			self.setPassword(password)


	## Attributes ##

	def manager(self):
		return self._manager

	def setManager(self, manager):
		"""Set the manager, which can only be done once."""
		assert self._manager is None
		from UserManager import UserManager
		assert isinstance(manager, UserManager)
		assert manager.userForName(self.name(), None) is None, \
			'There is already a user named %r.' % self.name()
		self._manager = manager

	def serialNum(self):
		return self._serialNum

	def externalId(self):
		if self._externalId is None:
			from time import localtime, time
			self._externalId = uniqueId(self)
		return self._externalId

	def name(self):
		return self._name

	def setName(self, name):
		"""Set the name, which can only be done once."""
		assert self._name is None
		self._name = name
		# @@ 2001-02-15 ce: do we need to notify the manager
		# which may have us keyed by name?

	def password(self):
		return self._password

	def setPassword(self, password):
		self._password = password
		# @@ 2001-02-15 ce: should we make some attempt to
		# cryptify the password so it's not real obvious
		# when inspecting memory?

	def isActive(self):
		return self._isActive

	def creationTime(self):
		return self._creationTime

	def lastAccessTime(self):
		return self._lastAccessTime

	def lastLoginTime(self):
		return self._lastLoginTime


	## Log in and out ##

	def login(self, password, fromMgr=0):
		"""Return self if the login is successful and None otherwise."""
		if not fromMgr:
			# Our manager needs to know about this
			# So make sure we go through him
			return self.manager().login(self, password)
		else:
			if password == self.password():
				self._isActive = 1
				self._lastLoginTime = self._lastAccessTime = time.time()
				return self
			else:
				if self._isActive:
					# Woops. We were already logged in, but we tried again
					# and this time it failed. Logout:
					self.logout()
				return None

	def logout(self, fromMgr=0):
		if not fromMgr:
			# Our manager needs to know about this
			# So make sure we go through him
			self.manager().logout(self)
		else:
			self._isActive = 0
			self._lastLogoutTime = time.time()


	## Notifications ##

	def wasAccessed(self):
		self._lastAccessTime = time.time()
