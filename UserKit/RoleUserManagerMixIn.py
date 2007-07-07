from RoleUser import RoleUser
from Role import Role
from MiscUtils import NoDefault


class RoleUserManagerMixIn:
	"""
	RoleUserManagerMixIn adds the functionality of keeping a dictionary mapping 
	names to role instances. Several accessor methods are provided for this.
	"""


	## Init ##

	def __init__(self):
		self._roles = {}
		self.initUserClass()

	def initUserClass(self):
		"""
		Invoked by __init__ to set the default user class to
		RoleUser.
		"""
		self.setUserClass(RoleUser)


	## Roles ##

	def addRole(self, role):
		assert isinstance(role, Role)
		name = role.name()
		assert not self._roles.has_key(name)
		self._roles[name] = role

	def role(self, name, default=NoDefault):
		if default is NoDefault:
			return self._roles[name]
		else:
			return self._roles.get(name, default)

	def hasRole(self, name):
		return self._roles.has_key(name)

	def delRole(self, name):
		del self._roles[name]

	def roles(self):
		return self._roles

	def clearRoles(self):
		self._roles = {}
