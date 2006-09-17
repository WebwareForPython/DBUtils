from WebKit.Page import Page


class EmbeddedServlet(Page):
	"""Test extra path info.

	This servlet serves as a test for "extra path info"-style URLs such as:

		http://localhost/WebKit.cgi/Servlet/Extra/Path/Info

	Where the servlet is embedded in the URL, rather than being the last
	component. This servlet simply prints it's fields.

	"""

	def writeBody(self):
		fields = self.request().fields()
		self.writeln('<h2>EmbeddedServlet</h2>')
		self.writeln('<pre>%s</pre>' % self.__class__.__doc__)
		self.writeln('<h3>Fields: %d</h3>' % len(fields))
		self.writeln('<ul>')
		for key, value in fields.items():
			self.writeln('<li>%s = %s</li>'
				% (self.htmlEncode(key), self.htmlEncode(value)))
		self.writeln('</ul>')


