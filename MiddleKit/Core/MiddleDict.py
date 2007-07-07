from UserDict import UserDict
from MiscUtils import StringTypes

try: # for Python < 2.3
	True, False
except NameError:
	True, False = 1, 0


class MiddleDict(UserDict):
	"""
	A UserDict for the purposes of MiddleKit, specifically Klass and
	Attr which are subclasses.

	@@ 2004-04-02 CE: Should consider making this case-preserving, but
	   case-insensitive with respect to keys.
	"""

	def boolForKey(self, key, default=False):
		"""
		Returns True or False for the given key. Returns False if the
		key does not even exist. Raises a value error if the key
		exists, but cannot be parsed as a bool.
		"""
		original = self.get(key, default)
		s = original
		if type(s) in StringTypes:
			s = s.lower().strip()
		if s in (False, '', None, 0, 0.0, '0', 'false'):
			return False
		elif s in (True, 1, '1', 1.0, 'true'):
			return True
		else:
			raise ValueError, ('%r for attr %r should be a boolean value'
				' (1, 0, True, False) but is %r instead'
				% (key, self.get('Name', '(UNNAMED)'), original))
