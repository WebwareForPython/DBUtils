from ExamplePage import ExamplePage


class OtherFileTypes(ExamplePage):

	def writeContent(self):
		self.writeln('<h4>Test for other file types:</h4>')
		self.writeLink('test.text')
		self.writeLink('test.html')

	def writeLink(self, link):
		self.write('<p><a href="Tests/%s">%s</a>\n' % (link, link))
