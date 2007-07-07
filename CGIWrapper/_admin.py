from time import time, localtime, gmtime, asctime
from AdminPage import *


class Page(AdminPage):

	def title(self):
		return 'Admin'

	def writeBody(self):
		curTime = time()
		self.writeln('''
	<table align=center cellspacing=0 cellpadding=0 borde=0>
		<tr> <td><b>Version:</b></td> <td>%s</td> </tr>
		<tr> <td><b>Local time:</b></td> <td>%s</td> </tr>
		<tr> <td><b>Global time:</b></td> <td>%s</td> </tr>
	</table>
	''' % (self._wrapper.version(),
		asctime(localtime(curTime)), asctime(gmtime(curTime))))

		self.startMenu()
		# @@ 2000-04-21 ce: use URLEncode() here.
		self.menuItem('Script log contents', '_dumpCSV?filename=%s'
			% self._wrapper.setting('ScriptLogFilename'))
		self.menuItem('Error log contents', '_dumpErrors?filename=%s'
			% self._wrapper.setting('ErrorLogFilename'))
		self.menuItem('Show config', '_showConfig')
		self.endMenu()

		self.writeln('''
<!--
begin-parse
{
	'Version': %s,
	'LocalTime': %s,
	'GlobalTime': %s
}
end-parse
-->''' % (repr(self._wrapper.version()),
	repr(localtime(curTime)), repr(gmtime(curTime))))

	def startMenu(self):
		self.writeln('''<p>&nbsp;</p><table align="center" border="0"'
			' cellspacing="2" cellpadding="2" bgcolor="#FFFFDD">'
			'<tr bgcolor="black"><td align="center">'
			'<b style="color:white;font-family:Arial,Helvetica,sans-serif">Menu</b>'
			'</td></tr>''')

	def menuItem(self, title, url):
		self.writeln('<tr><td><a href="%s">%s</a></td></tr>' % (url, title))

	def endMenu(self):
		self.writeln('</table>')
