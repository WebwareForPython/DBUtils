from RoleUserManagerMixIn import RoleUserManagerMixIn
from UserManagerToFile import UserManagerToFile


class RoleUserManagerToFile(UserManagerToFile, RoleUserManagerMixIn):
	"""
	See the base classes for more information.
	"""

	def __init__(self, userClass=None):
		UserManagerToFile.__init__(self, userClass)
		RoleUserManagerMixIn.__init__(self)
