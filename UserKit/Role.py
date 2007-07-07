from MiscUtils.Funcs import positive_id


class Role:
	"""
	Roles are used in conjuction with RoleUser to provide role-based security.
	All roles have a name and a description and respond to playsRole().

	RoleUser also responds to playsRole() and is the more popular entry point
	for programmers. Application code may then do something along the lines of:

	if user.playsRole('admin'):
		self.displayAdminMenuItems()

	See also:
		* class HierRole
		* class RoleUser
	"""


	## Init ##

	def __init__(self, name, description=None):
		self._name = name
		self._description = description


	## Attributes ##

	def name(self):
		return self._name

	def setName(self, name):
		self._name = name

	def description(self):
		return self._description

	def setDescription(self, description):
		self._description = description


	## As strings ##

	def __str__(self):
		return str(self._name)

	def __repr__(self):
		return '<%s %r instance at %x>' % (
			self.__class__, self._name, positive_id(self))


	## The big question ##

	def playsRole(self, role):
		"""Return true if the receiving role plays the role passed in.

		For Role, this is simply a test of equality. Subclasses may override
		this method to provide richer semantics (such as hierarchical roles).

		"""
		assert isinstance(role, Role)
		return self == role
