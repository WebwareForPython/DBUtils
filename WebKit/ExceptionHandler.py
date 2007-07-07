from types import DictType, ListType
import traceback, random, MimeWriter, smtplib

from Common import *
from MiscUtils.Funcs import dateForEmail
from WebUtils.HTMLForException import HTMLForException
from WebUtils.Funcs import htmlForDict, htmlEncode

try: # linecache update workaround for Python < 2.4
	traceback.format_exc # check version
except AttributeError: # Python < 2.4
	from linecache import checkcache
else: # Python >= 2.4
	# the linecache module updates the cache automatically
	def checkcache(): pass


class Singleton:
	pass


class ExceptionHandler(Object):
	"""Exception handling.

	ExceptionHandler is a utility class for Application that is created
	to handle a particular exception. The object is a one-shot deal.
	After handling an exception, it should be removed.

	At some point, the exception handler sends
	`writeExceptionReport` to the transaction (if present), which
	in turn sends it to the other transactional objects
	(application, request, response, etc.)  The handler is the
	single argument for this message.

	Classes may find it useful to do things like this::

		exceptionReportAttrs = 'foo bar baz'.split()
		def writeExceptionReport(self, handler):
			handler.writeTitle(self.__class__.__name__)
			handler.writeAttrs(self, self.exceptionReportAttrs)

	The handler write methods that may be useful are:

        * write
        * writeTitle
        * writeDict
        * writeTable
        * writeAttrs

	Derived classes must not assume that the error occured in a
	transaction.  self._tra may be None for exceptions outside
	of transactions.

	**HOW TO CREATE A CUSTOM EXCEPTION HANDLER**

	In the ``__init__.py`` of your context::

		from WebKit.ExceptionHandler import ExceptionHandler as _ExceptionHandler

		class ExceptionHandler(_ExceptionHandler):

			_hideValuesForFields = _ExceptionHandler._hideValuesForFields + ['foo', 'bar']

			def work(self):
				_ExceptionHandler.work(self)
				# do whatever
				# override other methods if you like

		def contextInitialize(app, ctxPath):
			app._exceptionHandlerClass = ExceptionHandler

	You can also control the errors with settings in
	``Application.config``

	"""
	# keep these lower case to support case insensitivity:
	_hideValuesForFields = ['password', 'passwd', 'pwd',
		'creditcard', 'credit card', 'cc', 'pin', 'tan']
	if 0: # for testing
		_hideValuesForFields.extend(['application', 'uri',
			'http_accept', 'userid'])
	_hiddenString = '*** hidden ***'


	## Init ##

	def __init__(self, application, transaction, excInfo,
			formatOptions=None):
		"""Create an exception handler instance.

		ExceptionHandler instances are created anew for each exception.
		Instantiating ExceptionHandler completes the process --
		the caller need not	do anything else.

		"""
		Object.__init__(self)

		# Keep references to the objects
		self._app = application
		self._tra = transaction
		self._exc = excInfo
		if self._tra:
			self._req = self._tra.request()
			self._res = self._tra.response()
		else:
			self._req = self._res = None

		self._formatOptions = formatOptions

		# Make some repairs, if needed. We use the transaction
		# & response to get the error page back out

		# @@ 2000-05-09 ce: Maybe a fresh transaction and
		# response should always be made for that purpose

		# @@ 2003-01-10 sd: This requires a transaction which
		# we do not have.

		# Making remaining code safe for no transaction.
		#
		# if self._res is None:
		#      self._res = HTTPResponse()
		#      self._tra.setResponse(self._res)

		# Cache MaxValueLengthInExceptionReport for speed
		self._maxValueLength = self.setting('MaxValueLengthInExceptionReport')

		# exception occurance time. (overridden by response.endTime())
		self._time = time.time()

		# Get to work
		self.work()


	## Accessors ##

	def setting(self, name):
		"""Settings are inherited from Application."""
		return self._app.setting(name)

	def servletPathname(self):
		"""The full filesystem path for the servlet."""
		try:
			return self._tra.request().serverSidePath()
		except Exception:
			return None

	def basicServletName(self):
		"""The base name for the servlet (sans directory)."""
		name = self.servletPathname()
		if name is None:
			return 'unknown'
		else:
			return os.path.basename(name)


	## Exception Handling ##

	def work(self):
		"""Main error handling method.

		Invoked by `__init__` to do the main work. This calls
		`logExceptionToConsole`, then checks settings to see if it should
		call `saveErrorPage` (to save the error to disk) and `emailException`.

		It also sends gives a page from `privateErrorPage` or
		`publicErrorPage` (which one based on ``ShowDebugInfoOnErrors``).

		"""
		if self._res:
			self._res.recordEndTime()
			self._time = self._res.endTime()

		checkcache() # update the linecache

		self.logExceptionToConsole()

		# Write the error page out to the response if available:
		if self._res and (not self._res.isCommitted()
			or self._res.header('Content-type', None) == 'text/html'):
			if not self._res.isCommitted():
				self._res.reset()
				self._res.setStatus(500, "Servlet Error")
			if self.setting('ShowDebugInfoOnErrors') == 1:
				publicErrorPage = self.privateErrorPage()
			else:
				publicErrorPage = self.publicErrorPage()
			self._res.write(publicErrorPage)

			# Add a large block comment; this prevents IE from overriding the
			# page with its own generic error 500 page
			self._res.write('<!-- --------------------------------- -->\n' * 100)

		privateErrorPage = None
		if self.setting('SaveErrorMessages'):
			privateErrorPage = self.privateErrorPage()
			filename = self.saveErrorPage(privateErrorPage)
		else:
			filename = ''

		self.logExceptionToDisk(errorMsgFilename=filename)

		if self.setting('EmailErrors'):
			if privateErrorPage is None:
				privateErrorPage = self.privateErrorPage()
			try:
				self.emailException(privateErrorPage)
			except Exception, e:
				print "Could not send error email:", e

	def logExceptionToConsole(self, stderr=None):
		"""Log an exception.

		Logs the time, servlet name and traceback to the console
		(typically stderr). This usually results in the information
		appearing in console/terminal from which AppServer was launched.

		"""
		if stderr is None:
			stderr = sys.stderr
		stderr.write('[%s] [error] WebKit: Error while executing script %s\n'
			% (asclocaltime(self._time), self.servletPathname()))
		traceback.print_exc(file=stderr)

	def publicErrorPage(self):
		"""Return a public error page.

		Returns a brief error page telling the user that an error has occurred.
		Body of the message comes from ``UserErrorMessage`` setting.

		"""
		return '\n'.join(('<html>', '<head>', '<title>Error</title>',
			htStyle(), '</head>', '<body text="black" bgcolor="white">',
			htTitle('Error'), '<p>%s</p>' % self.setting('UserErrorMessage'),
			'</body>', '</html>\n'))

	def privateErrorPage(self):
		"""Return a private error page.

		Returns an HTML page intended for the developer with
		useful information such as the traceback.

		Most of the contents are generated in `htmlDebugInfo`.

		"""
		html = ['<html>', '<head>', '<title>Error</title>',
			htStyle(), '</head>', '<body text="black" bgcolor="white">',
			htTitle('Error'), '<p>%s</p>' % self.setting('UserErrorMessage')]
		html.append(self.htmlDebugInfo())
		html.extend(['</body>', '</html>\n'])
		return '\n'.join(html)


	def htmlDebugInfo(self):
		"""Return the debug info.

		Return HTML-formatted debugging information about the current exception.
		Calls `writeHTML`, which uses ``self.write(...)`` to add content.

		"""
		self._html = []
		self.writeHTML()
		html = ''.join(self._html)
		self._html = None
		return html

	def writeHTML(self):
		"""Write the traceback.

		Writes all the parts of the traceback, invoking:
		* `writeTraceback`
		* `writeMiscInfo`
		* `writeTransaction`
		* `writeEnvironment`
		* `writeIds`
		* `writeFancyTraceback`

		"""
		self.writeTraceback()
		self.writeMiscInfo()
		self.writeTransaction()
		self.writeEnvironment()
		self.writeIds()
		self.writeFancyTraceback()


	## Write Methods ##

	def write(self, s):
		"""Output `s` to the body."""
		self._html.append(str(s))

	def writeln(self, s):
		"""Output `s` plus a newline."""
		self._html.append(str(s))
		self._html.append('\n')

	def writeTitle(self, s):
		"""Output the sub-heading to define a section."""
		self.writeln(htTitle(s))

	def writeDict(self, d):
		"""Output a table-formated dictionary."""
		self.writeln(htmlForDict(d, filterValueCallBack=self.filterDictValue,
			maxValueLength=self._maxValueLength))

	def writeTable(self, listOfDicts, keys=None):
		"""Output a table from dictionaries.

		Writes a table whose contents are given by `listOfDicts`.
		The keys of each dictionary are expected to be the same.
		If the `keys` arg is None, the headings are taken in alphabetical order
		from the first dictionary. If listOfDicts is false, nothing	happens.

		The keys and values are already considered to be HTML,
		and no quoting is applied.

		Caveat: There's no way to influence the formatting or to use
		column titles that are different than the keys.

		Used by `writeAttrs`.

		"""
		if not listOfDicts:
			return
		if keys is None:
			keys = listOfDicts[0].keys()
			keys.sort()
		wr = self.writeln
		wr('<table border="0" cellpadding="2" cellspacing="2"'
			' style="background-color:#FFFFFF;font-size:10pt">')
		wr('<tr>')
		for key in keys:
			wr('<td style="background-color:#F0F0F0;'
				'font-weight:bold">%s</td>' % key)
		wr('</tr>')
		for row in listOfDicts:
			wr('<tr>')
			for key in keys:
				wr('<td style="background-color:#F0F0F0">%s</td>'
					% self.filterTableValue(row[key], key, row, listOfDicts))
			wr('</tr>')
		wr('</table>')

	def writeAttrs(self, obj, attrNames):
		"""Output object attributes.

		Writes the attributes of the object as given by attrNames.
		Tries ``obj._name` first, followed by ``obj.name()``.
		Is resilient regarding exceptions so as not to spoil the
		exception report.

		"""
		rows = []
		for name in attrNames:
			value = getattr(obj, '_' + name, Singleton) # go for data attribute
			try:
				if value is Singleton:
					value = getattr(obj, name, Singleton) # go for method
					if value is Singleton:
						value = '(could not find attribute or method)'
					else:
						try:
							if callable(value):
								value = value()
						except Exception, e:
							value = '(exception during method call: %s: %s)' \
								% (e.__class__.__name__, e)
						value = self.repr(value)
				else:
					value = self.repr(value)
			except Exception, e:
				value = '(exception during value processing: %s: %s)' \
					% (e.__class__.__name__, e)
			rows.append({'attr': name, 'value': value})
		self.writeTable(rows, ('attr', 'value'))


	## Traceback sections ##

	def writeTraceback(self):
		"""Output the traceback.

		Writes the traceback, with most of the work done
		by `WebUtils.HTMLForException.HTMLForException`.

		"""
		self.writeTitle('Traceback')
		self.write('<p><i>%s</i></p>' % self.servletPathname())
		self.write(HTMLForException(self._exc, self._formatOptions))

	def writeMiscInfo(self):
		"""Output misc info.

		Write a couple little pieces of information about
		the environment.

		"""
		self.writeTitle('MiscInfo')
		info = {
			'time':        asclocaltime(self._time),
			'filename':    self.servletPathname(),
			'os.getcwd()': os.getcwd(),
			'sys.path':    sys.path,
			'sys.version': sys.version,
		}
		self.writeDict(info)

	def writeTransaction(self):
		"""Output transaction.

		Lets the transaction talk about itself, using
		`Transaction.writeExceptionReport`.

		"""
		if self._tra:
			self._tra.writeExceptionReport(self)
		else:
			self.writeTitle("No current Transaction.")

	def writeEnvironment(self):
		"""Output environment.

		Writes the environment this is being run in. This is *not* the
		environment that was passed in with the request (holding the CGI
		information) -- it's just the information from the environment
		that the AppServer is being executed in.

		"""
		self.writeTitle('Environment')
		self.writeDict(os.environ)

	def writeIds(self):
		"""Output OS identification.

		Prints some values from the OS (like processor ID).

		"""
		self.writeTitle('Ids')
		self.writeTable(osIdTable(), ['name', 'value'])

	def writeFancyTraceback(self):
		"""Output a fancy traceback, using cgitb."""
		if self.setting('IncludeFancyTraceback'):
			self.writeTitle('Fancy Traceback')
			try:
				from WebUtils.ExpansiveHTMLForException \
					import ExpansiveHTMLForException
				self.write(ExpansiveHTMLForException(
					context=self.setting('FancyTracebackContext')))
			except Exception:
				self.write('<p>Unable to generate a fancy traceback!'
					' (uncaught exception)</p>')
				try:
					self.write(HTMLForException(sys.exc_info()))
				except Exception:
					self.write('<p>Unable to even generate a normal traceback'
						' of the exception in fancy traceback!</p>')

	def saveErrorPage(self, html):
		"""Save the error page.

		Saves the given HTML error page for later viewing by
		the developer, and returns the filename used.

		"""
		filename = os.path.join(self._app._errorMessagesDir,
			self.errorPageFilename())
		f = open(filename, 'w')
		f.write(html)
		f.close()
		return filename

	def errorPageFilename(self):
		"""Create filename for error page.

		Construct a filename for an HTML error page, not including the
		``ErrorMessagesDir`` setting (which `saveError` adds on)

		"""
		return 'Error-%s-%s-%d.html' % (self.basicServletName(),
			'-'.join(map(lambda x: '%02d' % x, time.localtime(self._time)[:6])),
				random.randint(10000, 99999))
			# @@ 2000-04-21 ce: Using the timestamp & a
			# random number is a poor technique for
			# filename uniqueness, but this works for now

	def logExceptionToDisk(self, errorMsgFilename=''):
		"""Log the exception to disk.

		Writes a tuple containing (date-time, filename,
		pathname, exception-name, exception-data,error report
		filename) to the errors file (typically 'Errors.csv')
		in CSV format. Invoked by `handleException`.

		"""
		if not self.setting('LogErrors'):
			return
		logline = (
			asclocaltime(self._time),
			self.basicServletName(),
			self.servletPathname(),
			str(self._exc[0]),
			str(self._exc[1]),
			errorMsgFilename)
		filename = self._app.serverSidePath(self.setting('ErrorLogFilename'))
		if os.path.exists(filename):
			f = open(filename, 'a')
		else:
			f = open(filename, 'w')
			f.write('time,filename,pathname,exception name,'
				'exception data,error report filename\n')
		def fixElement(element):
			element = str(element)
			if element.find(',') >= 0 or element.find('"') >= 0:
				element = element.replace('"', '""')
				element = '"%s"' % element
			return element
		logline = map(fixElement, logline)
		f.write(','.join(logline) + '\n')
		f.close()

	def emailException(self, htmlErrMsg):
		"""Email the exception.

		Emails the exception, either as an attachment,
		or in the body of the mail.

		"""
		message = StringIO()
		writer = MimeWriter.MimeWriter(message)

		# Construct the message headers
		headers = self.setting('ErrorEmailHeaders').copy()
		headers['Date'] = dateForEmail()
		headers['Mime-Version'] = '1.0'
		headers['Subject'] = headers.get('Subject', '[WebKit Error]') \
			+ ' %s: %s' % sys.exc_info()[:2]
		for h, v in headers.items():
			if isinstance(v, ListType):
				v = ','.join(v)
			writer.addheader(h, v)

		# Construct the message body
		if self.setting('EmailErrorReportAsAttachment'):
			writer.startmultipartbody('mixed')
			# start off with a text/plain part
			part = writer.nextpart()
			body = part.startbody('text/plain')
			body.write('WebKit caught an exception while processing'
				' a request for "%s" at %s (timestamp: %s).'
				' The plain text traceback from Python is printed below and'
				' the full HTML error report from WebKit is attached.\n\n'
					% (self.servletPathname(),
					asclocaltime(self._time), self._time))
			traceback.print_exc(file=body)
			# now add htmlErrMsg
			part = writer.nextpart()
			part.addheader('Content-Transfer-Encoding', '7bit')
			part.addheader('Content-Description',
				'HTML version of WebKit error message')
			body = part.startbody('text/html; name=WebKitErrorMsg.html')
			body.write(htmlErrMsg)
			# finish off
			writer.lastpart()
		else:
			writer.addheader('Content-Type', 'text/html; charset=us-ascii')
			body = writer.startbody('text/html')
			body.write(htmlErrMsg)

		# Send the message
		server = self.setting('ErrorEmailServer')
		# this setting can be: server, server:port, server:port:user:password
		parts = server.split(':', 3)
		server = parts[0]
		try:
			port = int(parts[1])
		except (IndexError, ValueError):
			port = None
		if port:
			server = smtplib.SMTP(server, port)
		else:
			server = smtplib.SMTP(server)
		server.set_debuglevel(0)
		try:
			user = parts[2]
			try:
				passwd = parts[3]
			except IndexError:
				passwd = ''
			server.login(user, passwd)
		except AttributeError: # Python < 2.2
			raise smtplib.SMTPException, \
				"Python version doesn't support SMTP authentication"
		except IndexError:
			pass
		server.sendmail(headers['From'], headers['To'], message.getvalue())
		server.quit()


	## Filtering ##

	def filterDictValue(self, value, key, dict):
		"""Filter dictionary values.

		Filters keys from a dict.  Currently ignores the
		dictionary, and just filters based on the key.

		"""
		return self.filterValue(value, key)

	def filterTableValue(self, value, key, row, table):
		"""Filter table values.

		Invoked by writeTable() to afford the opportunity to filter the values
		written in tables. These values are already HTML when they arrive here.
		Use the extra key, row and table args as necessary.

		"""
		if row.has_key('attr') and key != 'attr':
			return self.filterValue(value, row['attr'])
		else:
			return self.filterValue(value, key)

	def filterValue(self, value, key):
		"""Filter values.

		This is the core filter method that is used in all filtering.
		By default, it simply returns self._hiddenString if the key is
		in self._hideValuesForField (case insensitive). Subclasses
		could override for more elaborate filtering techniques.

		"""
		try:
			key = key.lower()
		except Exception:
			pass
		if key in self._hideValuesForFields:
			return self._hiddenString
		else:
			return value


	## Utility ##

	def repr(self, x):
		"""Get HTML encoded representation.

		Returns the repr() of x already HTML encoded. As a special case,
		dictionaries are nicely formatted in table.

		This is a utility method for `writeAttrs`.

		"""
		if type(x) is DictType:
			return htmlForDict(x, filterValueCallBack=self.filterDictValue,
				maxValueLength=self._maxValueLength)
		else:
			rep = repr(x)
			if self._maxValueLength and len(rep) > self._maxValueLength:
				rep = rep[:self._maxValueLength] + '...'
			return htmlEncode(rep)


## Misc functions ##

def htStyle():
	"""Defines the page style."""
	return ('''<style type="text/css">
<!--
body {
	color: #080810;
	background-color: white;
	font-size: 11pt;
	font-family: Tahoma,Verdana,Arial,Helvetica,sans-serif;
	margin: 0pt;
	padding: 8pt;
}
h2 { font-size: 14pt; }
-->
</style>''')


def htTitle(name):
	"""Formats a `name` as a section title."""
	return ('<h2 style="text-align:center;'
		'color:white;background-color:#993333">%s</h2>' % name)

def osIdTable():
	"""Get all OS id information.

	Returns a list of dictionaries contained id information such as
	uid, gid, etc., all obtained from the os module.
	Dictionary keys are ``"name"`` and ``"value"``.

	"""

	funcs = ['getegid', 'geteuid', 'getgid', 'getpgrp',
		'getpid', 'getppid', 'getuid']
	table = []
	for funcName in funcs:
		if hasattr(os, funcName):
			value = getattr(os, funcName)()
			table.append({'name': funcName, 'value': value})
	return table
