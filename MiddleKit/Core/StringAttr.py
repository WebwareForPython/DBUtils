from BasicTypeAttr import BasicTypeAttr


class StringAttr(BasicTypeAttr):

	def __init__(self, dict):
		BasicTypeAttr.__init__(self, dict)
		if self.get('Max') is not None:
			self['Max'] = int(self['Max'])
		if self.get('Min') is not None:
			self['Min'] = int(self['Min'])

	def printWarnings(self, out):
		if self.get('Max') in (None, '') and not self.get('SQLType'):
			out.write('warning: model %s: class %s: attr %s: max string length unspecified\n' % (
				self.model().name(), self.klass().name(), self.name()))
