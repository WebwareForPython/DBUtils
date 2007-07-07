
from WebKit.Page import Page


class stop(Page):

	def writeContent(self):
		self.writeln('<h2>The AppServer has been stopped.</h2>')
		self.application()._server.initiateShutdown()
