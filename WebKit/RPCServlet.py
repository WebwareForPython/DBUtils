import traceback, sys

from HTTPServlet import HTTPServlet


class RPCServlet(HTTPServlet):

	def call(self, methodName, *args, **keywords):
		"""Call custom method.

		Subclasses may override this class for custom handling of methods.

		"""
		if methodName in self.exposedMethods():
			return getattr(self, methodName)(*args, **keywords)
		else:
			raise NotImplementedError, methodName

	def exposedMethods(self):
		"""Get exposed methods.

		Subclasses should return a list of methods that will be exposed
		through XML-RPC.

		"""
		return ['exposedMethods']

	def resultForException(self, e, trans):
		"""Get text for exception.

		Given an unhandled exception, returns the string that should be
		sent back in the RPC response as controlled by the
		RPCExceptionReturn setting.

		"""
		# report exception back to server
		setting = trans.application().setting('RPCExceptionReturn')
		assert setting in ('occurred', 'exception', 'traceback'), \
			'setting = %r' % setting
		if setting == 'occurred':
			result = 'unhandled exception'
		elif setting == 'exception':
			result = str(e)
		elif setting == 'traceback':
			result = ''.join(traceback.format_exception(*sys.exc_info()))
		return result

	def sendOK(self, contentType, contents, trans, contentEncoding=None):
		"""Send a 200 OK response with the given contents."""
		response = trans.response()
		response.setStatus(200, 'OK')
		response.setHeader('Content-type', contentType)
		response.setHeader('Content-length', str(len(contents)))
		if contentEncoding:
			response.setHeader('Content-encoding', contentEncoding)
		response.write(contents)

	def handleException(self, transaction):
		"""Handle exception.

		If ReportRPCExceptionsInWebKit is set to True, then flush the response
		(because we don't want the standard HTML traceback to be appended to
		the response) and then handle the exception in the standard WebKit way.
		This means logging it to the console, storing it in the error log,
		sending error email, etc. depending on the settings.

		"""
		setting = transaction.application().setting('ReportRPCExceptionsInWebKit')
		if setting:
			transaction.response().flush()
			transaction.application().handleExceptionInTransaction(
				sys.exc_info(), transaction)

	def transaction(self):
		# most uses of RPC will not need this
		return self._transaction

	def awake(self, transaction):
		HTTPServlet.awake(self, transaction)
		self._transaction = transaction

	def sleep(self, transaction):
		self._transaction = None
		HTTPServlet.sleep(self, transaction)
