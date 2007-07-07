"""HTTPExceptions

HTTPExceptions are for situations that are predicted by the
HTTP spec. Where the ``200 OK`` response is typical, a
``404 Not Found`` or ``301 Moved Temporarily`` response is not
entirely unexpected.

`Application` catches all `HTTPException` exceptions (and subclasses
of HTTPException), and instead of being errors these are translated
into responses. In various places these can also be caught and
changed, for instance an `HTTPAuthenticationRequired` could be
turned into a normal login page.

"""

from WebUtils.Funcs import htmlEncode


class HTTPException(Exception):
	"""HTTPException template class.

	Subclasses must define these variables (usually as class variables):

	`_code`:
	    a tuple of the integer error code, and the short
	    description that goes with it (like ``(200, "OK")``)
	`_description`:
	    the long-winded description, to be presented
	    in the response page. Or you can override description()
	    if you want something more context-sensitive.

	"""

	def __str__(self):
		return '%d %s' % (self.code(), self.codeMessage())


	## Error codes ##

	_description = 'An error occurred'

	def code(self):
		"""The integer code."""
		return self._code[0]

	def codeMessage(self):
		"""The message (like ``Not Found``) that goes with the code."""
		return self._code[1]


	## HTML Description ##

	def html(self):
		"""The error page.

		The HTML page that should be sent with the error,
		usually a description of the problem.

		"""
		return '''
<html><head><title>%(code)s %(title)s</title></head>
<body>
<h1>%(htTitle)s</h1>
%(body)s
</body></html>''' % {
			"htTitle": self.htTitle(),
			"title": self.title(),
			"body": self.htBody(),
			"code": self.code()
			}

	def title(self):
		"""The title used in the HTML page."""
		return self.codeMessage()

	def htTitle(self):
		"""The title, but it may include HTML markup (like italics)."""
		return self.title()

	def htBody(self):
		"""The HTML body of the page."""
		body = self.htDescription()
		if self.args:
			body += ''.join(['<p>%s</p>\n'
				% htmlEncode(str(p)) for p in self.args])
		return body

	def description(self):
		"""Error description.

		Possibly a plain text version of the error description,
		though usually just identical to `htDescription`.

		"""
		return self._description

	def htDescription(self):
		"""HTML error description.

		The HTML description of the error, for presentation
		to the browser user.

		"""
		return self.description()


	## Misc ##

	def headers(self):
		"""Get headers.

		Additional headers that should be sent with the
		response, not including the Status header. For instance,
		the redirect exception adds a Location header.

		"""
		return {}

	def setTransaction(self, trans):
		"""Set transaction.

		When the exception is caught by `Application`, it tells
		the exception what the transaction is. This way you
		can resolve relative paths, or otherwise act in a manner
		sensitive of the context of the error.

		"""
		self._transaction = trans


class HTTPMovedPermanently(HTTPException):
	"""HTTPExcecption "moved permanently" subclass.

	When a resource is permanently moved. The browser may remember this
	relocation, and later requests may skip requesting the original
	resource altogether.

	"""
	_code = 301, 'Moved Permanently'

	def __init__(self, location=None, webkitLocation=None, *args):
		"""Set destination.

		HTTPMovedPermanently needs a destination that you it should be
		directed to -- you can pass `location` *or* `webkitLocation` --
		if you pass `webkitLocation` it will be relative to the WebKit base
		(the portion through the adapter).
		"""
		self._location = location
		self._webkitLocation = webkitLocation
		HTTPException.__init__(self, 301, 'Moved Permanently', *args)

	def location(self):
		"""The location that we will be redirecting to."""
		if self._webkitLocation:
			location = self._transaction.request().servletPath()
			if not self._webkitLocation.startswith('/'):
				location += '/'
			location += self._webkitLocation
		else:
			location = self._location
		return location

	def headers(self):
		"""We include a Location header."""
		return {'Location': self.location()}

	def description(self):
		return 'The resource you are accessing has been moved to' \
			' <a href="%s">%s</a>' % ((htmlEncode(self.location()),)*2)


class HTTPTemporaryRedirect(HTTPMovedPermanently):
	"""HTTPExcecption "temporary tedirect" subclass.

	Like HTTPMovedPermanently, except the redirect is only valid for this
	request. Internally identical to HTTPMovedPermanently, except with a
	different response code. Browsers will check the server for each request
	to see where it's redirected to.

	"""
	_code = 307, 'Temporary Redirect'

# This is what people mean most often:
HTTPRedirect = HTTPTemporaryRedirect


class HTTPBadRequest(HTTPException):
	"""HTTPExcecption "bad request" subclass.

	When the browser sends an invalid request.

	"""
	_code = 400, 'Bad Request'


