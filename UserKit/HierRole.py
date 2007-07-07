from Role import Role


class HierRole(Role):
	"""
	HierRole is a hierarchical role. It points to its parent roles.
	The hierarchy cannot have cycles.
	"""

	def __init__(self, name, description=None, superRoles=[]):
		Role.__init__(self, name, description)
		for role in superRoles:
			assert isinstance(role, Role)
		self._superRoles = superRoles[:]

	def playsRole(self, role):
		"""
		Returns 1 if the receiving role plays the role that is passed in. This
		implementation provides for the inheritance that HierRole supports.
		"""
		if self == role:
			return 1
		for superRole in self._superRoles:
			if superRole.playsRole(role):
				return 1
		return 0
