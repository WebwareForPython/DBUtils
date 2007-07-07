
from WebKit.Page import Page


class Main(Page):

	def writeContent(self):
		self.writeln('<h1>Welcome to Webware!</h1>')
		self.writeln('<h2>Test passed.</h2>')
