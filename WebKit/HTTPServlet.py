from Common import *
from Servlet import Servlet


class HTTPServlet(Servlet):
	"""A HTTP servlet.

	HTTPServlet implements the respond() method to invoke methods such as
	respondToGet() and respondToPut() depending on the type of HTTP request.
	Example HTTP request methods are GET, POST, HEAD, etc.
	Subclasses implement HTTP method FOO in the Python method respondToFoo.
	Unsupported methods return a "501 Not Implemented" status.

	Note that HTTPServlet inherits awake() and respond() methods from
	Servlet and that subclasses may make use of these.

	See also: Servlet

	FUTURE
		* Document methods (take hints from Java HTTPServlet documentation)

	"""


	## Init ##

	def __init__(self):
		Servlet.__init__(self)
		self._methodForRequestType = {}  # a cache; see respond()


	## Transactions ##

	def respond(self, trans):
		"""Respond to a request.

		Invokes the appropriate respondToSomething() method depending on the
		type of request (e.g., GET, POST, PUT, ...).

		"""
		request = trans.request()
		httpMethodName = request.method()
		# For GET and HEAD, handle the HTTP If-Modified-Since header:
		# if the object's last modified time is the same
		# as the IMS header, we're done.
		if httpMethodName in ('GET', 'HEAD'):
			lm = self.lastModified(trans)
			if lm:
				lm = time.strftime('%a, %d %b %Y %H:%M:%S GMT',
					time.gmtime(lm))
				trans.response().setHeader('Last-Modified', lm)
				ifModifiedSince = request.environ().get(
					'HTTP_IF_MODIFIED_SINCE', None)
				if not ifModifiedSince:
					ifModifiedSince = request.environ().get(
						'If-Modified-Since', None)
				if ifModifiedSince and ifModifiedSince.split(';')[0] == lm:
					trans.response().setStatus(304, 'Not Modified')
					# print "304", request.serverSidePath()
					return
		method = self._methodForRequestType.get(httpMethodName, None)
		if not method:
			methName = 'respondTo' + httpMethodName.capitalize()
			method = getattr(self, methName, self.notImplemented)
			self._methodForRequestType[httpMethodName] = method
		method(trans)

	def notImplemented(self, trans):
		trans.response().setStatus(501, 'Not Implemented')

	def lastModified(self, trans):
		"""Get time of last modification.

		Return this object's Last-Modified time (as a float),
		or None (meaning don't know or not applicable).

		"""
		return None

	def respondToHead(self, trans):
		"""Respond to a HEAD request.

		A correct but inefficient implementation.

		"""
		res = trans.response()
		w = res.write
		res.write = lambda *args: None
		self.respondToGet(trans)
		res.write = w
