"""
OneShotAdapter.py

This is a special version of the CGIAdapter that doesn't require a persistent AppServer process. This is mostly useful during development when repeated changes to classes forces the developer to restart the app server to make the changes take effect.

An example, URL:

	http://127.0.0.1/OneShot.cgi/MyPage

"""


# 2000-08-07 ce: For accuracy purposes, we want to record the timestamp as early as possible.
import time
_timestamp = time.time()


# 2000-08-07 ce: We have to reassign sys.stdout *immediately* because it's referred to as a default parameter value in Configurable.py which happens to be our ancestor class as well as the ancestor class of AppServer and Application. The Configurable method that uses sys.stdout for a default parameter value must not execute before we rewire sys.stdout. Tricky, tricky.
# 2000-12-04 ce: Couldn't this be fixed by Configurable taking None as the default and then using sys.stdout if arg==None?
try:
	from cStringIO import StringIO
except ImportError:
	from StringIO import StringIO
import sys
_real_stdout = sys.stdout
sys.stdout = _console = StringIO()  # to capture the console output of the application

import os
from Adapter import *
from MiscUtils.Funcs import charWrap
from WebUtils.Funcs import htmlEncode


class OneShotAdapter(Adapter):

	def defaultConfig(self):
		config = Adapter.defaultConfig(self)
		config.update({
			'ShowConsole':           0,
			'ConsoleWidth':          80,  # use 0 to turn off
			'ConsoleHangingIndent':  4,
		})
		return config

	def run(self):

		try:
#			myInput = ''
#			if os.environ.has_key('CONTENT_LENGTH'):
#				length = int(os.environ['CONTENT_LENGTH'])
#				if length:
#					myInput = sys.stdin.read(length)
			#myInput = sys.stdin.read()

			# MS Windows: no special translation of end-of-lines
			if os.name=='nt':
				import msvcrt
				msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)

			dict = {
				'format':  'CGI',
				'time':    _timestamp,
				'environ': os.environ.data, # ce: a little tricky. We use marshal which only works on built-in types, so we need environ's dictionary
#				'input':   myInput,
				'input':   sys.stdin,
			}

			from WebKit import Profiler
			Profiler.startTime = time.time()

			print 'ONE SHOT MODE\n'

			from WebKit.OneShotAppServer import OneShotAppServer
			appSvr = OneShotAppServer(self._webKitDir)

			# It is important to call transaction.die() after using it, rather than just
			# letting it fall out of scope, to avoid circular references
			from WebKit.ASStreamOut import ASStreamOut
			rs = ASStreamOut()
			transaction = appSvr.dispatchRawRequest(dict, rs)
			rs.close()
			transaction.die()
			del transaction

			appSvr.shutDown()
			appSvr = None

			print "AppServer Run Time %.2f seconds" % ( time.time() - Profiler.startTime )
			sys.stdout = _real_stdout

			# MS Windows: no special translation of end-of-lines
			if os.name=='nt':
				import msvcrt
				msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

			write = sys.stdout.write
			write(rs._buffer)

			if self.setting('ShowConsole'):
				# show the contents of the console, but only if we
				# are serving up an HTML file
				endheaders = rs._buffer.find("\r\n\r\n")
				if endheaders == None:
					endheaders = rs._buffer.find("\n\n")
				if not endheaders:
					print "No Headers Found"
					return
				headers = rs._buffer[:endheaders].split("\n")
				entries = []
				for header in headers:
					entries.append(header.split(":"))
				found = 0
				for name, value in entries:
					if name.lower() == 'content-type':
						found = 1
						break
				if found and value.strip().lower() == 'text/html':
					self.showConsole(_console.getvalue())
		except:
			import traceback

			sys.stderr.write('[%s] [error] WebKit.OneShotAdapter: Error while responding to request (unknown)\n' % (time.asctime(time.localtime(time.time()))))
			sys.stderr.write('Python exception:\n')
			traceback.print_exc(file=sys.stderr)

			output = apply(traceback.format_exception, sys.exc_info())
			output = ''.join(output).replace('&', '&amp;').replace(
				'<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
			sys.stdout.write('''Content-type: text/html

<html><body>
<p><pre>ERROR

%s</pre>
</body></html>\n''' % output)

	def showConsole(self, contents):
		width = self.setting('ConsoleWidth')
		if width:
			contents = charWrap(contents, self.setting('ConsoleWidth'), self.setting('ConsoleHangingIndent'))
		contents = htmlEncode(contents)
		sys.stdout.write('<br><p><table><tr><td bgcolor=#EEEEEE><pre>%s</pre></td></tr></table>' % contents)


def main(webKitDir=None):
	if webKitDir is None:
		import os
		webKitDir = os.path.dirname(os.getcwd())
	try:
		OneShotAdapter(webKitDir).run()
	except:
		import traceback

		sys.stderr.write('[%s] [error] OneShotAdapter: Error while responding to request (unknown)\n' % (time.asctime(time.localtime(time.time()))))
		sys.stderr.write('Python exception:\n')
		traceback.print_exc(file=sys.stderr)

		output = apply(traceback.format_exception, sys.exc_info())
		output = ''.join(output).replace('&', '&amp;').replace(
			'<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
		sys.stdout.write('''Content-type: text/html

<html><body>
<p><pre>ERROR

%s</pre>
</body></html>\n''' % output)
