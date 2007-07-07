from Page import Page


class Page051(Page):
	"""
	This class is provided exclusively for backwards compatibility with the
	various writeFoo() methods as found in Page of WebKit 0.5.1 and earlier.
	If you have an existing site, you can change your Page classes to inherit
	Page051 in order to make them work.

	However, it is very easy to "upgrade" your site to the new version of
	Page, and we highly recommend that you do since the Page API is easier
	to customize and extend in subclasses.
	"""

	def writeHTML(self):
		"""
		Subclasses may override this method, which is invoked by
		respondToGet() and respondToPost()) or it's constituent methods,
		writeHeader(), writeBody() and writeFooter().
		"""
		self.writeln('<html>')
		self.writeHeader()
		self.writeBody()
		self.writeFooter()
		self.writeln('</html>')

	def writeHeader(self):
		self.writeln('''<head>
	<title>%s</title>
</head>
<body %s>''' % (self.title(), self.htBodyArgs()))

	def writeBody(self):
		self.writeln("<p>This page has not yet customized it's body.</p>")

	def writeFooter(self):
		self.writeln('</body>')
