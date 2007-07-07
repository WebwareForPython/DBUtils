#!/usr/bin/env python

# CGIWrapper.py
# Webware for Python
# See the CGIWrapper.html documentation for more information.


# We first record the starting time, in case we're being run as a CGI script.
from time import time, localtime, gmtime, asctime
serverStartTime  = time()

# Some imports
import cgi, os, sys, traceback, random
from types import DictType, FloatType

if '' not in sys.path:
	sys.path.insert(0, '')

try:
	import WebUtils
except:
	sys.path.append(os.path.abspath('..'))
	import WebUtils
from WebUtils.HTMLForException import HTMLForException

import MiscUtils
from MiscUtils.NamedValueAccess import NamedValueAccess
from UserDict import UserDict

# @@ 2000-05-01 ce:
# PROBLEM: For reasons unknown, target scripts cannot import modules of
#   the WebUtils package *unless* they are already imported.
# TEMP SOLUTION: Import all the modules.
# TO DO: distill this problem and post to comp.lang.python for help.
# begin
import WebUtils.Cookie
import WebUtils.HTTPStatusCodes
# end


# Beef up UserDict with the NamedValueAccess base class and custom versions of
# hasValueForKey() and valueForKey(). This all means that UserDict's (such as
# os.environ) are key/value accessible. At some point, this probably needs to
# move somewhere else as other Webware components will need this "patch".
# @@ 2000-01-14 ce: move this
#
if not NamedValueAccess in UserDict.__bases__:
	UserDict.__bases__ += (NamedValueAccess,)

	def _UserDict_hasValueForKey(self, key):
		return self.has_key(key)

	def _UserDict_valueForKey(self, key, default=None):
		return self.get(key, default)

	setattr(UserDict, 'hasValueForKey', _UserDict_hasValueForKey)
	setattr(UserDict, 'valueForKey', _UserDict_valueForKey)

try:
	from cStringIO import StringIO
except ImportError:
	from StringIO import StringIO


