from Attr import Attr


class ListAttr(Attr):
	"""
	This is an attribute that refers to a set of other user-defined objects.
	It cannot include basic data types or instances of classes that are not part of the object model.
	"""

	def __init__(self, dict):
		Attr.__init__(self, dict)
		self._className = dict['Type'].split()[-1]
		self._backRefAttr = None  # init'ed in awakeFromRead()
		if self.get('Min') is not None:
			self['Min'] = int(self['Min'])
		if self.get('Max') is not None:
			self['Max'] = int(self['Max'])

	def className(self):
		""" Returns the name of the base class that this obj ref attribute points to. """
		return self._className

	def backRefAttrName(self):
		"""
		Returns the name of the back-reference attribute in the referenced
		class.  It is necessary to be able to override the default back ref
		to create data structures like trees, in which a Middle object might
		reference a parent and multiple children, all of the same class as
		itself.
		"""
		assert self._backRefAttr is not None
		return self._backRefAttr

	def awakeFromRead(self):
		"""
		Check that the target class and backRefAttr actually exist.
		"""
		# Check that for "list of Foo", Foo actually exists. And,
		# Compute self._targetKlass.
		from Model import ModelError
		self._targetKlass = self.model().klass(self.className(), None)
		if not self._targetKlass:
			raise ModelError, 'class %s: attr %s: cannot locate target class %s for this list.' % (
				self.klass().name(), self.name(), self.className())

		# Compute self._backRefAttr.
		if self.has_key('BackRefAttr'):
			backRefName = self['BackRefAttr']
		else:
			backRefName = self.klass().name()
			attr = self._targetKlass.lookupAttr(backRefName, None)
			if attr is None:
				className = self.klass().name()
				backRefName = className[0].lower() + className[1:]
		self._backRefAttr = backRefName

		# Check that the backRefAttr, whether explicit or implicit, exists in the target class.
		backRefAttr = self._targetKlass.lookupAttr(self.backRefAttrName(), None)
		if backRefAttr is None:
			raise ModelError, 'class %s: attr %s: cannot locate backref attr %s.%s for this list.' % (
				self.klass().name(), self.name(), self.className(), self.backRefAttrName())
		backRefAttr['isBackRefAttr'] = 1
