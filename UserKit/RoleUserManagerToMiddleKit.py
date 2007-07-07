from RoleUserManagerMixIn import RoleUserManagerMixIn
from UserManagerToMiddleKit import UserManagerToMiddleKit


class RoleUserManagerToMiddleKit(UserManagerToMiddleKit, RoleUserManagerMixIn):
	"""
	See the base classes for more information.
	"""

	def __init__(self, userClass=None, store=None, useSQL=None):
		UserManagerToMiddleKit.__init__(self, userClass, store, useSQL)
		RoleUserManagerMixIn.__init__(self)

	def initUserClass(self):
		"""
		Overridden to pass on the semantics we inherit from
		RoleUsersManagerMixIn. The user class is a MiddleKit issue
		for us.
		"""
		pass
