from time import sleep

from WebKit.Page import Page


class PushServlet(Page):
	"""Pushing Content Demo.

	This is a test servlet for the buffered output streams of the app servers.
	This probably won't work with the CGI adapters. At least on Apache, the
	data doesn't seem to get flushed.

	This will not have the expected functionality on Internet Explorer, as it
	does not support the x-mixed-replace content type. Opera does, though.

	"""

	_boundary = "if-you-see-this-your-browser-does-not-support" \
		"-multipart/x-mixed-replace"

	def respond(self, transaction):
		# this isn't necessary, but it's here as an example:
		self.response().streamOut().setAutoCommit()
		# send the initial header:
		self.initialHeader()
		# push new content 4 times:
		for i in range(4):
			self.sendBoundary()
			self.sendLF()
			self.writeHTML(i)
			self.sendLF()
			# send the currently buffered output now:
			self.response().flush()
			sleep(i and 5 or 15)

	def initialHeader(self):
		self.response().setHeader("Content-type",
			"multipart/x-mixed-replace; boundary=" + self._boundary)

	def sendBoundary(self):
		self.write("--" + self._boundary)

	def sendLF(self):
		self.write("\r\n")

	def writeHTML(self, count):
		self.write("Content-type: text/html\r\n\r\n")
		wr = self.writeln
		wr('<html><body style="margin:8pt;"><div style='
			'"background-color:#EEF;padding:8pt 16pt;border:2px solid blue">')
		wr('<h1>Pushing Content Demo</h1>')
		if count:
			wr('<h3>This page has been replaced'
				' <strong style="color:#339">%d</strong> time%s.</h3>'
				% (count, count > 1 and 's' or ''))
			if count == 3:
				wr('<p>Stopped pushing contents.</p>')
			else:
				wr('<p>Next content will be pushed'
					' <strong>in 5</strong> seconds.</p>')
		else:
			wr('<p>This servlet will try to replace the content'
				' <strong>in 15 seconds</strong>.</p>')
		if not count or count == 3:
			wr('<h4>Note:</h4>')
			if count == 3:
				wr("<p>If you didn't get output for the last 30 seconds, "
					"pushing contents is not supported.</p>")
			wr('<p>The Browser needs to support the <tt>x-mixed-replace</tt>'
				' content type. Current versions of the Microsoft Internet'
				' Explorer and other browsers may not have this functionality.'
				' It will work with Firefox and Opera, though. Also, the'
				' adapter on the server side must support this. It will not'
				' work with the CGI adapter or the built-in HTTP server.</p>')
		wr('</div></body></html>')