class CGIWrapper(NamedValueAccess):
	"""
	A CGIWrapper executes a target script and provides various services for
	the both the script and website developer and administrator.

	See the CGIWrapper.html documentation for full information.
	"""


	## Init ##

	def __init__(self):
		self._config = self.config()


	## Configuration ##

	def defaultConfig(self):
		"""
		Returns a dictionary with the default
		configuration. Subclasses could override to customize
		the values or where they're taken from.
		"""

		return {
			'ScriptsHomeDir': 'Scripts',
			'ChangeDir': 1,
			'ExtraPaths': [],
			'ExtraPathsIndex': 1,
			'LogScripts': 1,
			'ScriptLogFilename': 'Scripts.csv',
			'ScriptLogColumns': [
				'environ.REMOTE_ADDR',
				'environ.REQUEST_METHOD', 'environ.REQUEST_URI',
				'responseSize', 'scriptName',
				'serverStartTimeStamp', 'serverDuration',
				'scriptDuration', 'errorOccurred'
			],
			'ClassNames': ['', 'Page'],
			'ShowDebugInfoOnErrors': 1,
			'UserErrorMessage': 'The site is having technical difficulties'
				' with this page. An error has been logged, and the problem'
				' will be fixed as soon as possible. Sorry!',
			'LogErrors': 1,
			'ErrorLogFilename': 'Errors.csv',
			'SaveErrorMessages': 1,
			'ErrorMessagesDir': 'ErrorMsgs',
			'EmailErrors': 0,
			'ErrorEmailServer': 'localhost',
			'ErrorEmailHeaders': {
				'From': 'webware@mydomain',
				'To': ['webware@mydomain'],
				'Reply-to': 'webware@mydomain',
				'Content-type': 'text/html',
				'Subject': 'Error'
			}
		}

	def configFilename(self):
		"""Used by userConfig()."""
		return 'Config.dict'

	def userConfig(self):
		"""
		Returns the user config overrides found in the
		optional config file, or {} if there is no such
		file. The config filename is taken from
		configFilename().
		"""

		try:
			file = open(self.configFilename())
		except IOError:
			return {}
		else:
			config = eval(file.read())
			file.close()
			assert type(config) is DictType
			return config

	def config(self):
		"""
		Returns the configuration for the wrapper which is a
		combination of defaultConfig() and userConfig(). This
		method does no caching.
		"""
		config = self.defaultConfig()
		config.update(self.userConfig())
		return config

	def setting(self, name):
		"""Returns the value of a particular setting in the configuration."""
		return self._config[name]


	## Utilities ##

	def makeHeaders(self):
		"""Returns a default header dictionary containing {'Content-type': 'text/html'}."""
		return {'Content-type': 'text/html'}

	def makeFieldStorage(self):
		"""Returns a default field storage object created from the cgi module."""
		return cgi.FieldStorage()

	def enhanceThePath(self):
		"""Enhance sys.path according to our configuration."""
		extraPathsIndex = self.setting('ExtraPathsIndex')
		sys.path[extraPathsIndex:extraPathsIndex] = self.setting('ExtraPaths')

	def requireEnvs(self, names):
		"""
		Checks that given environment variable names exist. If
		they don't, a basic HTML error message is printed and
		we exit.
		"""
		badNames = []
		for name in names:
			if not self._environ.has_key(name):
				badNames.append(name)
		if badNames:
			print 'Content-type: text/html\n'
			print '<html><body>'
			print '<p>ERROR: Missing', ', '.join(badNames)
			print '</body></html>'
			sys.exit(0)

	def scriptPathname(self):
		"""
		Returns the full pathname of the target
		script. Scripts that start with an underscore are
		special--they run out of the same directory as the CGI
		Wrapper and are typically CGI Wrapper support
		scripts.
		"""
		pathname = os.path.split(self._environ['SCRIPT_FILENAME'])[0] # This removes the CGI Wrapper's filename part
		filename = self._environ['PATH_INFO'][1:]
		ext      = os.path.splitext(filename)[1]
		if ext == '':
			# No extension - we assume a Python CGI script
			if filename[0] == '_':
				# underscores denote private scripts packaged with CGI Wrapper, such as '_admin.py'
				filename = os.path.join(pathname, filename + '.py')
			else:
				# all other scripts are based in the directory named by the 'ScriptsHomeDir' setting
				filename = os.path.join(pathname, self.setting('ScriptsHomeDir'), filename + '.py')
			self._servingScript = 1
		else:
			# Hmmm, some kind of extension like maybe '.html'. Leave out the 'ScriptsHomeDir' and leave the extension alone
			filename = os.path.join(pathname, filename)
			self._servingScript = 0
		return filename

	def writeScriptLog(self):
		"""
		Writes an entry to the script log file. Uses settings
		ScriptLogFilename and ScriptLogColumns.
		"""
		filename = self.setting('ScriptLogFilename')
		if os.path.exists(filename):
			file = open(filename, 'a')
		else:
			file = open(filename, 'w')
			file.write(','.join(self.setting('ScriptLogColumns')) + '\n')
		values = []
		for column in self.setting('ScriptLogColumns'):
			value = self.valueForName(column)
			if type(value) is FloatType:
				value = '%0.2f' % value   # might need more flexibility in the future
			else:
				value = str(value)
			values.append(value)
		file.write(','.join(values) + '\n')
		file.close()

	def version(self):
		return '0.2'


	## Exception handling ##

	def handleException(self, excInfo):
		"""
		Invoked by self when an exception occurs in the target
		script. <code>excInfo</code> is a sys.exc_info()-style
		tuple of information about the exception.
		"""

		self._scriptEndTime = time() # Note the duration of the script and time of the exception
		self.logExceptionToConsole()
		self.reset()
		print self.htmlErrorPage(showDebugInfo=self.setting('ShowDebugInfoOnErrors'))
		fullErrorMsg = None
		if self.setting('SaveErrorMessages'):
			fullErrorMsg = self.htmlErrorPage(showDebugInfo=1)
			filename = self.saveHTMLErrorPage(fullErrorMsg)
		else:
			filename = ''
		self.logExceptionToDisk(filename)
		if self.setting('EmailErrors'):
			if fullErrorMsg is None:
				fullErrorMsg = self.htmlErrorPage(showDebugInfo=1)
			self.emailException(fullErrorMsg)

	def logExceptionToConsole(self, stderr=sys.stderr):
		"""
		Logs the time, script name and traceback to the
		console (typically stderr). This usually results in
		the information appearing in the web server's error
		log. Used by handleException().
		"""
		# stderr logging
		stderr.write('[%s] [error] CGI Wrapper: Error while executing script %s\n' % (
			asctime(localtime(self._scriptEndTime)), self._scriptPathname))
		traceback.print_exc(file=stderr)

	def reset(self):
		"""
		Used by handleException() to clear out the current CGI
		output results in preparation of delivering an HTML
		error message page. Currently resets headers and
		deletes cookies, if present.
		"""
		# Set headers to basic text/html. We don't want stray headers from a script that failed.
		headers = {'Content-Type': 'text/html'}

		# Get rid of cookies, too
		if self._namespace.has_key('cookies'):
			del self._namespace['cookies']

	def htmlErrorPage(self, showDebugInfo=1):
		"""
		Returns an HTML page explaining that there is an
		error. There could be more options in the future so
		using named arguments (e.g., 'showDebugInfo=1') is
		recommended. Invoked by handleException().
		"""
		html = ['''
<html>
	<title>Error</title>
	<body fgcolor=black bgcolor=white>
%s
<p> %s''' % (htTitle('Error'), self.setting('UserErrorMessage'))]

		if self.setting('ShowDebugInfoOnErrors'):
			html.append(self.htmlDebugInfo())

		html.append('</body></html>')
		return ''.join(html)

	def htmlDebugInfo(self):
		"""
		Return HTML-formatted debugging information about the
		current exception. Used by handleException().
		"""
		html = ['''
%s
<p> <i>%s</i>
''' % (htTitle('Traceback'), self._scriptPathname)]

		html.append(HTMLForException())

		html.extend([
			htTitle('Misc Info'),
			htDictionary({
				'time':          asctime(localtime(self._scriptEndTime)),
				'filename':      self._scriptPathname,
				'os.getcwd()':   os.getcwd(),
				'sys.path':      sys.path
			}),
			htTitle('Fields'),        htDictionary(self._fields),
			htTitle('Headers'),       htDictionary(self._headers),
			htTitle('Environment'),   htDictionary(self._environ, {'PATH': ';'}),
			htTitle('Ids'),           htTable(osIdTable(), ['name', 'value'])])

		return ''.join(html)

	def saveHTMLErrorPage(self, html):
		"""
		Saves the given HTML error page for later viewing by
		the developer, and returns the filename used. Invoked
		by handleException().
		"""
		filename = os.path.join(self.setting('ErrorMessagesDir'), self.htmlErrorPageFilename())
		f = open(filename, 'w')
		f.write(html)
		f.close()
		return filename

	def htmlErrorPageFilename(self):
		"""Construct a filename for an HTML error page, not including the 'ErrorMessagesDir' setting."""
		return 'Error-%s-%s-%d.html' % (
			os.path.split(self._scriptPathname)[1],
			'-'.join(map(lambda x: '%02d' % x, localtime(self._scriptEndTime)[:6])),
			random.randint(10000, 99999))
			# @@ 2000-04-21 ce: Using the timestamp & a random number is a poor technique for filename uniqueness, but this works for now

	def logExceptionToDisk(self, errorMsgFilename='', excInfo=None):
		"""
		Writes a tuple containing (date-time, filename,
		pathname, exception-name, exception-data,error report
		filename) to the errors file (typically 'Errors.csv')
		in CSV format. Invoked by handleException().
		"""
		if not excInfo:
			excInfo = sys.exc_info()
		logline = (
			asctime(localtime(self._scriptEndTime)),
			os.path.split(self._scriptPathname)[1],
			self._scriptPathname,
			str(excInfo[0]),
			str(excInfo[1]),
			errorMsgFilename)
		filename = self.setting('ErrorLogFilename')
		if os.path.exists(filename):
			f = open(filename, 'a')
		else:
			f = open(filename, 'w')
			f.write('time,filename,pathname,exception name,exception data,error report filename\n')
		f.write(','.join(logline))
		f.write('\n')
		f.close()

	def emailException(self, html, excInfo=None):
		# Construct the message
		if not excInfo:
			excInfo = sys.exc_info()
		headers = self.setting('ErrorEmailHeaders')
		msg = []
		for key in headers.keys():
			if key != 'From' and key != 'To':
				msg.append('%s: %s\n' % (key, headers[key]))
		msg.append('\n')
		msg.append(html)
		msg = ''.join(msg)

		# dbg code, in case you're having problems with your e-mail
		# open('error-email-msg.text', 'w').write(msg)

		# Send the message
		import smtplib
		server = smtplib.SMTP(self.setting('ErrorEmailServer'))
		server.set_debuglevel(0)
		server.sendmail(headers['From'], headers['To'], msg)
		server.quit()



	## Serve ##

	def serve(self, environ=os.environ):
		# Record the time
		if globals().has_key('isMain'):
			self._serverStartTime = serverStartTime
		else:
			self._serverStartTime = time()
		self._serverStartTimeStamp = asctime(localtime(self._serverStartTime))

		# Set up environment
		self._environ = environ

		# Ensure that filenames and paths have been provided
		self.requireEnvs(['SCRIPT_FILENAME', 'PATH_INFO'])

		# Set up the namespace
		self._headers = self.makeHeaders()
		self._fields = self.makeFieldStorage()
		self._scriptPathname = self.scriptPathname()
		self._scriptName = os.path.split(self._scriptPathname)[1]

		# @@ 2000-04-16 ce: Does _namespace need to be an ivar?
		self._namespace = {
			'headers': self._headers,
			'fields': self._fields,
			'environ': self._environ,
			'wrapper': self,
			# 'WebUtils': WebUtils, # @@ 2000-05-01 ce: Resolve.
		}
		info = self._namespace.copy()

		# Set up sys.stdout to be captured as a string. This allows scripts
		# to set CGI headers at any time, which we then print prior to
		# printing the main output. This also allows us to skip on writing
		# any of the script's output if there was an error.
		#
		# This technique was taken from Andrew M. Kuchling's Feb 1998
		# WebTechniques article.
		#
		self._realStdout = sys.stdout
		sys.stdout = StringIO()

		# Change directories if needed
		if self.setting('ChangeDir'):
			origDir = os.getcwd()
			os.chdir(os.path.split(self._scriptPathname)[0])
		else:
			origDir = None

		# A little more setup
		self._errorOccurred = 0
		self._scriptStartTime = time()

		# Run the target script
		try:
			if self._servingScript:
				execfile(self._scriptPathname, self._namespace)
				for name in self.setting('ClassNames'):
					if name == '':
						name = os.path.splitext(self._scriptName)[0]
					if self._namespace.has_key(name):         # our hook for class-oriented scripts
						print self._namespace[name](info).html()
						break
			else:
				self._headers = {'Location':
					os.path.split(self._environ['SCRIPT_NAME'])[0]
					+ self._environ['PATH_INFO']}

			# Note the end time of the script
			self._scriptEndTime = time()
			self._scriptDuration = self._scriptEndTime - self._scriptStartTime
		except:
			# Note the end time of the script
			self._scriptEndTime = time()
			self._scriptDuration = self._scriptEndTime - self._scriptStartTime

			self._errorOccurred = 1

			# Not really an error, if it was sys.exit(0)
			excInfo = sys.exc_info()
			if excInfo[0] == SystemExit:
				code = excInfo[1].code
				if not code:
					self._errorOccurred = 0

			# Clean up
			if self._errorOccurred:
				if origDir:
					os.chdir(origDir)
					origDir = None

				# Handle exception
				self.handleException(sys.exc_info())

		self.deliver()

		# Restore original directory
		if origDir:
			os.chdir(origDir)

		# Note the duration of server processing (as late as we possibly can)
		self._serverDuration = time() - self._serverStartTime

		# Log it
		if self.setting('LogScripts'):
			self.writeScriptLog()


	def deliver(self):
		"""Deliver the HTML, whether it came from the script being served, or from our own error reporting."""

		# Compile the headers & cookies
		headers = StringIO()
		for header, value in self._headers.items():
			headers.write("%s: %s\n" % (header, value))
		if self._namespace.has_key('cookies'):
			headers.write(str(self._namespace['cookies']))
		headers.write('\n')

		# Get the string buffer values
		headersOut = headers.getvalue()
		stdoutOut  = sys.stdout.getvalue()

		# Compute size
		self._responseSize = len(headersOut) + len(stdoutOut)

		# Send to the real stdout
		self._realStdout.write(headersOut)
		self._realStdout.write(stdoutOut)


