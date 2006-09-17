from ExamplePage import ExamplePage


class PlugInInspector(ExamplePage):
	"""Plug-in Inspector.

	This example is not public yet.
	And this should probably just be axed and something
	real added in Admin/PlugIns.

	"""

	def writeContent(self):
		wr = self.writeln
		for pi in self.application().server().plugIns():
			wr('<h4>%s</h4>' % self.htmlEncode(repr(pi)))
			for item in dir(pi):
				wr('<p><b>%s</b> = %s' % (item,
					self.htmlEncode(str(getattr(pi, item)))))
			self.writeln('<hr>')
