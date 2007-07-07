from Attr import Attr
from types import StringType, IntType


class EnumAttr(Attr):

	def __init__(self, dict):
		Attr.__init__(self, dict)
		# We expect than an 'Enums' key holds the enumeration values
		enums = self['Enums']
		enums = enums.split(',')
		enums = [enum.strip() for enum in enums]
		self._enums = enums
		set = {}
		i = 0
		for enum in self._enums:
			set[enum] = i
			i += 1
		self._enumSet = set

	def enums(self):
		"""Return a sequence of the enum values in their string form."""
		return self._enums

	def hasEnum(self, value):
		if isinstance(value, StringType):
			return self._enumSet.has_key(value)
		else:
			return value >= 0 and value < len(self._enums)

	def intValueForString(self, s):
		return self._enumSet[s]
