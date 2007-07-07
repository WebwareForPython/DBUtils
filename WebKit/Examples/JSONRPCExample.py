#
# JSON-RPC example servlet contributed by Jean-Francois Pieronne
#

from WebKit.JSONRPCServlet import JSONRPCServlet


class JSONRPCExample(JSONRPCServlet):
	"""Example JSON-RPC servlet.

	To try it out, use the JSONRPCClient servlet.

	"""

	def __init__(self):
		JSONRPCServlet.__init__(self)

	def echo(self, msg):
		return msg

	def reverse(self, msg):
		return msg[::-1]

	def uppercase(self, msg):
		return msg.upper()

	def lowercase(self, msg):
		return msg.lower()

	def exposedMethods(self):
		return JSONRPCServlet.exposedMethods(self) + [
			'echo', 'reverse', 'uppercase', 'lowercase']
