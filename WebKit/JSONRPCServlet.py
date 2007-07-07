"""JSON-RPC servlet base class

Written by Jean-Francois Pieronne

"""

import traceback
from MiscUtils import StringIO
try:
	import simplejson
except ImportError:
	print "ERROR: simplejson is not installed."
	print "Get it from http://cheeseshop.python.org/pypi/simplejson"

from HTTPContent import HTTPContent


class JSONRPCServlet(HTTPContent):
	"""A superclass for Webware servlets using JSON-RPC techniques.

	JSONRPCServlet can be used to make coding JSON-RPC applications easier.

	Subclasses should override the method json_methods() which returns a list
	of method names. These method names refer to Webware Servlet methods that
	are able to be called by an JSON-RPC-enabled web page. This is very similar
	in functionality to Webware's actions.

	Some basic security measures against JavaScript hijacking are taken	by
	default which can be deactivated if you're not dealing with sensitive data.
	You can further increase security by adding shared secret mechanisms.

	"""

	# Class level variables that can be overridden by servlet instances:
	_debug = 0 # set to True if you want to see debugging output
	# The following variables control security precautions concerning
	# a vulnerability known as "JavaScript hijacking". See also:
	# http://www.fortifysoftware.com/servlet/downloads/public/JavaScript_Hijacking.pdf
	# http://ajaxian.com/archives/protecting-a-javascript-service
	_allowGet = 0 # set to True if you want to allow GET requests
	_allowEval = 0 # set to True to allow direct evaluation of the response

	def __init__(self):
		HTTPContent.__init__(self)

	def respondToGet(self, transaction):
		if self._allowGet:
			self.writeError("GET method not allowed")
		HTTPContent.respondToGet(self, transaction)

	def defaultAction(self):
		self.jsonCall()

	def actions(self):
		actions = HTTPContent.actions(self)
		actions.append('jsonCall')
		return actions

	def exposedMethods(self):
		return []

	def writeError(self, msg):
		self.write(simplejson.dumps({'id': self._id, 'code': -1, 'error': msg}))

	def writeResult(self, data):
		data = simplejson.dumps({'id': self._id, 'result': data})
		if not self._allowEval:
			data = 'throw new Error' \
				'("Direct evaluation not allowed");\n/*%s*/' % (data,)
		self.write(data)

	def jsonCall(self):
		"""Execute method with arguments on the server side.

		Returns Javascript function to be executed by the client immediately.

		"""
		request = self.request()
		data = simplejson.loads(request.rawInput().read())
		self._id, call, params = data["id"], data["method"], data["params"]
		if call == 'system.listMethods':
			self.writeResult(self.exposedMethods())
		elif call in self.exposedMethods():
			try:
				method = getattr(self, call)
			except AttributeError:
				self.writeError('%s, although an approved method, '
					'was not found' % call)
			else:
				try:
					if self._debug:
						self.log("json call %s(%s)" % (call, params))
					self.writeResult(method(*params))
				except Exception:
					err = StringIO()
					traceback.print_exc(file=err)
					e = err.getvalue()
					self.writeError('%s was called, '
						'but encountered an error: %s' % (call, e))
					err.close()
		else:
			self.writeError('%s is not an approved method' % call)
