from UserManager import UserManager
from MiscUtils import NoDefault
import os
from glob import glob
from User import User


class UserManagerToFile(UserManager):
	"""
	When using this user manager, make sure you invoke setUserDir() and that
	this directory is writeable by your application. It will contain 1 file per
	user with the user's serial number as the main filename and an extension of
	'.user'.

	The default user directory is the current working directory, but relying on
	the current directory is often a bad practice.
	"""

	_baseOfUserManagerToFile = UserManager


	## Init ##

	def __init__(self, userClass=None):
		self._baseOfUserManagerToFile.__init__(self, userClass=None)
		try:
			from cPickle import load, dump
		except ImportError:
			from pickle import load, dump
		self.setEncoderDecoder(dump, load)
		self.setUserDir(os.getcwd())
		self.initNextSerialNum()

	def initNextSerialNum(self):
		if os.path.exists(self._userDir):
			serialNums = self.scanSerialNums()
			if serialNums:
				self._nextSerialNum = max(serialNums) + 1
			else:
				self._nextSerialNum = 1
		else:
			self._nextSerialNum = 1


	## WebKit integration ##

	def wasInstalled(self, owner):
		self._baseOfUserManagerToFile.wasInstalled(self, owner)
		self.setUserDir(owner.serverSidePath('Users'))
		self.initNextSerialNum()


	## File storage specifics ##

	def userDir(self):
		return self._userDir

	def setUserDir(self, userDir):
		""" Sets the directory where user information is stored. You should strongly consider invoking initNextSerialNum() afterwards. """
		self._userDir = userDir

	def loadUser(self, serialNum, default=NoDefault):
		"""
		Loads the user with the given serial number from disk.
		If there is no such user, a KeyError will be raised unless a default value was passed, in which case that value is returned.
		"""
		filename = str(serialNum) + '.user'
		filename = os.path.join(self.userDir(), filename)
		if os.path.exists(filename):
			file = open(filename, 'r')
			user = self.decoder()(file)
			file.close()
			self._cachedUsers.append(user)
			self._cachedUsersBySerialNum[serialNum] = user
			return user
		else:
			if default is NoDefault:
				raise KeyError, serialNum
			else:
				return default

	def scanSerialNums(self):
		"""
		Returns a list of all the serial numbers of users found on disk. Serial numbers are always integers.
		"""
		chopIndex = -len('.user')
		nums = glob(os.path.join(self.userDir(), '*.user'))
		nums = [num[:chopIndex] for num in nums]
		nums = [os.path.basename(num) for num in nums]
		nums = [int(num) for num in nums]
		return nums


	## UserManager customizations ##

	def setUserClass(self, userClass):
		""" Overridden to mix in UserMixIn to the class that is passed in. """
		# cz: doing so with MiscUtils.Mixin lead to errors later
		# when pickling the user, so I'm doing it this way now:
		if UserMixIn not in userClass.__bases__:
			userClass.__bases__ += (UserMixIn,)
		self._baseOfUserManagerToFile.setUserClass(self, userClass)


	## UserManager concrete methods ##

	def nextSerialNum(self):
		result = self._nextSerialNum
		self._nextSerialNum += 1
		return result

	def addUser(self, user):
		assert isinstance(user, User)
		user._serialNum = self.nextSerialNum()
		self._baseOfUserManagerToFile.addUser(self, user)
		user.save()

	def userForSerialNum(self, serialNum, default=NoDefault):
		user = self._cachedUsersBySerialNum.get(serialNum, None)
		if user is not None:
			return user
		return self.loadUser(serialNum, default)

	def userForExternalId(self, externalId, default=NoDefault):
		for user in self._cachedUsers:
			if user.externalId() == externalId:
				return user
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
		for user in self.users():
			if user.name() == name:
				return user
		if default is NoDefault:
			raise KeyError, name
		else:
			return default

	def users(self):
		return _UserList(self)

	def activeUsers(self):
		return _UserList(self, lambda user: user.isActive())

	def inactiveUsers(self):
		return _UserList(self, lambda user: not user.isActive())


	## Encoder/decoder ##

	def encoder(self):
		return self._encoder

	def decoder(self):
		return self._decoder

	def setEncoderDecoder(self, encoder, decoder):
		self._encoder = encoder
		self._decoder = decoder


class UserMixIn:

	def filename(self):
		return os.path.join(self.manager().userDir(), str(self.serialNum())) + '.user'

	def save(self):
		file = open(self.filename(), 'w')
		self.manager().encoder()(self, file)
		file.close()


class _UserList:

	def __init__(self, mgr, filterFunc=None):
		self._mgr = mgr
		self._serialNums = mgr.scanSerialNums()
		self._count = len(self._serialNums)
		self._data = None
		if filterFunc:
			results = []
			for user in self:
				if filterFunc(user):
					results.append(user)
			self._count = len(results)
			self._data = results

	def __getitem__(self, index):
		if index >= self._count:
			raise IndexError
		if self._data:
			# We have the data directly. Just return it
			return self._data[index]
		else:
			# We have a list of the serial numbers.
			# Get the user from the manager via the cache or loading
			serialNum = self._serialNums[index]
			if self._mgr._cachedUsersBySerialNum.has_key(serialNum):
				return self._mgr._cachedUsersBySerialNum[serialNum]
			else:
				return self._mgr.loadUser(self._serialNums[index])

	def __len__(self):
		return self._count
