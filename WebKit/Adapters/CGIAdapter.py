#!/usr/bin/env python
"""
CGIAdapter.py

This is the CGI Adapter for the WebKit AppServer.

This CGI script collects information about the request, puts it into a
package, and then sends it to the WebKit application server over TCP/IP.

This script expects to find a file in it's directory called
'address.text' that specifies the address of the app server.
The file is written by the app server upon successful startup
and contains nothing but:

hostname:port

with no other characters, not even a newline. For example,

localhost:8086

or even:

:8086

...since an empty string is a special case indicating the local host.

"""


import time, sys
timestamp = time.time()

from socket import *
from marshal import dumps, loads
from Adapter import Adapter

debugging = 0   # set 1 if you want to see the raw response dictionary, instead of a normal page

class CGIAdapter(Adapter):
	def run(self):
		import os, sys

		try:
			# MS Windows: no special translation of end-of-lines
			if os.name=='nt':
				import msvcrt
				msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
				msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)

			myInput = ''
			if os.environ.has_key('CONTENT_LENGTH'):
				length = int(os.environ['CONTENT_LENGTH'])
				myInput = myInput + sys.stdin.read(length)


			# 2000-05-20 ce: For use in collecting raw request dictionaries for use in Testing/stress.py
			# Leave this code here in case it's needed again
			#
			#counter = int(open('counter.text').read())
			#counter = counter + 1
			#open('counter.text', 'w').write(str(counter))
			#open('rr-%02d.rr' % counter, 'w').write(str(dict))

			(host, port) = open(os.path.join(self._webKitDir, 'address.text')).read().split(':')
			if os.name=='nt' and host=='': # MS Windows doesn't like a blank host name
				host = 'localhost'
			port = int(port)

			response = self.transactWithAppServer(os.environ.data, myInput, host, port)

			# deliver it!
			# write = sys.stdout.write
			# if debugging:
			#	write('Content-type: text/html\n\n<html><body>')
			#	write('<p> Your adapter has <b>debugging</b> set to true. <p>')
			#	write(HTMLEncode(str(response)))
			#	write('</body></html>')

		except:
			import traceback

			sys.stderr.write('[%s] [error] WebKit.CGIAdapter:'
				' Error while responding to request (unknown)\n'
				% (time.asctime(time.localtime(time.time()))))
			sys.stderr.write('Python exception:\n')
			traceback.print_exc(file=sys.stderr)

			output = apply(traceback.format_exception, sys.exc_info())
			output = ''.join(output)
			output = HTMLEncode(output)
			sys.stdout.write('''Content-type: text/html

<html><body>
<p><pre>ERROR

%s</pre>
</body></html>\n''' % output)


	def processResponse(self, data):
		sys.stdout.write(data)
		sys.stdout.flush()


HTMLCodes = [
	['&', '&amp;'],
	['<', '&lt;'],
	['>', '&gt;'],
	['"', '&quot;'],
]

def HTMLEncode(s, codes=HTMLCodes):
	""" Returns the HTML encoded version of the given string. This is useful to display a plain ASCII text string on a web page. (We could get this from WebUtils, but we're keeping CGIAdapter independent of everything but standard Python.) """
	for code in codes:
		s = s.replace(code[0], code[1])
	return s

def main(webKitDir):
	CGIAdapter(webKitDir).run()
