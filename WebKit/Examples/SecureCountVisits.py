from SecurePage import SecurePage


class SecureCountVisits(SecurePage):
	"""Secured version of counting visits example."""

	def writeContent(self):
		count = self.session().value('secure_count', 0) + 1
		self.session().setValue('secure_count', count)
		plural = count > 1 and 's' or ''
		self.writeln('<h3>Counting Visits on a Secured Page</h3>')
		if self.request().isSessionExpired():
			self.writeln('<p>Your session has expired.</p>')
		self.writeln("<p>You've been here"
			' <strong style="background-color:yellow">&nbsp;%d&nbsp;</strong>'
			' time%s.</p>' % (count, plural))
		self.writeln('<p>This page records your visits using a session object.'
			' Every time you <a href="javascript:location.reload()">reload</a> or'
			' <a href="SecureCountVisits">revisit</a> this page, the counter will increase.'
			' If you close your browser, then your session will end and you'
			' will see the counter go back to 1 on your next visit.</p>')
		self.writeln('<p>Try hitting <a href="javascript:location.reload()">'
			'reload</a> now.</p>')
		user = self.loggedInUser()
		if user:
			self.writeln('<p>Authenticated user is <strong>%s</strong>.</p>' % user)
		self.writeln('<p><a href="SecureCountVisits">Revisit this page</a> | '
			'<a href="SecureCountVisits?logout=1">Logout</a></p>')
