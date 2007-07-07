import types
from User import User


class RoleUser(User):
	"""
	RoleUser, in conjunction with Role, provides for role-based users and security.

	See the doc for playsRole() for an example.

	Note that this class plays nicely with both Role and HierRole. e.g., no "HierRoleUser" is needed when making use of HierRoles.

	See also:
		* class Role
		* class HierRole
	"""


	## Init ##

	def __init__(self, manager=None, name=None, password=None):
		User.__init__(self, manager, name, password)
		self._roles = []
		self._rolesByName = {}


	## Accessing roles ##

	def roles(self):
		""" Returns a direct list of the user's roles. Do not modify. """
		return self._roles

	def setRoles(self, listOfRoles):
		"""
		Sets all the roles for the user. Each role in the list may be a valid role name or a Role object.
		Implementation note: depends on addRoles().
		"""
		self._roles = []
		self.addRoles(listOfRoles)

	def addRoles(self, listOfRoles):
		""" Adds additional roles for the user. Each role in the list may be a valid role name or a Role object. """
		start = len(self._roles)
		self._roles.extend(listOfRoles)

		# Convert names to role objects and update self._rolesByName
		index = start
		numRoles = len(self._roles)
		while index < numRoles:
			role = self._roles[index]
			if type(role) is types.StringType:
				role = self._manager.roleForName(role)
				self._roles[index] = role
			self._rolesByName[role.name()] = role
			index += 1

	def playsRole(self, roleOrName):
		"""
		Returns 1 if the user plays the given role. More specifically, if any of the user's roles return true for role.playsRole(otherRole), this method returns true.
		The application of this popular method often looks like this:
			if user.playsRole('admin'):
				self.displayAdminMenuItems()
		"""
		if type(roleOrName) is types.StringType:
			roleOrName = self._manager.roleForName(roleOrName)
		for role in self._roles:
			if role.playsRole(roleOrName):
				return 1
		return 0
