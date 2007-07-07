import re

from ModelObject import ModelObject
from MiscUtils import NoDefault, StringTypes
from MiddleDict import MiddleDict

try: # for Python < 2.3
	True, False
except NameError:
	True, False = 1, 0

nameRE = re.compile(r'^([A-Za-z_][A-Za-z_0-9]*)$')


class Attr(MiddleDict, ModelObject):
	"""
	An Attr represents an attribute of a Klass mostly be being a dictionary-like object.
	"""

	def __init__(self, dict):
		MiddleDict.__init__(self, {})
		for key, value in dict.items():
			if key == 'Attribute':
				key = 'Name'
			# @@ 2001-02-21 ce: should we always strip string fields? Probably.
			if type(value) in StringTypes and value.strip() == '':
				value = None
			self[key] = value
		match = nameRE.match(self['Name'])
		if match is None or len(match.groups()) != 1:
			raise ValueError, 'Bad name (%r) for attribute: %r.' % (self['Name'], dict)
		self._getPrefix = None
		self._setPrefix = None

	def name(self):
		return self.data['Name']

	def isRequired(self):
		"""
		Returns true if a value is required for this attribute. In Python, that means the
		value cannot be None. In relational theory terms, that means the value cannot be
		NULL.
		"""
		return self.boolForKey('isRequired')

	def setKlass(self, klass):
		""" Sets the klass that the attribute belongs to. """
		self._klass = klass

	def klass(self):
		"""
		Returns the klass that this attribute is declared in and, therefore, belongs to.
		"""
		return self._klass

	def pyGetName(self):
		"""
		Returns the name that should be used for the Python "get" accessor method for this
		attribute.
		"""
		if self._getPrefix is None:
			self._computePrefixes()
		name = self.name()
		if self._getCapped:
			return self._getPrefix + name[0].upper() + name[1:]
		else:
			return self._getPrefix + name

	def pySetName(self):
		"""
		Returns the name that should be used for the Python "set" accessor method for this
		attribute.
		"""
		if self._setPrefix is None:
			self._computePrefixes()
		name = self.name()
		if self._setCapped:
			return self._setPrefix + name[0].upper() + name[1:]
		else:
			return self._setPrefix + name

	def setting(self, name, default=NoDefault):
		"""
		Returns the value of a particular configuration setting taken
		from the model.

		Implementation note: Perhaps a future version should ask the
		klass and so on up the chain.
		"""
		return self.model().setting(name, default)

	def model(self):
		return self._klass.klasses()._model

	def awakeFromRead(self):
		pass


	## Warnings ##

	def printWarnings(self, out):
		pass


	## Self Util ##

	def _computePrefixes(self):
		style = self.setting('AccessorStyle', 'methods').lower()
		assert style in ('properties', 'methods')
		if style == 'properties':
			self._getPrefix = '_get_'
			self._setPrefix = '_set_'
			self._getCapped = False
			self._setCapped = False
		else:
			# methods
			self._getPrefix = ''
			self._setPrefix = 'set'
			self._getCapped = False
			self._setCapped = True
