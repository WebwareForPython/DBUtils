from WebKit.Page import Page
from WebKit.Application import Application
from string import replace, split, strip
import os


class Servlet(Page):
	"""Test of extra path info."""

	def title(self):
		return self.__doc__

	def writeBody(self):
		self.writeln('<h2>WebKit Testing Servlet</h2>')
		self.writeln('<h3>%s</h3>' % self.title())
		req = self.request()
		self.writeln("<p>serverSidePath = <tt>%s</tt></p>" % req.serverSidePath())
		self.writeln("<p>extraURLPath = <tt>%s</tt></p>" % req.extraURLPath())
