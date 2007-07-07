import os
from time import time, localtime, gmtime, asctime

from AdminSecurity import AdminSecurity


class Main(AdminSecurity):

	def title(self):
		return 'Admin'

	def writeContent(self):
		self.writeGeneralInfo()
		self.writeSignature()

	def writeGeneralInfo(self):
		app = self.application()
		curTime = time()
		info = [
			('Webware Version', app.webwareVersionString()),
			('WebKit Version',  app.webKitVersionString()),
			('Local Time',      asctime(localtime(curTime))),
			('Up Since',        asctime(localtime(app.server().startTime()))),
			('Num Requests',    app.server().numRequests()),
			('Working Dir',     os.getcwd()),
			('Active Sessions', len(app.sessions()))
			]
		self.writeln('<h2 style="text-align:center">'
			'WebKit Administration Pages</h2>')
		self.writeln('<table cellspacing="2" cellpadding="4" align="center"'
			' style="margin-left:auto;margin-right:auto">')
		for label, value in info:
			self.writeln('<tr">'
				'<th style="background-color:#DDD">%s:</th>'
				'<td style="background-color:#EEE">%s</td></tr>'
				% (label, value))
		self.writeln('</table>')

	def writeSignature(self):
		app = self.application()
		curTime = time()
		self.writeln('''
<!--
begin-parse
{
	'Version': %s,
	'LocalTime': %s,
	'GlobalTime': %s
}
end-parse
-->''' % (repr(app.webKitVersion()),
		repr(localtime(curTime)), repr(gmtime(curTime))))
