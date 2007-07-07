from AdminPage import *


class _showConfig(AdminPage):

	def title(self):
		return 'Config'

	def writeBody(self):
		import CGIWrapper
		self.writeln(CGIWrapper.htDictionary(self._wrapper.config()))
