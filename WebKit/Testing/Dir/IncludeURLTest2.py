from WebKit.Page import Page
from WebKit.Testing.IncludeURLTest import IncludeURLTest


class IncludeURLTest2(IncludeURLTest):
	"""This is the second part of the URL test code.

	It gets included into the IncludeURLTest, and calls methods
	on other servlets to verify the references continue to work.

	"""

	def writeBody(self):
		self.writeln('<body style="margin:6pt;font-family:sans-serif">')
		self.writeln('<h2>%s</h2>' % self.__class__.__name__)
		self.writeln('<h3>class = <tt>%s</tt>, module= <tt>%s</tt></h3>' %
			(self.__class__.__name__, self.__module__))
		self.writeln('<p>%s</p>' %
			self.__class__.__doc__.replace('\n\n', '</p><p>'))
		self.writeStatus()
		self.cmos("/Testing/", "serverSidePath",
			"Expect to see the serverSidePath of the Testing/Main module.")
		self.writeln('</body>')
