from ExamplePage import ExamplePage


class Error(ExamplePage):

	def writeBody(self):
		self.write('<p>About to raise an exception...</p>')
		import UnknownModule
