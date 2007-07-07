import cgi, traceback
from types import ListType

from Common import *
from WebUtils import FieldStorage
from WebKit.Cookie import CookieEngine
Cookie = CookieEngine.SimpleCookie
from Request import Request
import HTTPResponse

debug = False


class HTTPRequest(Request):
	"""A type of Message for HTTP requests."""


	## Initialization ##

	def __init__(self, dict=None):
		Request.__init__(self)
		self._stack = []
		if dict:
			# Dictionaries come in from web server adapters like the CGIAdapter
			assert dict['format'] == 'CGI'
			self._time = dict['time']
			self._environ = dict['environ']
			self._input = dict['input']
			self._requestID = dict['requestID']
			self._fields = FieldStorage.FieldStorage(
				self._input, environ=self._environ,
				keep_blank_values=True, strict_parsing=False)
			self._fields.parse_qs()
			self._cookies = Cookie()
			if self._environ.has_key('HTTP_COOKIE'):
				# Protect the loading of cookies with an exception handler,
				# because MSIE cookies sometimes can break the cookie module.
				try:
					self._cookies.load(self._environ['HTTP_COOKIE'])
				except Exception:
					traceback.print_exc(file=sys.stderr)
		else:
			# If there's no dictionary, we pretend we're a CGI script
			# and see what happens...
			self._time = time.time()
			self._environ = os.environ.copy()
			self._input = None
			self._fields = cgi.FieldStorage(keep_blank_values=True)
			self._cookies = Cookie()

		env = self._environ

		# Debugging
		if debug:
			f = open('env.text', 'a')
			save = sys.stdout
			sys.stdout = f
			print '>> env for request:'
			keys = env.keys()
			keys.sort()
			for key in keys:
				print '%s: %s' % (repr(key), repr(env[key]))
			print
			sys.stdout = save
			f.close()

		# Get adapter, servlet path and query string
		self._servletPath = env.get('SCRIPT_NAME', '')
		self._pathInfo = env.get('PATH_INFO', '')
		self._queryString = env.get('QUERY_STRING', '')
		if env.has_key('REQUEST_URI'):
			self._uri = env['REQUEST_URI']
			# correct servletPath if there was a redirection
			if not (self._uri + '/').startswith(self._servletPath + '/'):
				i = self._uri.find(self._pathInfo)
				self._servletPath = i >= 0 and self._uri[:i] or '/'
		else:
			# REQUEST_URI isn't actually part of the CGI standard and some
			# web servers like IIS don't set it (as of 8/22/2000).
			if env.has_key('SCRIPT_URL'):
				self._uri = self._environ['SCRIPT_URL']
				# correct servletPath if there was a redirection
				if not (self._uri + '/').startswith(self._servletPath + '/'):
					i = self._uri.find(self._pathInfo)
					self._servletPath = i >= 0 and self._uri[:i] or '/'
			else:
				self._uri = self._servletPath + self._pathInfo
			if self._queryString:
				self._uri += '?' + self._queryString
		self._absolutepath = env.has_key('WK_ABSOLUTE') # set by adapter
		if self._absolutepath:
			self._fsPath = self.fsPath()

		# We use the cgi module to get the fields,
		# but then change them into an ordinary dictionary of values:
		try:
			keys = self._fields.keys()
		except TypeError:
			# This can happen if, for example, the request is an XML-RPC request,
			# not a regular POST from an HTML form. In that case we just create
			# an empty set of fields.
			keys = []
		dict = {}
		for key in keys:
			value = self._fields[key]
			if type(value) is not ListType:
				if value.filename:
					if debug:
						print "Uploaded File Found"
				else: # i.e., if we don't have a list,
					# we have one of those cgi.MiniFieldStorage objects.
					value = value.value # get it's value.
			else:
				value = map(lambda miniFieldStorage: miniFieldStorage.value,
					value) # extract those value's
			dict[key] = value

		self._fieldStorage = self._fields
		self._fields = dict

		# We use Tim O'Malley's Cookie class to get the cookies,
		# but then change them into an ordinary dictionary of values
		dict = {}
		for key in self._cookies.keys():
			dict[key] = self._cookies[key].value
		self._cookies = dict

		self._contextName = None
		self._serverSidePath = self._serverSideContextPath = None
		self._serverRootPath = self._extraURLPath = ''
		self._sessionExpired = False

		self._pathInfo = self.pathInfo()

		if debug:
			print "Done setting up request, found keys %r" % self._fields.keys()


	## Security ##

	def isSecure(self):
		"""Check whether this is a HTTPS connection."""
		return self._environ.get('HTTPS', '').lower() == 'on'


	## Transactions ##

	def responseClass(self):
		return HTTPResponse.HTTPResponse


	## Values ##

	def value(self, name, default=NoDefault):
		"""Return the value with the given name.

		Values are fields or cookies.
		Use this method when you're field/cookie agnostic.

		"""
		if self._fields.has_key(name):
			return self._fields[name]
		else:
			return self.cookie(name, default)

	def hasValue(self, name):
		return self._fields.has_key(name) or self._cookies.has_key(name)

	def extraURLPath(self):
		return self._extraURLPath


	## Fields ##

	def fieldStorage(self):
		return self._fieldStorage

	def field(self, name, default=NoDefault):
		if default is NoDefault:
			return self._fields[name]
		else:
			return self._fields.get(name, default)

	def hasField(self, name):
		return self._fields.has_key(name)

	def fields(self):
		return self._fields

	def setField(self, name, value):
		self._fields[name] = value

	def delField(self, name):
		del self._fields[name]


	## Cookies ##

	def cookie(self, name, default=NoDefault):
		"""Return the value of the specified cookie."""
		if default is NoDefault:
			return self._cookies[name]
		else:
			return self._cookies.get(name, default)

	def hasCookie(self, name):
		"""Return whether a cookie with the given name exists."""
		return self._cookies.has_key(name)

	def cookies(self):
		"""Return a dict of all cookies the client sent with this request."""
		return self._cookies


	## Variables passed by server ##

	def serverDictionary(self):
		"""Return a dictionary with the data the web server gave us.

		This data includes HTTP_HOST and HTTP_USER_AGENT, for example.

		"""
		return self._environ


	## Sessions ##

	def session(self):
		"""Return the session associated with this request.

		The session is either as specified by sessionId() or newly created.
		This is a convenience for transaction.session()

		"""
		return self._transaction.session()

	def isSessionExpired(self):
		"""Return whether the request originally had an expired session ID.

		Only works if the Application.config setting "IgnoreInvalidSession"
		is set to true; otherwise you get a canned error page on an invalid
		session, so your servlet never gets processed.

		"""
		return self._sessionExpired

	def setSessionExpired(self, sessionExpired):
		self._sessionExpired = sessionExpired


	## Remote info ##

	def remoteUser(self):
		"""Always returns None since authentication is not yet supported.

		Take from CGI variable REMOTE_USER.

		"""
		return self._environ['REMOTE_USER']

	def remoteAddress(self):
		"""Return a string containing the IP address of the client."""
		return self._environ['REMOTE_ADDR']

	def remoteName(self):
		"""Return the fully qualified name of the client that sent the request.

		Returns the IP address of the client if the name cannot be determined.

		"""
		env = self._environ
		return env.get('REMOTE_NAME', env['REMOTE_ADDR'])

	def accept(self, which=None):
		"""Return preferences as requested by the user agent.

		The accepted preferences are returned as a list of codes
		in the same order as they appeared in the header.
		In other words, the explicit weighting criteria are ignored.

		If you do not define otherwise which preferences you are
		interested in ('language', 'charset', 'encoding'), by default
		you will get the user preferences for the content types.

		"""
		var = 'HTTP_ACCEPT'
		if which:
			var += '_' + which.upper()
		prefs = []
		for pref in self._environ.get(var, '').split(','):
			pref = pref.split(';', 1)[0].strip()
			prefs.append(pref)
		return prefs


	## Path ##

	def urlPath(self):
		"""Return URL path without host, adapter and query string.

		For example, http://host/WebKit.cgi/Context/Servlet?x=1
		yields '/Context/Servlet'.

		If self._absolutepath is set, this refers to the filesystem path.

		"""
		if self._absolutepath:
			return self._fsPath
		else:
			return self._pathInfo

	def urlPathDir(self):
		"""Same as urlPath, but only gives the directory."""
		return os.path.dirname(self.urlPath())

	def setURLPath(self, path):
		"""Set the URL path of the request.

		If self._absolutepath is set, this refers to the filesystem path.

		There is rarely a need to do this. Proceed with caution.

		"""
		if self._absolutepath:
			self._fsPath = path
		else:
			self._pathInfo = path
			self._uri = self._servletPath + path
			if self._queryString:
				self._uri += '?' + self._queryString

	def serverSidePath(self, path=None):
		"""Return the absolute server-side path of the request.

		If the optional path is passed in, then it is joined with the
		server side directory to form a path relative to the object.

		"""
		if path:
			if path.startswith('/'):
				path = path[1:]
			return os.path.normpath(os.path.join(
				os.path.dirname(self._serverSidePath), path))
		else:
			return self._serverSidePath

	def serverSideContextPath(self, path=None):
		"""Return the absolute server-side path of the context of this request.

		If the optional path is passed in, then it is joined with the server
		side context directory to form a path relative to the object.

		This directory could be different from the result of serverSidePath()
		if the request is in a subdirectory of the main context directory.

		"""
		if path:
			if path.startswith('/'):
				path = path[1:]
			return os.path.normpath(os.path.join(
				self._serverSideContextPath, path))
		else:
			return self._serverSideContextPath

	def contextName(self):
		"""Return the name of the context of this request.

		This isn't necessarily the same as the name of the directory
		containing the context.

		"""
		return self._contextName

	def servletURI(self):
		"""Return servlet URI without any query strings or extra path info."""
		p = self._pathInfo
		if not self._extraURLPath:
			if p.endswith('/'):
				p = p[:-1]
			return p
		i = p.rfind(self._extraURLPath)
		if i >= 0:
			p = p[:i]
		if p.endswith('/'):
			p = p[:-1]
		return p

	def uriWebKitRoot(self):
		"""Return relative URL path of the WebKit root location."""
		if not self._serverRootPath:
			self._serverRootPath = ''
			loc = self.urlPath()
			loc, curr = os.path.split(loc)
			while 1:
				loc, curr = os.path.split(loc)
				if not curr:
					break
				self._serverRootPath += "../"
		return self._serverRootPath

	def fsPath(self):
		"""The filesystem path of the request according to the webserver."""
		fspath = self.adapterFileName()
		if not fspath:
			fspath = self.servletPath()
			docroot = self._environ['DOCUMENT_ROOT']
			fspath = os.path.join(docroot, fspath)
		return fspath

	def serverURL(self, canonical=False):
		"""Return the full internet path to this request.

		This is the URL that was actually received by the webserver
		before any rewriting took place. If canonical is set to true,
		then the canonical hostname of the server is used if possible.

		The path is returned without any extra path info or query strings,
		i.e. http://www.my.own.host.com:8080/WebKit/TestPage.py

		"""
		if canonical and self._environ.has_key('SCRIPT_URI'):
			return self._environ['SCRIPT_URI']
		else:
			scheme = self.isSecure() and 'https' or 'http'
			host = self._environ['HTTP_HOST'] # includes port
			return scheme + '://' + host + self.serverPath()

	def serverURLDir(self):
		"""Return the directory of the URL in full internet form.

		Same as serverURL, but removes the actual page.

		"""
		fullurl = self.serverURL()
		if fullurl and not fullurl.endswith('/'):
			fullurl = fullurl[:fullurl.rfind('/') + 1]
		return fullurl

	def serverPath(self):
		"""Return the webserver URL path of this request.

		This is the URL that was actually received by the webserver
		before any rewriting took place.

		Same as serverURL, but without scheme and host.

		"""
		if self._environ.has_key('SCRIPT_URL'):
			return self._environ['SCRIPT_URL']
		else:
			return self._servletPath + self._pathInfo

	def serverPathDir(self):
		"""Return the directory of the webserver URL path.

		Same as serverPath, but removes the actual page.

		"""
		fullurl = self.serverPath()
		if fullurl and not fullurl.endswith('/'):
			fullurl = fullurl[:fullurl.rfind('/') + 1]
		return fullurl

	def siteRoot(self):
		"""Return the relative URL path of the home location.

		This includes all URL path components necessary to get back home
		from the current location.

		Examples:
			''
			'../'
			'../../'

		You can use this as a prefix to a URL that you know is based off
		the home location. Any time you are in a servlet that may have been
		forwarded to from another servlet at a different level, you should
		prefix your URL's with this. That is, if servlet "Foo/Bar" forwards
		to "Qux", then the qux servlet should use siteRoot() to construct all
		links to avoid broken links. This works properly because this method
		computes the path based on the _original_ servlet, not the location
		of the servlet that you have forwarded to.

		"""
		url = self.originalURLPath()
		if url.startswith('/'):
			url = url[1:]
		contextName = self.contextName() + '/'
		if url.startswith(contextName):
			url = url[len(contextName):]
		numStepsBack = len(url.split('/')) - 1
		return '../' * numStepsBack

	def siteRootFromCurrentServlet(self):
		"""Return relative URL path to home seen from the current servlet.

		This includes all URL path components necessary to get back home
		from the current servlet (not from the original request).

		Similar to siteRoot() but instead, it returns the site root
		relative to the _current_ servlet, not the _original_ servlet.

		"""
		url = self.urlPath()
		if url.startswith('/'):
			url = url[1:]
		contextName = self.contextName() + '/'
		if url.startswith(contextName):
			url = url[len(contextName):]
		numStepsBackward = len(url.split('/')) - 1
		return '../' * numStepsBackward

	def servletPathFromSiteRoot(self):
		"""Return the "servlet path" of this servlet relative to the siteRoot.

		In other words, everything after the name of the context (if present).
		If you append this to the result of self.siteRoot() you get back to
		the current servlet. This is useful for saving the path to the current
		servlet in a database, for example.

		"""
		urlPath = self.urlPath()
		if urlPath.startswith('/'):
			urlPath = urlPath[1:]
		parts = urlPath.split('/')
		newParts = []
		for part in parts:
			if part == '..' and newParts:
				newParts.pop()
			elif part != '.':
				newParts.append(part)
		if newParts[:1] == [self.contextName()]:
			newParts[:1] = []
		return '/'.join(newParts)


	## Special ##

	def adapterName(self):
		"""Return the name of the adapter as it appears in the URL.

		Example: '/WK' or '/WebKit.cgi'
		Does not reflect redirection by the webserver.
		Equivalent to the CGI variable SCRIPT_NAME.

		"""
		return self._environ.get('SCRIPT_NAME', '')

	def adapterFileName(self):
		"""Return the filesystem path of the adapter.

		Equivalent to the CGI variable SCRIPT_FILENAME.

		"""
		return self._environ.get('SCRIPT_FILENAME', '')

	def environ(self):
		"""Get the environment for the request."""
		return self._environ

	def push(self, servlet, url=None):
		"""Push servlet and URL path on a stack, setting a new URL."""
		self._stack.append((servlet, self.urlPath(), self._contextName,
			self._serverSidePath, self._serverSideContextPath,
			self._serverRootPath, self._extraURLPath))
		if url is not None:
			self.setURLPath(url)

	def pop(self):
		"""Pop URL path and servlet from the stack, returning the servlet."""
		if self._stack:
			(servlet, url, self._contextName,
				self._serverSidePath, self._serverSideContextPath,
				self._serverRootPath, self._extraURLPath) = self._stack.pop()
			if url is not None:
				self.setURLPath(url)
			return servlet

	def servlet(self):
		"""Get current servlet for this request."""
		return self._transaction.servlet()

	def originalServlet(self):
		"""Get original servlet before any forwarding."""
		if self._stack:
			return self._stack[0][0]
		else:
			self.servlet()

	def previousServlet(self):
		"""Get the servlet that passed this request to us, if any."""
		if self._stack:
			return self._stack[-1][0]

	parent = previousServlet # kept old name as synonym

	def previousServlets(self):
		"""Get the list of all previous servlets."""
		return [s[0] for s in self._stack]

	parents = previousServlets # kept old name as synonym

	def originalURLPath(self):
		"""Get URL path of the original servlet before any forwarding."""
		if self._stack:
			return self._stack[0][1]
		else:
			return self.urlPath()

	def previousURLPath(self):
		"""Get the previous URL path, if any."""
		if self._stack:
			return self._stack[-1][1]

	def previousURLPaths(self):
		"""Get the list of all previous URL paths."""
		return [s[1] for s in self._stack]

	def originalURI(self):
		"""Get URI of the original servlet before any forwarding."""
		if self._stack:
			return self._servletPath + self._stack[0][1]
		else:
			return self.uri()

	def previousURI(self):
		"""Get the previous URI, if any."""
		if self._stack:
			return self._servletPath + self._stack[-1][1]

	def previousURIs(self):
		"""Get the list of all previous URIs."""
		return [self._servletPath + s[1] for s in self._stack]

	def originalContextName(self):
		"""Return the name of the original context before any forwarding."""
		if self._stack:
			return self._stack[0][2]
		else:
			return self._contextName

	def previousContextName(self):
		"""Get the previous context name, if any."""
		if self._stack:
			return self._stack[-1][2]

	def previousContextNames(self):
		"""Get the list of all previous context names."""
		return [s[2] for s in self._stack]

	def rawInput(self, rewind=False):
		"""Get the raw input from the request.

		This gives you a file-like object for the data that was sent with
		the request (e.g., the body of a POST request, or the document
		uploaded in a PUT request).

		The file might not be rewound to the beginning if there was valid,
		form-encoded POST data. Pass rewind=True if you want to be sure
		you get the entire body of the request.

		"""
		fs = self.fieldStorage()
		if fs is None:
			return None
		if rewind and fs.file:
			fs.file.seek(0)
		return fs.file

	def time(self):
		"""Return the time that the request was received."""
		return self._time

	def requestID(self):
		"""Return the request ID.

		The request ID is a serial number unique to this request
		(at least unique for one run of the AppServer).

		"""
		return self._requestID


	## Information ##

	def servletPath(self):
		"""Return the base URL for the servlets, sans host.

		This is useful in cases when you are constructing URLs.
		See Testing/Main.py for an example use.

		Roughly equivalent to the CGI variable SCRIPT_NAME,
		but reflects redirection by the webserver.

		"""
		return self._servletPath

	def contextPath(self):
		"""Return the portion of the URI that is the context of the request."""
		return self._serverSideContextPath

	def pathInfo(self):
		"""Return any extra path information as sent by the client.

		This is anything after the servlet name but before the query string.
		Equivalent to the CGI variable PATH_INFO.

		"""
		return self._pathInfo

	def pathTranslated(self):
		"""Return extra path information translated as file system path.

		This is the same as pathInfo() but translated to the file system.
		Equivalent to the CGI variable PATH_TRANSLATED.

		"""
		return self._environ.get('PATH_TRANSLATED', '')

	def queryString(self):
		"""Return the query string portion of the URL for this request.

		Equivalent to the CGI variable QUERY_STRING.

		"""
		return self._queryString

	def uri(self):
		"""Return the URI for this request (everything after the host name).

		This is the URL that was actually received by the webserver
		before any rewriting took place, including the query string.
		Equivalent to the CGI variable REQUEST_URI.

		"""
		return self._uri

	def method(self):
		"""Return the HTTP request method (in all uppercase).

		Typically from the set GET, POST, PUT, DELETE, OPTIONS and TRACE.

		"""
		return self._environ['REQUEST_METHOD'].upper()

	def sessionId(self):
		"""Return a string with the session ID specified by the client.

		Returns None if there is no session ID.

		"""
		trans = self._transaction
		app = trans.application()
		sid = self.value(app.sessionName(trans), None)
		if app.setting('Debug')['Sessions']:
			print '>> sessionId: returning sid =', sid
		return sid

	def setSessionId(self, sessionID, force=False):
		"""Set the session ID.

		This needs to be called _before_ attempting to use the session.
		This would be useful if the session ID is being passed in through
		unusual means, for example via a field in an XML-RPC request.

		Pass in force=True if you want to force this session ID to be used
		even if the session doesn't exist. This would be useful in unusual
		circumstances where the client is responsible for creating the unique
		session ID rather than the server.
		Be sure to use only legal filename characters in the session ID --
		0-9, a-z, A-Z, _, -, and . are OK but everything else will be rejected,
		as will identifiers longer than 80 characters.
		(Without passing in force=True, a random session ID will be generated
		if that session ID isn't already present in the session store.)

		"""
		# Modify the request so that it looks like a hashed version of the
		# given session ID was passed in
		trans = self._transaction
		app = trans.application()
		self.setField(app.sessionName(trans), sessionID)
		if force:
			# Force this session ID to exist, so that a random session ID
			# won't be created in case it's a new session.
			app.createSessionWithID(trans, sessionID)


	## Inspection ##

	def info(self):
		"""Return request info.

		Return a list of tuples where each tuple has a key/label (a string)
		and a value (any kind of object).

		Values are typically atomic values such as numbers and strings or
		another list of tuples in the same fashion. This is for debugging only.

		"""
		# @@ 2000-04-10 ce: implement and invoke super if appropriate
		# @@ 2002-06-08 ib: should this also return the unparsed body
		# of the request?
		info = [
			('time', self._time),
			('environ', self._environ),
			('input', self._input),
			('fields', self._fields),
			('cookies', self._cookies)
		]

		# Information methods
		for method in _infoMethods:
			try:
				info.append((method.__name__, method(self)))
			except Exception:
				info.append((method.__name__, None))

		return info

	def htmlInfo(self):
		"""Return a single HTML string that represents info().

		Useful for inspecting objects via web browsers.

		"""
		return htmlInfo(self.info())

	_exceptionReportAttrNames = Request._exceptionReportAttrNames + (
		'uri adapterName servletPath serverSidePath'
		' pathInfo pathTranslated queryString method'
		' sessionId previousURLPaths fields cookies environ'.split())


	## Deprecated ##

	def serverSideDir(self):
		"""deprecated: HTTPRequest.serverSideDir() on 01/24/01 in 0.5.

		Use serverSidePath() instead.@

		Return the servlet directory (as given through __init__()'s path).

		"""
		self.deprecated(self.serverSideDir)
		if not hasattr(self, '_serverSideDir'):
			self._serverSideDir = os.path.dirname(self.serverSidePath())
		return self._serverSideDir

	def relativePath(self, joinPath):
		"""deprecated: HTTPRequest.relativePath() on 01/24/01 in 0.5.

		Use serverSidePath() instead.@

		Return a new path with the servlet's path appended by 'joinPath'.
		If 'joinPath' is an absolute path, then only 'joinPath' is returned.

		"""
		self.deprecated(self.relativePath)
		return os.path.join(self.serverSideDir(), joinPath)

	def servletFilePath(self):
		"""deprecated: HTTPRequest.servletFilePath() on 04/12/07 in 0.9.3.

		Use adapterFileName() instead.@

		Equivalent to the CGI variable SCRIPT_FILENAME.

		"""
		self.deprecated(self.servletFilePath)
		return self.adapterFileName(file)


## Info Structure ##

_infoMethods = (
	HTTPRequest.adapterName,
	HTTPRequest.servletPath,
	HTTPRequest.contextPath,
	HTTPRequest.pathInfo,
	HTTPRequest.pathTranslated,
	HTTPRequest.queryString,
	HTTPRequest.uri,
	HTTPRequest.method,
	HTTPRequest.sessionId
)

def htmlInfo(info):
	"""Return a single HTML string that represents the info structure.

	Useful for inspecting objects via web browsers.

	"""
	res = ['<table border="1">\n']
	for pair in info:
		value = pair[1]
		if hasattr(value, 'items') and (type(value) is type({})
				or hasattr(value, '__getitem__')):
			value = htmlInfo(_infoForDict(value))
		res.append('<tr valign="top"><td>%s</td><td>%s&nbsp;</td></tr>\n'
			% (pair[0], value))
	res.append('</table>\n')
	return ''.join(res)

def _infoForDict(dict):
	"""Return an "info" structure for any dictionary-like object."""
	items = dict.items()
	items.sort(lambda a, b: cmp(a[0], b[0]))
	return items
