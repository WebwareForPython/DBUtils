from RoleUserManagerMixIn import RoleUserManagerMixIn
from UserManager import UserManager


class RoleUserManager(UserManager, RoleUserManagerMixIn):
	"""
	See the base classes for more information.
	"""

	def __init__(self, userClass=None):
		UserManager.__init__(self, userClass)
		RoleUserManagerMixIn.__init__(self)
