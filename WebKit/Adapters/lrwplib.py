#!python
#------------------------------------------------------------------------
#               Copyright (c) 1997 by Total Control Software
#                         All Rights Reserved
#------------------------------------------------------------------------
#
# Module Name:  lrwplib.py
#
# Description:  Class LRWP handles the connection to the LRWP agent in
#               Xitami.  This class can be used standalone or derived
#               from to override behavior.
#
# Creation Date:    11/11/97 8:36:21PM
#
# License:      This is free software.  You may use this software for any
#               purpose including modification/redistribution, so long as
#               this header remains intact and that you do not claim any
#               rights of ownership or authorship of this software.  This
#               software has been tested, but no warranty is expressed or
#               implied.
#
#------------------------------------------------------------------------

import sys, socket
import os, cgi
try:
	from cStringIO import StringIO
except:
	from StringIO import StringIO


__version__ = '1.0'

LENGTHSIZE  = 9
LENGTHFMT   = '%09d'

#---------------------------------------------------------------------------
# Exception objects

ConnectError        = 'lrwp.ConnectError'
ConnectionClosed    = 'lrwp.ConnectionClosed'
SocketError         = 'lrwp.SocketError'

#---------------------------------------------------------------------------

class Request:
	'''
	Encapsulates the request/response IO objects and CGI-Environment.
	An instance of this class is returned
	'''
	def __init__(self, lrwp):
		self.inp = lrwp.inp
		self.out = lrwp.out
		self.err = lrwp.out
		self.env = lrwp.env
		self.lrwp = lrwp

	def finish(self):
		self.lrwp.finish()

	def getFieldStorage(self):
		method = 'POST'
		if self.env.has_key('REQUEST_METHOD'):
			method = self.env['REQUEST_METHOD'].upper()
		return cgi.FieldStorage(fp=method != 'GET' and self.inp or None,
			environ=self.env, keep_blank_values=1)


#---------------------------------------------------------------------------

class LRWP:

	def __init__(self, name, host, port, vhost='', filter='', useStdio=0):
		'''
		Construct an LRWP object.
			name        The name or alias of this request handler.  Requests
						matching http://host/name will be directed to this
						LRWP object.
			host        Hostname or IP address to connect to.
			port        Port number to connect on.
			vhost       If this handler is to only be available to a specific
						virtual host, name it here.
			filter      A space separated list of file extenstions that should
						be directed to this handler in filter mode.  (Not yet
						supported.)
		'''
		self.name = name
		self.host = host
		self.port = port
		self.vhost = vhost
		self.filter = filter
		self.useStdio = useStdio
		self.sock = None
		self.env = None
		self.inp = None
		self.out = None

	#----------------------------------------
	def connect(self):
		'''
		Establishes the connection to the web server, using the parameters
		given at construction.
		'''
		try:
			self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.sock.connect((self.host, self.port))
			self.sock.send("%s\xFF%s\xFF%s"
				% (self.name, self.vhost, self.filter))
			buf = self.sock.recv(1024)
			if buf != 'OK':
				raise ConnectError, buf
		except socket.error, val:
			raise SocketError, val

	#----------------------------------------
	def acceptRequest(self):
		'''
		Wait for, and accept a new request from the Web Server.  Reads the
		name=value pairs that comprise the CGI environment, followed by the
		post data, if any.  Constructs and returns a Request object.
		'''
		if self.out:
			self.finish()
		try:
			# get the length of the environment data
			data = self.recvBlock(LENGTHSIZE)
			if not data: # server closed down
				raise ConnectionClosed
			length = int(data)

			# and then the environment data
			data = self.recvBlock(length)
			if not data: # server closed down
				raise ConnectionClosed
			data = data.split('\000')
			self.env = {}
			for x in data:
				x = x.split('=')
				if len(x) > 1:
					self.env[x[0]] = '='.join(x[1:])

			# now get the size of the POST data
			data = self.recvBlock(LENGTHSIZE)
			if not data: # server closed down
				raise ConnectionClosed
			length = int(data)

			# and the POST data...
			if length:
				data = self.recvBlock(length)
				if not data: # server closed down
					raise ConnectionClosed
				self.inp = StringIO(data)
			else:
				self.inp = StringIO()

			self.out = StringIO()

			# do the switcheroo on the sys IO objects, etc.
			if self.useStdio:
				self.saveStdio = sys.stdin, sys.stdout, sys.stderr, os.environ
				sys.stdin, sys.stdout, sys.stderr, os.environ = \
					self.inp, self.out, self.out, self.env

			return Request(self)

		except socket.error, val:
			raise SocketError, val


	#----------------------------------------
	def recvBlock(self, size):
		'''
		Pull an exact number of bytes from the socket, taking into
		account the possibility of multiple packets...
		'''
		numRead = 0
		data = []
		while numRead < size:
			buf = self.sock.recv(size - numRead)
			if not buf:
				return ''
			data.append(buf)
			numRead += len(buf)

		return ''.join(data)

	#----------------------------------------
	def finish(self):
		'''
		Complete the request and send the output back to the webserver.
		'''
		doc = self.out.getvalue()
		size = LENGTHFMT % (len(doc),)
		try:
			self.sock.send(size)
			self.sock.send(doc)
		except socket.error, val:
			raise SocketError, val

		if self.useStdio:
			sys.stdin, sys.stdout, sys.stderr, os.environ = self.saveStdio

		self.env = None
		self.inp = None
		self.out = None

	#----------------------------------------
	def close(self):
		'''
		Close the LRWP connection to the web server.
		'''
		self.sock.close()
		self.sock = None
		self.env = None
		self.inp = None
		self.out = None

#---------------------------------------------------------------------------


def _test():
	import os, time

	eol = '\r\n'
	appname = 'testapp1'
	vhost = ''
	host = 'localhost'
	port = 5081
	if len(sys.argv) > 1:
		appname = sys.argv[1]
	if len(sys.argv) > 2:
		host = sys.argv[2]
	if len(sys.argv) > 3:
		port = int(sys.argv[3])
	if len(sys.argv) > 4:
		vhost = sys.argv[4]

	lrwp = LRWP(appname, host, port, vhost)
	lrwp.connect()

	count = 0
	while count < 5:        # exit after servicing 5 requests
		req = lrwp.acceptRequest()

		doc = ['<HTML><HEAD><TITLE>LRWP TestApp (%s)</TITLE></HEAD>\n'
			'<BODY>\n' % (appname,)]
		count += 1
		doc.append('<H2>LRWP test app (%s)</H2><P>' % (appname,))
		doc.append('<b>request count</b> = %d<br>' % (count,))
		if hasattr(os, 'getpid'):
			doc.append('<b>pid</b> = %s<br>' % (os.getpid(),))
		doc.append('<br><b>post data:</b> %s<br>' % (req.inp.read(),))

		doc.append('<P><HR><P><pre>')
		keys = req.env.keys()
		keys.sort()
		for k in keys:
			doc.append('<b>%-20s :</b>  %s\n' % (k, req.env[k]))
		doc.append('\n</pre><P><HR>\n')
		doc.append('</BODY></HTML>\n')

		req.out.write('Content-type: text/html' + eol)
		req.out.write(eol)
		req.out.write(''.join(doc))

		req.finish()

	lrwp.close()


if __name__ == '__main__':
	#import pdb
	#pdb.run('_test()')
	_test()
