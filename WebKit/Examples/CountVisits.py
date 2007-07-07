from ExamplePage import ExamplePage


class CountVisits(ExamplePage):
	"""Counting visits example."""

	def writeContent(self):
		count = self.session().value('count', 0) + 1
		self.session().setValue('count', count)
		plural = count > 1 and 's' or ''
		self.writeln('<h3>Counting Visits</h3>')
		if self.request().isSessionExpired():
			self.writeln('<p>Your session has expired.</p>')
		self.writeln("<p>You've been here"
			' <strong style="background-color:yellow">&nbsp;%d&nbsp;</strong>'
			' time%s.</p>' % (count, plural))
		self.writeln('<p>This page records your visits using a session object.'
			' Every time you <a href="javascript:location.reload()">reload</a> or'
			' <a href="CountVisits">revisit</a> this page, the counter will increase.'
			' If you close your browser, then your session will end and you'
			' will see the counter go back to 1 on your next visit.</p>')
		self.writeln('<p>Try hitting <a href="javascript:location.reload()">'
			'reload</a> now.</p>')
