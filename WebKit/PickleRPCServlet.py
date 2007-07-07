import sys, traceback, types
from time import time

try:
	from cPickle import dumps, PickleError
except ImportError:
	from pickle import dumps, PickleError

try:
	import zlib
except ImportError:
	zlib = None

from RPCServlet import RPCServlet
from MiscUtils.PickleRPC import RequestError, SafeUnpickler


class PickleRPCServlet(RPCServlet, SafeUnpickler):
	"""PickleRPCServlet is a base class for Dict-RPC servlets.

	The "Pickle" refers to Python's pickle module. This class is
	similar to XMLRPCServlet. By using Python pickles you get their
	convenience (assuming the client is Pythonic), but lose
	language independence. Some of us don't mind that last one.  ;-)

	Conveniences over XML-RPC include the use of all of the following:
	  * Any pickle-able Python type (mx.DateTime for example)
	  * Python instances (aka objects)
	  * None
	  * Longs that are outside the 32-bit int boundaries
	  * Keyword arguments

	Pickles should also be faster than XML, especially now that
	we support binary pickling and compression.

	To make your own PickleRPCServlet, create a subclass and implement a
	method which is then named in exposedMethods():

		from WebKit.PickleRPCServlet import PickleRPCServlet
		class Math(PickleRPCServlet):
			def multiply(self, x, y):
				return x * y
			def exposedMethods(self):
				return ['multiply']

	To make a PickleRPC call from another Python program, do this:
		from MiscUtils.PickleRPC import Server
		server = Server('http://localhost/WebKit.cgi/Context/Math')
		print server.multiply(3, 4)    # 12
		print server.multiply('-', 10) # ----------

	If a request error is raised by the server, then
	MiscUtils.PickleRPC.RequestError is raised. If an unhandled
	exception is raised by the server, or the server response is
	malformed, then	MiscUtils.PickleRPC.ResponseError (or one of
	it's subclasses) is raised.

	Tip: If you want callers of the RPC servlets to be able to
	introspect what methods are available, then include
	'exposedMethods' in exposedMethods().

	If you wanted the actual response dictionary for some reason:
		print server._request('multiply', 3, 4)
			# { 'value': 12, 'timeReceived': ... }

	In which case, an exception is not purposefully raised if the
	dictionary contains	one. Instead, examine the dictionary.

	For the dictionary formats and more information see the docs
	for MiscUtils.PickleRPC.

	"""

	def respondToPost(self, trans):
		try:
			request = trans.request()
			data = request.rawInput(rewind=1)
			response = {
				'timeReceived': trans.request().time(),
			}
			try:
				try:
					encoding = request.environ().get('HTTP_CONTENT_ENCODING', None)
					if encoding == 'x-gzip':
						if zlib is not None:
							try:
								rawstring = data.read()
								req = self.loads(zlib.decompress(rawstring))
							except zlib.error:
								raise RequestError, \
									'Cannot uncompress compressed dict-rpc request'
						else:
							raise RequestError, \
								'Cannot handle compressed dict-rpc request'
					elif encoding:
						raise RequestError, \
							'Cannot handle Content-Encoding of %s' % encoding
					else:
						req = self.load(data)
				except PickleError:
					raise RequestError, 'Cannot unpickle dict-rpc request.'
				if not isinstance(req, types.DictType):
					raise RequestError, \
						'Expecting a dictionary for dict-rpc requests, ' \
						'but got %s instead.' % type(dict)
				if req.get('version', 1) != 1:
					raise RequestError, 'Cannot handle version %s requests.' \
						% req['version']
				if req.get('action', 'call') != 'call':
					raise RequestError, \
						'Cannot handle the request action, %r.' % req['action']
				try:
					methodName = req['methodName']
				except KeyError:
					raise RequestError, 'Missing method in request'
				args = req.get('args', ())
				if methodName == '__methods__.__getitem__':
					# support PythonWin autoname completion
					response['value'] = self.exposedMethods()[args[0]]
				else:
					response['value'] = self.call(methodName, *args,
						**req.get('keywords', {}))
			except RequestError, e:
				response['requestError'] = str(e)
				self.sendResponse(trans, response)
				self.handleException(trans)
			except Exception, e:
				response['exception'] = self.resultForException(e, trans)
				self.sendResponse(trans, response)
				self.handleException(trans)
			except:  # if it's a string exception, this gets triggered
				response['exception'] = self.resultForException(
					sys.exc_info()[0], trans)
				self.sendResponse(trans, response)
				self.handleException(trans)
			else:
				self.sendResponse(trans, response)
		except Exception:
			# internal error, report as HTTP server error
			print 'PickleRPCServlet internal error'
			print ''.join(traceback.format_exception(*sys.exc_info()))
			trans.response().setStatus(500, 'Server Error')
			self.handleException(trans)

	def sendResponse(self, trans, response):
		"""Timestamp the response dict and send it."""
		# Generated a pickle string
		response['timeResponded'] = time()
		if self.useBinaryPickle():
			contentType = 'application/x-python-binary-pickled-dict'
			response = dumps(response, 1)
		else:
			contentType = 'text/x-python-pickled-dict'
			response = dumps(response)

		# Get list of accepted encodings
		try:
			acceptEncoding = trans.request().environ()["HTTP_ACCEPT_ENCODING"]
			if acceptEncoding:
				acceptEncoding = [enc.strip()
					for enc in acceptEncoding.split(',')]
			else:
				acceptEncoding = []
		except KeyError:
			acceptEncoding = []

		# Compress the output if we are allowed to.
		# We'll avoid compressing short responses and
		# we'll use the fastest possible compression -- level 1.
		if zlib is not None and "gzip" in acceptEncoding \
				and len(response) > 1000:
			contentEncoding = 'x-gzip'
			response = zlib.compress(response, 1)
		else:
			contentEncoding = None
		self.sendOK(contentType, response, trans, contentEncoding)

	def useBinaryPickle(self):
		"""Override this to return 0 to use the less-efficient text pickling format."""
		return 1
