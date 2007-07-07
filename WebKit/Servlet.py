from Common import *
from MiscUtils.Funcs import excstr


class Servlet(Object):
	"""A general servlet.

	A servlet is a key portion of a server-based application that implements
	the semantics of a particular request by providing a response.
	This abstract class defines servlets at a very high level.
	Most often, developers will subclass HTTPServlet or even Page.

	Servlets can be created once, then used and destroyed, or they may be
	reused several times over (it's up to the server). Therefore, servlet
	developers should take the proper actions in awake() and sleep()
	so that reuse can occur.

	Objects that participate in a transaction include:
		* Application
		* Request
		* Transaction
		* Session
		* Servlet
		* Response

	The awake(), respond() and sleep() methods form a message sandwich.
	Each is passed an instance of Transaction which gives further access
	to all the objects involved.

	"""


	## Init ##

	def __init__(self):
		"""Subclasses must invoke super."""
		Object.__init__(self)
		self._serverSidePath = None
		self._factory = None
		self._busy = False


	## Access ##

	def name(self):
		"""Return the name which is simple the name of the class.

		Subclasses should *not* override this method.
		It is used for logging and debugging.

		"""
		return self.__class__.__name__


	## Request-response cycles ##

	def runTransaction(self, trans):
		try:
			trans.awake()
			trans.respond()
		except Exception, first:
			try:
				trans.sleep()
			except Exception, second:
				# The first exception is more important than the *second* one
				# that comes from sleep(). In fact, without this little trick
				# the first exception gets hidden by the second which is often
				# just a result of the first. Then you're stuck scratching your
				# head wondering what the first might have been.
				raise Exception('Two exceptions. first=%s; second=%s'
					% (excstr(first), excstr(second)))
			else:
				raise # no problems with sleep() so raise the one and only exception
		else:
			trans.sleep()

	def runMethodForTransaction(self, trans, method, *args, **kw):
		self.awake(trans)
		result = getattr(self, method)(*args, **kw)
		self.sleep(trans)
		return result

	def awake(self, trans):
		"""Send the awake message.

		This message is sent to all objects that participate in the
		request-response cycle in a top-down fashion, prior to respond().
		Subclasses must invoke super.

		"""
		self._transaction = trans

	def respond(self, trans):
		"""Respond to a request."""
		raise AbstractError, self.__class__

	def sleep(self, trans):
		"""Send the sleep message."""
		pass


	## Log ##

	def log(self, message):
		"""Log a message.

		This can be invoked to print messages concerning the servlet.
		This is often used by self to relay important information back
		to developers.

		"""
		print '[%s] [msg] %s' % (asclocaltime(), message)


	## Abilities ##

	def canBeThreaded(self):
		"""Return whether the servlet can be multithreaded.

		This value should not change during the lifetime of the object.
		The default implementation returns False.
		Note: This is not currently used.

		"""
		return False

	def canBeReused(self):
		"""Returns whether a single servlet instance can be reused.

		The default is True, but subclasses con override to return False.
		Keep in mind that performance may seriously be degraded if instances
		can't be reused. Also, there's no known good reasons not to reuse
		an instance. Remember the awake() and sleep() methods are invoked
		for every transaction. But just in case, your servlet can refuse
		to be reused.

		"""
		return True


	## Server side filesystem ##

	def serverSidePath(self, path=None):
		"""Return the filesystem path of the page on the server."""
		if self._serverSidePath is None:
			self._serverSidePath = self._transaction.request().serverSidePath()
		if path:
			if path.startswith('/'):
				path = path[1:]
			return os.path.normpath(os.path.join(
				os.path.dirname(self._serverSidePath), path))
		else:
			return self._serverSidePath


	## Private ##

	def open(self):
		self._busy = True

	def close(self):
		if self._busy and self._factory:
			self._busy = False
			self._factory.returnServlet(self)

	def setFactory(self, factory):
		self._factory = factory
