from types import FloatType, IntType, LongType, StringType, TupleType

from Common import *

# time.gmtime() no longer returns a tuple, and there is no globally defined
# type for this at the moment.
TimeTupleType = type(time.gmtime(0))

from Response import Response
from Cookie import Cookie
from HTTPExceptions import HTTPException, HTTPServerError
from MiscUtils import mxDateTime as DateTime
from MiscUtils.DateInterval import timeDecode

debug = False


class HTTPResponse(Response):


	## Init ##

	def __init__(self, transaction, strmOut, headers=None):
		"""Initialize the request."""

		Response.__init__(self, transaction, strmOut)

		self._committed = False

		if headers is None:
			self._headers = {}
			self.setHeader('Content-type', 'text/html')
		else:
			self._headers = headers

		self._cookies = {}


	## Headers ##

	def header(self, name, default=NoDefault):
		"""Return the value of the specified header."""
		if default is NoDefault:
			return self._headers[name.capitalize()]
		else:
			return self._headers.get(name.capitalize(), default)

	def hasHeader(self, name):
		return self._headers.has_key(name.capitalize())

	def setHeader(self, name, value):
		"""Set a specific header by name.

		Parameters:
			name: the header name
			value: the header value

		"""
		assert not self._committed, "Headers have already been sent."
		self._headers[name.capitalize()] = value

	def addHeader(self, name, value):
		"""deprecated: HTTPResponse.addHeader() on 01/02/12 in 0.6.

		Use setHeader() instead.@

		Add a specific header by name.

		"""
		self.deprecated(self.addHeader)
		assert not self._committed, "Headers have already been sent."
		self.setHeader(name, value)

	def headers(self, name=None):
		"""Return all the headers.

		Returns a dictionary-style object of all header objects contained by
		this request.

		"""
		return self._headers

	def clearHeaders(self):
		"""Clear all the headers.

		You might consider a setHeader('Content-type', 'text/html')
		or something similar after this.

		"""
		assert not self._committed, "Headers have already been sent."
		self._headers = {}


	## Cookies ##

	def cookie(self, name):
		"""Return the value of the specified cookie."""
		return self._cookies[name]

	def hasCookie(self, name):
		"""Return True if the specified cookie is present."""
		return self._cookies.has_key(name)

	def setCookie(self, name, value, path='/', expires='ONCLOSE',
			secure=False):
		"""Set a cookie.

		You can also set the path (which defaults to /).
		You can also set when it expires. It can expire:
		  'NOW': this is the same as trying to delete it, but it
		    doesn't really seem to work in IE
		  'ONCLOSE': the default behavior for cookies (expires when
		             the browser closes)
		  'NEVER': some time in the far, far future.
		  integer: a timestamp value
		  tuple: a tuple, as created by the time module
		  DateTime: an mxDateTime object for the time (assumed to
		    be *local*, not GMT time)
		  DateTimeDelta: a interval from the present, e.g.,
		    DateTime.DateTimeDelta(month=1) (1 month in the future)
		    '+...': a time in the future, '...' should be something like
		    1w (1 week), 3h46m (3:45), etc.  You can use y (year),
		    b (month), w (week), d (day), h (hour), m (minute),
		    s (second). This is done by the MiscUtils.DateInterval.

		"""
		cookie = Cookie(name, value)
		if expires == 'ONCLOSE' or not expires:
			pass # this is already default behavior
		elif expires == 'NOW':
			cookie.delete()
			return
		elif expires == 'NEVER':
			t = time.gmtime(time.time())
			if expires == 'NEVER':
				t = (t[0] + 10,) + t[1:]
			t = time.strftime("%a, %d-%b-%Y %H:%M:%S GMT", t)
			cookie.setExpires(t)
		else:
			t = expires
			if type(t) is StringType and t and t[0] == '+':
				interval = timeDecode(t[1:])
				t = time.time() + interval
			if type(t) in (IntType, LongType, FloatType):
				t = time.gmtime(t)
			if type(t) in (TupleType, TimeTupleType):
				t = time.strftime("%a, %d-%b-%Y %H:%M:%S GMT", t)
			if DateTime and \
					(type(t) is DateTime.DateTimeDeltaType
				or isinstance(t, DateTime.RelativeDateTime)):
				t = DateTime.now() + t
			if DateTime and type(t) is DateTime.DateTimeType:
				t = (t - t.gmtoffset()).strftime("%a, %d-%b-%Y %H:%M:%S GMT")
			cookie.setExpires(t)
		if path:
			cookie.setPath(path)
		if secure:
			cookie.setSecure(secure)
		self.addCookie(cookie)

	def addCookie(self, cookie):
		"""Add a cookie that will be sent with this response.

		cookie is a Cookie object instance. See WebKit.Cookie.

		"""
		assert not self._committed, "Headers have already been sent."
		assert isinstance(cookie, Cookie)
		self._cookies[cookie.name()] = cookie

	def delCookie(self, name):
		"""Delete a cookie at the browser.

		To do so, one has to create and send to the browser a cookie with
		parameters that will cause the browser to delete it.

		"""
		if self._cookies.has_key(name):
			self._cookies[name].delete()
		else:
			cookie = Cookie(name, None)
			cookie.delete()
			self.addCookie(cookie)

	def cookies(self):
		"""Get all the cookies.

		Returns a dictionary-style object of all Cookie objects that will
		be sent with this response.

		"""
		return self._cookies

	def clearCookies(self):
		"""Clear all the cookies."""
		assert not self._committed, "Headers have already been sent."
		self._cookies = {}


	## Status ##

	def setStatus(self, code, msg=''):
		"""Set the status code of the response, such as 200, 'OK'."""
		assert not self._committed, "Headers have already been sent."
		self.setHeader('Status', str(code) + ' ' + msg)


	## Special responses ##

	def sendError(self, code, msg=''):
		"""Set the status code to the specified code and message."""
		assert not self._committed, "Response already partially sent."
		self.setStatus(code, msg)

	def sendRedirect(self, url):
		"""Redirect to another url.

		This method sets the headers and content for the redirect, but does
		NOT change the cookies. Use clearCookies() as appropriate.

        See http://www.ietf.org/rfc/rfc2616 (section 10.3.3),
        http://www.ietf.org/rfc/rfc3875 (section 6.2.3) and
        http://support.microsoft.com/kb/176113
        (removing cookies by IIS is considered a bug).

		"""
		assert not self._committed, "Headers have already been sent."
		self.setHeader('Status', '302 Redirect')
		self.setHeader('Location', url)
		self.setHeader('Content-type', 'text/html')
		self.write('<html><body>This page has been redirected'
			' to <a href="%s">%s</a>.</body> </html>' % (url, url))


	## Output ##

	def write(self, charstr=None):
		"""Write charstr to the response stream."""
		if charstr:
			self._strmOut.write(charstr)
		if not self._committed and self._strmOut._needCommit:
			self.commit()

	def flush(self, autoFlush=True):
		"""Send all accumulated response data now.

		Commits the response headers and tells the underlying stream to flush.
		if autoFlush is true, the responseStream will flush itself automatically
		from now on.

		"""
		if not self._committed:
			self.commit()
		self._strmOut.flush()
		self._strmOut.setAutoCommit(autoFlush)

	def isCommitted(self):
		"""Check whether response is already commited.

		Checks whether the reponse has already been partially or completely sent.
		If this returns true, no new headers/cookies can be added
		to the response.

		"""
		return self._committed

	def deliver(self):
		"""Deliver response.

		The final step in the processing cycle.
		Not used for much with responseStreams added.

		"""
		if debug:
			print "HTTPResponse deliver called"
		self.recordEndTime()
		if not self._committed:
			self.commit()

	def commit(self):
		"""Commit response.

		Write out all headers to the reponse stream, and tell the underlying
		response stream it can start sending data.

		"""
		if debug:
			print "HTTPResponse commit"
		self.recordSession()
		if self._transaction.errorOccurred():
			err = self._transaction.error()
			if not isinstance(err, HTTPException):
				err = HTTPServerError()
				self._transaction.setError(err)
			self.setErrorHeaders(err)
		self.writeHeaders()
		self._committed = True
		self._strmOut.commit()

	def writeHeaders(self):
		"""Write headers to the response stream. Used internally."""
		if self._committed:
			print "response.writeHeaders called when already committed"
			return
		# make sure the status header comes first
		if self._headers.has_key('Status'):
			# store and temporarily delete status
			status = self._headers['Status']
			del self._headers['Status']
		else:
			# invent meaningful status
			status = self._headers.has_key('Location') \
				and '302 Redirect' or '200 OK'
		head = ['Status: %s' % status]
		head.extend(map(lambda h: '%s: %s' % h, self._headers.items()))
		self._headers['Status'] = status # restore status
		head.extend(map(lambda c: 'Set-Cookie: %s' % c.headerValue(),
			self._cookies.values()))
		head.extend(['']*2) # this adds one empy line
		head = '\r\n'.join(head)
		self._strmOut.prepend(head)

	def recordSession(self):
		"""Record session ID.

		Invoked by commit() to record the session ID in the response
		(if a session exists). This implementation sets a cookie for
		that purpose. For people who don't like sweets, a future version
		could check a setting and instead of using cookies, could parse
		the HTML and update all the relevant URLs to include the session ID
		(which implies a big performance hit). Or we could require site
		developers to always pass their URLs through a function which adds
		the session ID (which implies pain). Personally, I'd rather just
		use cookies. You can experiment with different techniques by
		subclassing Session and overriding this method. Just make sure
		Application knows which "session" class to use.

		It should be also considered to automatically add the server port
		to the cookie name in order to distinguish application instances
		running on different ports on the same server, or to use the port
		cookie-attribute introduced with RFC 2965 for that purpose.

		"""
		trans = self._transaction
		app = trans.application()
		if not app.setting('UseCookieSessions'):
			return
		sess = trans.session()
		if sess:
			cookie = Cookie(app.sessionName(trans), sess.identifier())
			cookie.setPath(app.sessionCookiePath(trans))
			if trans.request().isSecure():
				cookie.setSecure(app.setting('SecureSessionCookie'))
			if sess.isExpired() or sess.timeout() == 0:
				cookie.delete() # invalid -- tell client to forget the cookie
			self.addCookie(cookie)
			if debug:
				print '>> recordSession: Setting SID =', sess.identifier()
		else:
			if debug:
				print '>> recordSession: Did not set SID.'

	def reset(self):
		"""Reset the response (such as headers, cookies and contents)."""
		assert not self._committed, \
			"Cannot reset the response; it has already been sent."
		self._headers = {}
		self.setHeader('Content-type', 'text/html')
		self._cookies = {}
		self._strmOut.clear()

	def rawResponse(self):
		"""Return the final contents of the response.

		Don't invoke this method until after deliver().

		Returns a dictionary representing the response containing only
		strings, numbers, lists, tuples, etc. with no backreferences.
		That means you don't need any special imports to examine the contents
		and you can marshal it. Currently there are two keys. 'headers' is
		list of tuples each of which contains two strings: the header and
		it's value. 'contents' is a string (that may be binary, for example,
		if an image were being returned).

		"""
		headers = []
		for key, value in self._headers.items():
			headers.append((key, value))
		for cookie in self._cookies.values():
			headers.append(('Set-Cookie', cookie.headerValue()))
		return {
			'headers': headers,
			'contents': self._strmOut.buffer()
		}

	def size(self):
		"""Return the size of the final contents of the response.

		Don't invoke this method until after deliver().

		"""
		return self._strmOut.size()

	def mergeTextHeaders(self, headerstr):
		"""Merge text into our headers.

		Given a string of headers (separated by newlines),
		merge them into our headers.

		"""
		linesep = "\n"
		lines = headerstr.split("\n")
		for line in lines:
			sep = line.find(":")
			if sep:
				self.setHeader(line[:sep], line[sep+1:].rstrip())


	## Exception reporting ##

	_exceptionReportAttrNames = Response._exceptionReportAttrNames + [
		'committed', 'headers', 'cookies']

	def setErrorHeaders(self, err):
		"""Set error headers for an HTTPException."""
		for header, value in err.headers().items():
			self.setHeader(header, value)
		self.setStatus(err.code(), err.codeMessage())
		self.setHeader('Content-type', 'text/html')

	def displayError(self, err):
		"""Display HTTPException errors, with status codes."""
		assert not self._committed, "Already committed"
		self._strmOut.clear()
		self._strmOut.write(err.html())
		uri = self._transaction.request().uri()
		print 'HTTPResponse: %s: %s' % (uri, err.codeMessage())
		self.commit()
