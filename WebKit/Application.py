#!/usr/bin/env python

from UserDict import UserDict
from types import FloatType, ClassType

from Common import *
from Object import Object
from ConfigurableForServerSidePath import ConfigurableForServerSidePath
from ExceptionHandler import ExceptionHandler
from HTTPRequest import HTTPRequest
from Transaction import Transaction
from Session import Session
import URLParser
import HTTPExceptions

debug = 0


class EndResponse(Exception):
	"""End response exception.

	Used to prematurely break out of the awake()/respond()/sleep()
	cycle without reporting a traceback. During servlet processing,
	if this exception is caught during awake() or respond() then sleep()
	is called and the response is sent. If caught during sleep(),
	processing ends and the response is sent.

	"""
	pass


class Application(ConfigurableForServerSidePath, Object):
	"""The Application singleton.

	`Application` and `AppServer` work together to setup up and dispatch
	requests. The distinction between the two is largely historical, but
	AppServer communicates directly with Adapters (or speaks protocols like
	HTTP), and Application receives the (slightly) processed input from
	AppServer and turns it into `Transaction`, `HTTPRequest`, `HTTPResponse`,
	and `Session`.

	Application is a singleton, which belongs to the AppServer. You can get
	access through the Transaction object (``transaction.application()``),
	or you can do::

	    from AppServer import globalAppServer
	    application = globalAppServer.application()

	Settings for Application are taken from ``Configs/Application.config``,
	and it is used for many global settings, even if they aren't closely tied
	to the Application object itself.

	"""


	## Init ##

	def __init__(self, server):
		"""Called only by `AppServer`, sets up the Application."""

		self._server = server
		self._serverSidePath = server.serverSidePath()

		self._imp = server._imp # the import manager

		ConfigurableForServerSidePath.__init__(self)
		Object.__init__(self)

		if self.setting('PrintConfigAtStartUp'):
			self.printConfig()

		self.initVersions()

		self._shutDownHandlers = []

		# Initialize TaskManager:
		if self._server.isPersistent():
			from TaskKit.Scheduler import Scheduler
			self._taskManager = Scheduler(1)
			self._taskManager.start()
		else:
			self._taskManager = None

		# Define this before initializing URLParser, so that contexts have a
		# chance to override this. Also be sure to define it before loading the
		# sessions, in case the loading of the sessions causes an exception.
		self._exceptionHandlerClass = ExceptionHandler

		self._session_prefix = self.setting('SessionPrefix', None) or ''
		if self._session_prefix:
			if self._session_prefix == 'hostname':
				from MiscUtils.Funcs import hostName
				self._session_prefix = hostName()
			self._session_prefix += '-'
		self._session_timeout = self.setting('SessionTimeout')*60
		self._session_name = self.setting('SessionName', None) or '_SID_'

		# For session store:
		session_store = 'Session%sStore' % self.setting('SessionStore')
		exec 'from %s import %s' % (session_store, session_store)
		klass = locals()[session_store]
		assert isinstance(klass, ClassType) or issubclass(klass, Object)
		self._sessions = klass(self)

		print 'Current directory:', os.getcwd()

		URLParser.initApp(self)
		self._rootURLParser = URLParser.ContextParser(self)

		self.running = 1

		self.startSessionSweeper()

		try: # try to get a 404 error page from the working dir
			self._404Page = open(os.path.join(self._serverSidePath,
				"404Text.txt")).read()
		except: # if not found in the working dir,
			try: # then try the directory this file is located in
				self._404Page = open(os.path.join(
					os.path.dirname(os.path.abspath(__file__)),
					"404Text.txt")).read()
			except: # otherwise fall back to standard exception
				self._404Page = None

	def initVersions(self):
		"""Get and store versions.

		Initialize attributes that store the Webware and WebKit versions as
		both tuples and strings. These are stored in the Properties.py files.

		"""
		from MiscUtils.PropertiesObject import PropertiesObject
		props = PropertiesObject(os.path.join(self.webwarePath(),
			'Properties.py'))
		self._webwareVersion = props['version']
		self._webwareVersionString = props['versionString']
		props = PropertiesObject(os.path.join(self.webKitPath(),
			'Properties.py'))
		self._webKitVersion = props['version']
		self._webKitVersionString = props['versionString']

	def taskManager(self):
		"""Accessor: `TaskKit.Scheduler` instance."""
		return self._taskManager

	def startSessionSweeper(self):
		"""Start session sweeper.

		Starts the session sweeper, `WebKit.Tasks.SessionTask`, which deletes
		session objects (and disk copies of those objects) that have expired.

		"""
		if self._session_timeout:
			tm = self.taskManager()
			if tm:
				from Tasks import SessionTask
				import time
				task = SessionTask.SessionTask(self._sessions)
				sweepinterval = self._session_timeout/10
				tm.addPeriodicAction(time.time() + sweepinterval,
					sweepinterval, task, "SessionSweeper")
				print "Session sweeper has started."

	def shutDown(self):
		"""Shut down the application.

		Called by AppServer when it is shuting down.  The `__del__` function
		of Application probably won't be called due to circular references.

		"""
		print "Application is shutting down..."
		self.running = 0
		self._sessions.storeAllSessions()
		if self._server.isPersistent():
			self.taskManager().stop()
		del self._sessions
		del self._server

		# Call all registered shutdown handlers
		for shutDownHandler in self._shutDownHandlers:
			shutDownHandler()
		del self._shutDownHandlers

		print "Application has been succesfully shutdown."

	def addShutDownHandler(self, func):
		"""Add a shutdown handler.

		Functions added through `addShutDownHandler` will be called when
		the AppServer is shutting down. You can use this hook to close
		database connections, clean up resources, save data to disk, etc.

		"""
		self._shutDownHandlers.append(func)


	## Config ##

	def defaultConfig(self):
		"""The default Application.config."""
		return {
			'PrintConfigAtStartUp': 1,
			'LogActivity': 1,
			'ActivityLogFilename': 'Logs/Activity.csv',
			'ActivityLogColumns': [
				'request.remoteAddress', 'request.method',
				'request.uri', 'response.size',
				'servlet.name', 'request.timeStamp',
				'transaction.duration',
				'transaction.errorOccurred'
				],
			'SessionStore': 'Dynamic',
			'SessionTimeout': 60,
			'IgnoreInvalidSession': 1,
			'UseAutomaticPathSessions': 0,
			'ShowDebugInfoOnErrors': 1,
			'IncludeFancyTraceback': 0,
			'FancyTracebackContext': 5,
			'UserErrorMessage': 'The site is having technical difficulties'
				' with this page. An error has been logged, and the problem'
				' will be fixed as soon as possible. Sorry!',
			'LogErrors': 1,
			'ErrorLogFilename': 'Logs/Errors.csv',
			'SaveErrorMessages': 1,
			'ErrorMessagesDir': 'ErrorMsgs',
			'EmailErrors': 0,
			'ErrorEmailServer': 'localhost',
			'ErrorEmailHeaders': {
				'From': 'webware@mydomain',
				'To': ['webware@mydomain'],
				'Reply-to': 'webware@mydomain',
				'content-type': 'text/html',
				'Subject': 'Error'
				},
			'MaxValueLengthInExceptionReport': 500,
			'RPCExceptionReturn': 'traceback',
			'ReportRPCExceptionsInWebKit': 1,
			'Contexts': {
				'default': 'Examples',
				'Admin': 'Admin',
				'Examples': 'Examples',
				'Testing': 'Testing',
				'Docs': 'Docs',
				},
			'Debug': {
				'Sessions': 0,
				},
			'EnterDebuggerOnException': 0,
			'DirectoryFile': ['index', 'Index', 'main', 'Main'],
			'UseCascadingExtensions': 1,
			'ExtensionCascadeOrder': ['.py','.psp','.kid','.html'],
			'ExtraPathInfo': 1,
			'ExtensionsToIgnore': [
				'.pyc', '.pyo', '.tmpl', '.bak', '.py_bak',
				'.py~', '.psp~', '.kid~', '.html~', '.tmpl~'
				],
			'ExtensionsToServe': [],
			'FilesToHide': [
				'.*', '*~', '*.bak', '*.py_bak', '*.tmpl',
				'*.pyc', '*.pyo', '__init__.*', '*.config'
				],
			'FilesToServe': [],
			'UnknownFileTypes': {
				'ReuseServlets': 1,
				'Technique': 'serveContent', # serveContent or redirectSansAdapter
				'CacheContent': 0,
				'MaxCacheContentSize': 128*1024,
				'ReadBufferSize': 32*1024
				},
		}

	def configFilename(self):
		return self.serverSidePath('Configs/Application.config')

	def configReplacementValues(self):
		return self._server.configReplacementValues()


	## Versions ##

	def version(self):
		"""Return the version of the application.

		This implementation returns '0.1'. Subclasses should
		override to return the correct version number.

		"""
		# @@ 2000-05-01 ce: Maybe this could be a setting 'AppVersion'
		# @@ 2003-03 ib: Does anyone care about this?  What's this
		# version even supposed to mean?
		return '0.1'

	def webwareVersion(self):
		"""Return the Webware version as a tuple."""
		return self._webwareVersion

	def webwareVersionString(self):
		"""Return the Webware version as a printable string."""
		return self._webwareVersionString

	def webKitVersion(self):
		""" Return the WebKit version as a tuple."""
		# @@ 2003-03 ib: This is synced with Webware now, should be removed
		# because redundant (and not that useful anyway)
		return self._webKitVersion

	def webKitVersionString(self):
		"""Return the WebKit version as a printable string."""
		return self._webKitVersionString


	## Sessions ##

	def session(self, sessionId, default=NoDefault):
		"""The session object for `sessionId`.

		Raises ``KeyError`` if session not found and no default is given.

		"""
		if default is NoDefault:
			return self._sessions[sessionId]
		else:
			return self._sessions.get(sessionId, default)

	def hasSession(self, sessionId):
		"""Check whether session `sessionId` exists."""
		return self._sessions.has_key(sessionId)

	def sessions(self):
		"""A dictionary of all the session objects."""
		return self._sessions

	def createSessionForTransaction(self, transaction):
		"""Get the session object for the transaction.

		If the session already exists, returns that, otherwise creates
		a new session.

		Finding the session ID is done in `Transaction.sessionId`.

		"""
		debug = self.setting('Debug').get('Sessions')
		if debug:
			prefix = '>> [session] createSessionForTransaction:'
		sessId = transaction.request().sessionId()
		if debug:
			print prefix, 'sessId =', sessId
		if sessId:
			try:
				session = self.session(sessId)
				if debug:
					print prefix, 'retrieved session =', session
			except KeyError:
				transaction.request().setSessionExpired(1)
				if not self.setting('IgnoreInvalidSession'):
					raise HTTPExceptions.HTTPSessionExpired
				sessId = None
		if not sessId:
			session = Session(transaction)
			self._sessions[session.identifier()] = session
			if debug:
				print prefix, 'created session =', session
		transaction.setSession(session)
		return session

	def createSessionWithID(self, transaction, sessionID):
		# Create a session object with our session ID
		sess = Session(transaction, sessionID)
		# Replace the session if it didn't already exist,
		# otherwise we just throw it away.  setdefault is an atomic
		# operation so this guarantees that 2 different
		# copies of the session with the same ID never get placed into
		# the session store, even if multiple threads are calling
		# this method simultaneously.
		transaction.application()._sessions.setdefault(sessionID, sess)


	## Misc Access ##

	def server(self):
		"""Acessor: the AppServer"""
		return self._server

	def serverSidePath(self, path=None):
		"""Get the serve-side-path.

		Returns the absolute server-side path of the WebKit application.
		If the optional path is passed in, then it is joined with the
		server side directory to form a path relative to the app server.

		"""
		if path:
			return os.path.normpath(
				os.path.join(self._serverSidePath, path))
		else:
			return self._serverSidePath

	def webwarePath(self):
		"""The path of the ``Webware/`` directory."""
		return self._server.webwarePath()

	def webKitPath(self):
		"""The Path of the ``Webware/WebKit/`` directory."""
		return self._server.webKitPath()

	def name(self):
		"""The name by which this was started. Usually ``AppServer``."""
		# @@ 2003-03 ib: unconfirmed
		return sys.argv[0]


	## Activity Log ##

	def writeActivityLog(self, transaction):
		"""Write an entry to the activity log.

		Writes an entry to the script log file. Uses settings
		``ActivityLogFilename`` and ``ActivityLogColumns``.

		"""
		filename = self.serverSidePath(
			self.setting('ActivityLogFilename'))
		if os.path.exists(filename):
			f = open(filename, 'a')
		else:
			f = open(filename, 'w')
			f.write(','.join(self.setting('ActivityLogColumns')) + '\n')
		values = []
		# We use UserDict on the next line because we know it inherits
		# NamedValueAccess and reponds to valueForName()
		objects = UserDict({
			'application': self,
			'transaction': transaction,
			'request': transaction.request(),
			'response': transaction.response(),
			'servlet': transaction.servlet(),
			'session': transaction._session, # don't cause creation of session
		})
		for column in self.setting('ActivityLogColumns'):
			try:
				value = objects.valueForName(column)
			except:
				value = '(unknown)'
			if type(value) is FloatType:
				# probably need more flexibility in the future
				value = '%0.2f' % value
			else:
				value = str(value)
			values.append(value)
		f.write(','.join(values) + '\n')
		f.close()
		for i in objects.keys():
			objects[i] = None


	## Request Dispatching ##

	# These are the entry points from `AppServer`, which take a raw request,
	# turn it into a transaction, run the transaction, and clean up.

	def dispatchRawRequest(self, requestDict, strmOut):
		"""Dispatch a raw request.

		Dispatch a request as passed from the Adapter through the AppServer.
		This method creates the request, response, and transaction object,
		then runs (via `runTransaction`) the transaction. It also catches any
		exceptions, which are then passed on to `handleExceptionInTransaction`.

		"""
		trans = None
		try:
			request = self.createRequestForDict(requestDict)
			trans = Transaction(application=self, request=request)
			request.setTransaction(trans)
			response = request.responseClass()(trans, strmOut)
			trans.setResponse(response)
			self.runTransaction(trans)
			trans.response().deliver()
		except:
			if trans:
				trans.setErrorOccurred(1)
			if self.setting('EnterDebuggerOnException') and sys.stdin.isatty():
				import pdb
				pdb.post_mortem(sys.exc_info()[2])
			self.handleExceptionInTransaction(sys.exc_info(), trans)
			trans.response().deliver()

		if self.setting('LogActivity'):
			self.writeActivityLog(trans)
		request.clearTransaction()
		response.clearTransaction()
		return trans

	def createRequestForDict(self, requestDict):
		"""Create request object for a given dictionary.

		Create a request object (subclass of `Request`) given the raw
		dictionary as passed by the adapter.

		The class of the request may be based on the contents of the
		dictionary (though only `HTTPRequest` is currently created),
		and the request will later determine the class of the response.

		Called by `dispatchRawRequest`.

		"""
		format = requestDict['format']
		# Maybe an EmailAdapter would make a request with a
		# format of Email, and an EmailRequest would be
		# generated.  For now just CGI/HTTPRequest.
		assert format == 'CGI'
		return HTTPRequest(requestDict)

	def runTransaction(self, trans):
		"""Run transation.

		Executes the transaction, handling HTTPException errors.
		Finds the servlet (using the root parser, probably
		`URLParser.ContextParser`, to find the servlet for the
		transaction, then calling `runTransactionViaServlet`.

		Called by `dispatchRawRequest`.

		"""
		# @@ gtalvola: I'm guessing this is not the ideal place
		# @@ to put this code. But, it works.
		if self.setting('UseAutomaticPathSessions'):
			request = trans.request()
			request_has_cookie_session = request.hasCookieSession()
			request_has_path_session = request.hasPathSession()
			if request_has_cookie_session and request_has_path_session:
				self.handleUnnecessaryPathSession(trans)
				return
			elif not request_has_cookie_session and not request_has_path_session:
				self.handleMissingPathSession(trans)
				return
		servlet = None
		try:
			servlet = self._rootURLParser.findServletForTransaction(trans)
			self.runTransactionViaServlet(servlet, trans)
		except HTTPExceptions.HTTPException, err:
			err.setTransaction(trans)
			trans.response().displayError(err)
		except EndResponse:
			pass
		if servlet:
			# Return the servlet to its pool
			self.returnServlet(servlet, trans)

	def runTransactionViaServlet(self, servlet, trans):
		"""Execute the transaction using the servlet.

		This is the `awake`/`respond`/`sleep` sequence of calls, or if
		the servlet supports it, a single `runTransaction` call (which is
		presumed to make the awake/respond/sleep calls on its own). Using
		`runTransaction` allows the servlet to override the basic call
		sequence, or catch errors from that sequence.

		Called by `runTransaction`.

		"""
		trans.setServlet(servlet)
		if hasattr(servlet, 'runTransaction'):
			servlet.runTransaction(trans)
		else:
			# For backward compatibility (Servlet.runTransaction implements
			# this same sequence of calls, but by keeping it in the servlet
			# it's easier for the servlet to catch exceptions).
			try:
				trans.awake()
				trans.respond()
			finally:
				trans.sleep()

	def forward(self, trans, url):
		"""Forward the request to a different (internal) URL.

		The transaction's URL is changed to point to the new servlet,
		and the transaction is simply run again.

		Output is _not_ accumulated, so if the original servlet had any output,
		the new output will _replace_ the old output.

		You can change the request in place to control the servlet you are
		forwarding to -- using methods like `HTTPRequest.setField`.

		@@ 2003-03 ib: how does the forwarded servlet knows that it's not
		the original servlet?

		"""
		# Reset the response to a "blank slate"
		trans.response().reset()

		# Include the other servlet
		self.includeURL(trans, url)

		# Raise an exception to end processing of this request
		raise EndResponse

	def callMethodOfServlet(self, trans, url, method, *args, **kw):
		"""Call method of another servlet.

		Call a method of the servlet referred to by the URL. Calls sleep()
		and awake() before and after the method call. Or, if the servlet
		defines it, then `runMethodForTransaction` is used (analogous to the
		use of `runTransaction` in `forward`).

		The entire process is similar to `forward`, except that instead of
		`respond`, `method` is called (`method` should be a string, ``*args``
		and ``**kw`` are passed as arguments to that method).

		"""
		urlPath = self.resolveInternalRelativePath(trans, url)
		req = trans.request()
		currentPath = req.urlPath()
		currentServlet = trans._servlet
		currentServerSidePath = req._serverSidePath
		currentServerSideContextPath = req._serverSideContextPath
		currentContextName = req._contextName
		currentServerRootPath = req._serverRootPath
		currentExtraURLPath = req._extraURLPath
		req.setURLPath(urlPath)
		req.addParent(currentServlet)

		servlet = self._rootURLParser.findServletForTransaction(trans)
		trans._servlet = servlet
		if hasattr(servlet, 'runMethodForTransaction'):
			result = servlet.runMethodForTransaction(trans, method, *args, **kw)
		else:
			servlet.awake(trans)
			result = getattr(servlet, method)(*args, **kw)
			servlet.sleep(trans)

		# Put things back
		req.setURLPath(currentPath)
		req._serverSidePath = currentServerSidePath
		req._serverSideContextPath = currentServerSideContextPath
		req._contextName = currentContextName
		req._serverRootPath = currentServerRootPath
		req._extraURLPath = currentExtraURLPath
		req.popParent()
		trans._servlet = currentServlet

		return result

	def includeURL(self, trans, url):
		"""Include another servlet.

		Include the servlet given by the URL. Like `forward`,
		except control is ultimately returned to the servlet.

		"""
		urlPath = self.resolveInternalRelativePath(trans, url)
		req = trans.request()
		currentPath = req.urlPath()
		currentServlet = trans._servlet
		currentServerSidePath = req._serverSidePath
		currentServerSideContextPath = req._serverSideContextPath
		currentContextName = req._contextName
		req.setURLPath(urlPath)
		req.addParent(currentServlet)

		# Run the included servlet.
		# (2006-07-05 cz: Do not use try/finally here, because exception
		# handling should happen in the context of the included servlet.)
		servlet = self._rootURLParser.findServletForTransaction(trans)
		trans._servlet = servlet
		# We will interpret an EndResponse in an included page to mean that
		# the current page may continue processing.
		try:
			servlet.runTransaction(trans)
		except EndResponse:
			pass
		self.returnServlet(servlet, trans)

		# Restore everything properly
		req.popParent()
		req.setURLPath(currentPath)
		req._serverSidePath = currentServerSidePath
		req._serverSideContextPath = currentServerSideContextPath
		req._contextName = currentContextName
		trans._servlet = currentServlet

	def resolveInternalRelativePath(self, trans, url):
		"""Return the absolute internal path.

		Given a URL, return the absolute internal URL.
		URLs are assumed relative to the current URL.
		Absolute paths are returned unchanged.

		"""
		if not url.startswith('/'):
			origDir = trans.request().urlPath()
			if not origDir.endswith('/'):
				origDir = os.path.dirname(origDir)
				if not origDir.endswith('/'):
					origDir += '/'
			url = origDir + url
		# Deal with . and .. in the path:
		parts = []
		for part in url.split('/'):
			if parts and part == '..':
				parts.pop()
			elif part != '.':
				parts.append(part)
		return '/'.join(parts)

	def returnServlet(self, servlet, trans):
		servlet.close(trans)

	def handleException(self):
		"""Handle exceptions.

		This should only be used in cases where there is no transaction object,
		for example if an exception occurs when attempting to save a session
		to disk.

		"""
		self._exceptionHandlerClass(self, None, sys.exc_info())

	def handleExceptionInTransaction(self, excInfo, transaction):
		"""Handle exception with info.

		Handles exception `excInfo` (as returned by ``sys.exc_info()``)
		that was generated by `transaction`. It may display the exception
		report, email the report, etc., handled by
		`ExceptionHandler.ExceptionHandler`.

		"""
		req = transaction.request()
		editlink = req.adapterName() + "/Admin/EditFile"
		self._exceptionHandlerClass(self, transaction,
			excInfo, {"editlink": editlink})

	def rootURLParser(self):
		"""Accessor: the Rool URL parser.

		URL parsing (as defined	by subclasses of `URLParser.URLParser`)
		starts here. Other parsers are called in turn by this parser.

		"""
		return self._rootURLParser

	def hasContext(self, name):
		"""Checks whether context `name` exist."""
		return self._rootURLParser._contexts.has_key(name)

	def addContext(self, name, path):
		"""Add a context by named `name`, rooted at `path`.

		This gets imported as a package, and the last directory
		of `path` does not have to match the context name.
		(The package will be named `name`, regardless of `path`).

		Delegated to `URLParser.ContextParser`.

		"""
		self._rootURLParser.addContext(name, path)

	def addServletFactory(self, factory):
		"""Add a ServletFactory.

		Delegated to the `URLParser.ServletFactoryManager` singleton.

		"""
		URLParser.ServletFactoryManager.addServletFactory(factory)

	def contexts(self):
		"""Return a dictionary of context-name: context-path."""
		return self._rootURLParser._contexts

	def writeExceptionReport(self, handler):
		# @@ 2003-02 ib: does anyone care?
		pass

	def handleMissingPathSession(self, transaction):
		"""Redirect requests without session info in the path.

		if UseAutomaticPathSessions is enabled in Application.config
		we redirect the browser to a url with SID in path
		http://gandalf/a/_SID_=2001080221301877755/Examples/
		_SID_ is extracted and removed from path in HTTPRequest.py

		This is for convinient building of webapps that must not
		depend on cookie support.

		"""
		newSid = transaction.session().identifier()
		request = transaction.request()
		url = '%s/%s=%s/%s%s%s' % (request.adapterName(), self._session_name,
			newSid, request.pathInfo(), request.extraURLPath() or '',
			request.queryString() and '?' + request.queryString() or '')
		if self.setting('Debug')['Sessions']:
			print '>> [sessions] handling UseAutomaticPathSessions,' \
				' redirecting to', url
		transaction.response().sendRedirect(url)

	def handleUnnecessaryPathSession(self, transaction):
		"""Redirect request with unnecessary session info in the path.

		This is called if it has been determined that the request has a path
		session, but also cookies. In that case we redirect	to eliminate the
		unnecessary path session.

		"""
		request = transaction.request()
		url = '%s/%s%s%s' % (request.adapterName(),
			request.pathInfo(), request.extraURLPath() or '',
			request.queryString() and '?' + request.queryString() or '')
		if self.setting('Debug')['Sessions']:
			print ">> [sessions] handling unnecessary path session,' \
				' redirecting to", url
		transaction.response().sendRedirect(url)


## Main ##

def main(requestDict):
	"""Return a raw reponse.

	This method is mostly used by OneShotAdapter.py.

	"""
	from WebUtils.HTMLForException import HTMLForException
	try:
		assert type(requestDict) is type({})
		app = Application(useSessionSweeper=0)
		return app.runRawRequest(requestDict).response().rawResponse()
	except:
		return {
			'headers': [('Content-type', 'text/html')],
			'contents': '<html><body>%s</html></body>' % HTMLForException()
		}


"""
You can run Application as a main script, in which case it expects a
single argument which is a file containing a dictionary representing
a request. This technique isn't very popular as Application itself
could raise exceptions that aren't caught. See `CGIAdapter` and
`AppServer` for a better example of how things should be done.

Largely historical.
"""

if __name__ == '__main__':
	if len(sys.argv) != 2:
		sys.stderr.write('WebKit: Application: Expecting one filename argument.\n')
	requestDict = eval(open(sys.argv[1]).read())
	main(requestDict)
