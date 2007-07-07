from WebKit.PickleRPCServlet import PickleRPCServlet


class PickleRPCExample(PickleRPCServlet):
	"""Example XML-RPC servlet.

	To try it out, use something like the following:

	>>> from MiscUtils.PickleRPC import Server
	>>> server = Server('http://localhost/cgi-bin/WebKit.cgi/Examples/PickleRPCExample')
	>>> server.multiply(10,20)
	200
	>>> server.add(10,20)
	30

	You'll get an exception if you try to call divide, because that
	method is not listed in exposedMethods.

	"""

	def exposedMethods(self):
		return ['multiply', 'add']

	def multiply(self, x, y):
		return x * y

	def add(self, x, y):
		return x + y

	def divide(self, *args):
		return reduce(operator.div, args)

	def allowedGlobals(self):
		"""
		This allows you to pass in mx.DateTime objects. See SafeUnpickler in
		MiscUtils.PickleRPC for more details. You are only allowed
		to unpickle classes that are specifically listed here.
		"""
		return [('mx.DateTime', '_DT')]