class HTTPAuthenticationRequired(HTTPException):
	"""HTTPExcecption "authentication required" subclass.

	HTTPAuthenticationRequired will usually cause the browser to open up an
	HTTP login box, and after getting login information from the user, the
	browser will resubmit the request. However, this should also trigger
	login pages in properly set up environments (though much code will not
	work this way).

	Browsers will usually not send authentication information unless they
	receive this response, even when other pages on the site have given 401
	responses before. So when using this authentication every request will
	usually be doubled, once without authentication, once with.

	"""
	_code = 401, 'Authentication Required'
	_description = "You must log in to access this resource"

	def __init__(self, realm=None, *args):
		if not realm:
			realm = 'Password required'
		assert realm.find('"') == -1, 'Realm must not contain "'
		self._realm = realm
		HTTPException.__init__(self, *args)

	def headers(self):
		return {'WWW-Authenticate': 'Basic realm="%s"' % self._realm}

# This is for wording mistakes. I'm unsure about their benefit.
HTTPAuthorizationRequired = HTTPAuthenticationRequired
"""
There is also an alias `HTTPAuthorizationRequired`, as it is hard
to distinguish between these two names.
"""


class HTTPSessionExpired(HTTPException):
	"""HTTPExcecption "session expired" subclass.

	This is the same as HTTPAuthenticationRequired, but should be used
	in the situation when a session has expired.

	"""
	_code = 401, 'Session Expired'
	_description = 'Your login session has expired - please log in again'


class HTTPForbidden(HTTPException):
	"""HTTPExcecption "forbidden" subclass.

	When access is not allowed to this resource. If the user is anonymous,
	and must be authenticated, then HTTPAuthenticationRequired is a preferable
	exception. If the user should not be able to get to this resource (at
	least through the path they did), or is authenticated and still doesn't
	have access, or no one is allowed to view this, then HTTPForbidden would
	be the proper response.

	"""
	_code = 403, 'Forbidden'
	_description = "You are not authorized to access this resource"


class HTTPNotFound(HTTPException):
	"""HTTPExcecption "not found" subclass.

	When the requested resource does not exist. To be more secretive,
	it is okay to return a 404 if access to the resource is not permitted
	(you are not required to use HTTPForbidden, though it makes it more
	clear why access was disallowed).

	"""
	_code = 404, 'Not Found'
	_description = 'The resource you were trying to access was not found'

	def html(self):
		trans = self._transaction
		page = trans.application()._error404
		if page:
			uri = trans.request().uri()
			return page % htmlEncode(uri)
		else:
			return HTTPException.html(self)


class HTTPMethodNotAllowed(HTTPException):
	"""HTTPExcecption "method not allowed" subclass.

	When a method (like GET, PROPFIND, POST, etc) is not allowed
	on this resource (usually because it does not make sense, not
	because it is not permitted). Mostly for WebDAV.

	"""
	_code = 405, 'Method Not Allowed'
	_description = 'The method is not supported on this resource'


class HTTPRequestTimeout(HTTPException):
	"""HTTPExcecption "request timeout" subclass.

	The client did not produce a request within the time that the
	server was prepared to wait. The client may repeat the request
	without modifications at any later time.

	"""
	_code = 408, 'Request Timeout'


class HTTPConflict(HTTPException):
	"""HTTPExcecption "conflict" subclass.

	When there's a locking conflict on this resource (in response to
	something like a PUT, not for most other conflicts). Mostly for WebDAV.

	"""
	_code = 409, 'Conflict'


class HTTPUnsupportedMediaType(HTTPException):
	"""HTTPExcecption "unsupported media type" subclass.

	The server is refusing to service the request because the entity
	of the request is in a format not supported by the requested resource
	for the requested method.

	"""
	_code = 415, 'Unsupported Media Type'


class HTTPPreconditionFailed(HTTPException):
	"""HTTPExcecption "Precondition Failed" subclass.

	During compound, atomic operations, when a precondition for an early
	operation fail, then later operations in will fail with this code.
	Mostly for WebDAV.

	"""
	_code = 412, 'Precondition Failed'


class HTTPServerError(HTTPException):
	"""HTTPExcecption "Server Error" subclass.

	The server encountered an unexpected condition which prevented it
	from fulfilling the request.

	"""
	_code = 500, 'Server Error'


class HTTPNotImplemented(HTTPException):
	"""HTTPExcecption "not implemented" subclass.

	When methods (like GET, POST, PUT, PROPFIND, etc) are not
	implemented for this resource.

	"""
	_code = 501, "Not Implemented"
	_description = "The method given is not yet implemented by this application"


class HTTPInsufficientStorage(HTTPException):
	"""HTTPExcecption "insufficient storage" subclass.

	When there is not sufficient storage, usually in response to a PUT when
	there isn't enough disk space. Mostly for WebDAV.

	"""
	_code = 507, 'Insufficient Storage'
	_description = 'There was not enough storage space on the server to complete your request'
