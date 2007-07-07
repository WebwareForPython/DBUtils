import os, string, sys


class AdminPage:
	"""
	AdminPage is the abstract superclass of all CGI Wrapper administration CGI classes.

	Subclasses typically override title() and writeBody(), but may customize other methods.

	Subclasses use self._var for the various vars that are passed in from CGI Wrapper
	and self.write() and self.writeln().
	"""


	## Init ##

	def __init__(self, vars):
		for name in vars.keys():
			setattr(self, '_'+name, vars[name])
		self._vars = vars


	## HTML ##

	def html(self):
		self._html = []
		self.writeHeader()
		self.writeBody()
		self.writeFooter()
		return string.join(self._html, '')


	## Utility methods ##

	def write(self, *args):
		for arg in args:
			self._html.append(str(arg))

	def writeln(self, *args):
		for arg in args:
			self._html.append(str(arg))
		self._html.append('\n')


	## Content methods ##

	def writeHeader(self):
		self.writeln('''<html>
			<head>
				<title>%s</title>
			</head>
			<body %s><table align=center><tr><td>''' % (self.title(), self.bodyTags()))
		self.writeBanner()
		self.writeToolbar()

	def writeBody(self):
		raise NotImplementedError, 'Should be overridden in a subclass'

	def writeFooter(self):
		self.writeln('<p><br><hr></table></body></html>')

	def title(self):
		raise NotImplementedError, 'Should be overridden in a subclass'

	def bodyTags(self):
		return 'color=black bgcolor=white'

	def writeBanner(self):
		self.writeln('''<table align=center bgcolor=darkblue cellpadding=5 cellspacing=0 width=100%%>
			<tr><td align=center>
				<font face="Tahoma, Arial, Helvetica" color=white><b>
					CGI Wrapper
					<br><font size=+2>%s</font>
				</b></font>
			</td></tr>
		</table><p>''' % self.title())

	def writeToolbar(self):
		pass
