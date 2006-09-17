"""
M2Crypto-enhanced transport for PickleRPC

This lets you use M2Crypto for SSL encryption.

Based on m2xmlrpclib.py which is
	Copyright (c) 1999-2002 Ng Pheng Siong. All rights reserved
"""

from PickleRPC import Transport
import base64, string, sys
from M2Crypto import SSL, httpslib, m2urllib
try:
	from cStringIO import StringIO
except ImportError:
	from StringIO import StringIO

__version__ = 1   # version of M2PickleRPC

class M2Transport(Transport):
	user_agent = "M2PickleRPC.py/%s - %s" % (__version__, Transport.user_agent)

	def __init__(self, ssl_context=None):
		if ssl_context is None:
			self.ssl_ctx=SSL.Context('sslv23')
		else:
			self.ssl_ctx=ssl_context

	def make_connection(self, host):
		_host, _port = m2urllib.splitport(host)
		if sys.version[0] == '2':
			return httpslib.HTTPS(_host, int(_port), ssl_context=self.ssl_ctx)
		elif sys.version[:3] ==  '1.5':
			return httpslib.HTTPS(self.ssl_ctx, _host, int(_port))
		else:
			raise RuntimeError, 'unsupported Python version'

	# @@ workarounds below are necessary because M2Crypto seems to
	# return from fileobject.read() early!  So we have to call it
	# over and over to get the full data.
	
	def parse_response(self, f):
		"""
		Workaround M2Crypto issue mentioned above
		"""
		sio = StringIO()
		while 1:
			chunk = f.read()
			if not chunk:
				break
			sio.write(chunk)
		sio.seek(0)
		return Transport.parse_response(self, sio)

	def parse_response_gzip(self, f):
		"""
		Workaround M2Crypto issue mentioned above
		"""
		sio = StringIO()
		while 1:
			chunk = f.read()
			if not chunk:
				break
			sio.write(chunk)
		sio.seek(0)
		return Transport.parse_response_gzip(self, sio)