# Some misc functions
def htTitle(name):
	return '''
<p> <br> <table border=0 cellpadding=4 cellspacing=0 bgcolor=#A00000> <tr> <td>
	<font face="Tahoma, Arial, Helvetica" color=white> <b> %s </b> </font>
</td> </tr> </table>''' % name

def htDictionary(dict, addSpace=None):
	"""Returns an HTML string with a <table> where each row is a key-value pair."""
	keys = dict.keys()
	keys.sort()
	html = ['<table width=100% border=0 cellpadding=2 cellspacing=2 bgcolor=#F0F0F0>']
	for key in keys:
		value = dict[key]
		if addSpace is not None and addSpace.has_key(key):
			target = addSpace[key]
			value = ('%s ' % target).join(value.split(target))
		html.append('<tr> <td> %s </td> <td> %s &nbsp;</td> </tr>\n' % (key, value))
	html.append('</table>')
	return ''.join(html)

def osIdTable():
	"""
	Returns a list of dictionaries contained id information such
	as uid, gid, etc., all obtained from the os module. Dictionary
	keys are 'name' and 'value'.
	"""
	funcs = ['getegid', 'geteuid', 'getgid', 'getpgrp', 'getpid', 'getppid', 'getuid']
	table = []
	for funcName in funcs:
		if hasattr(os, funcName):
			value = getattr(os, funcName)()
			table.append({'name': funcName, 'value': value})
	return table

