from TaskKit.Task import Task


class SessionTask(Task):

	def __init__(self, sessions):
		Task.__init__(self)
		self._sessionstore = sessions

	def run(self):
		if self.proceed():
			self._sessionstore.cleanStaleSessions(self)