def htTable(listOfDicts, keys=None):
	"""
	The listOfDicts parameter is expected to be a list of
	dictionaries whose keys are always the same.  This function
	returns an HTML string with the contents of the table.  If
	keys is None, the headings are taken from the first row in
	alphabetical order.  Returns an empty string if listOfDicts is
	none or empty.

	Deficiencies: There's no way to influence the formatting or to
	use column titles that are different than the keys.
	"""

	if not listOfDicts:
		return ''
	if keys is None:
		keys = listOfDicts[0].keys()
		keys.sort()
	s = '<table border=0 cellpadding=2 cellspacing=2 bgcolor=#F0F0F0>\n<tr>'
	for key in keys:
		s = '%s<td><b>%s</b></td>' % (s, key)
	s += '</tr>\n'
	for row in listOfDicts:
		s += '<tr>'
		for key in keys:
			s = '%s<td>%s</td>' % (s, row[key])
		s += '</tr>\n'
	s += '</table>'
	return s


def main():
	stdout = sys.stdout
	try:
		wrapper = CGIWrapper()
		wrapper.serve()
	except:
		# There is already a fancy exception handler in the CGIWrapper for
		# uncaught exceptions from target scripts. However, we should also
		# catch exceptions here that might come from the wrapper, including
		# ones generated while it's handling exceptions.
		import traceback
		sys.stderr.write('[%s] [error] CGI Wrapper: Error while executing script (unknown)\n' % (
			asctime(localtime(time()))))
		sys.stderr.write('Error while executing script\n')
		traceback.print_exc(file=sys.stderr)
		output = traceback.format_exception(*sys.exc_info())
		output = ''.join(output)
		output = output.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
		stdout.write('''Content-type: text/html

<html><body>
<p>ERROR
<p><pre>%s</pre>
</body></html>\n''' % output)


if __name__ == '__main__':
	isMain = 1
	main()
