from Common import *
from Message import Message


class Request(Message):
	"""The abstract request class.

	Request is a type of Message that offers the following:

		* A time stamp (indicating when the request was made)
		* An input stream. @@ 2000-04-30 ce: resolve this
		* Remote request information (address, name)
		* Local host information (address, name, port)
		* A security indicator

	Request is an abstract class; developers typically use HTTPRequest.

	FUTURE
		* Consider if the local host information should be moved up to Message.
		* Locales
		* Secure requests, authentication, etc.

	"""


	## Init ##

	def __init__(self):
		"""Initialize the request.

		Subclasses are responsible for invoking super
		and initializing self._time.

		"""
		Message.__init__(self)
		self._transaction = None


	## Access ##

	def time(self):
		return self._time

	def timeStamp(self):
		"""Return time() as a human readable string, useful for logging and debugging."""
		return asclocaltime(self.time())


	## Input ##

	def input(self):
		"""Return a file-style object that the contents can be read from.

		# @@ 2000-05-03 ce: This is bogus. Disregard for now.

		"""
		pass


	## Remote info ##

	# @@ 2000-05-07 ce: Do remoteAddress() and remoteName()
	# have to be implemented here or should it be a subclass responsibility?

	def remoteAddress(self):
		"""Get the remote address.

		Returns a string containing the Internet Protocol (IP) address
		of the client that sent the request.

		"""
		raise NotImplementedError

	def remoteName(self):
		"""Get the remote name.

		Returns the fully qualified name of the client that sent the request,
		or the IP address of the client if the name cannot be determined.

		"""
		raise NotImplementedError


	## Local info ##

	def localAddress(self):
		"""Get local address.

		Returns a string containing the Internet Protocol (IP) address
		of the local host (e.g., the server) that received the request.

		"""
		raise NotImplementedError

	def localName(self):
		"""Get local name.

		Returns the fully qualified name of the local host (e.g., the server)
		that received the request.

		"""
		return 'localhost'

	def localPort(self):
		"""Get local port.

		Returns the port of the local host (e.g., the server)
		that received the request.

		"""
		raise NotImplementedError


	## Security ##

	def isSecure(self):
		"""Check whether this is a secure channel.

		Returns true if request was made using a secure channel,
		such as HTTPS. This currently always returns false,
		since secure channels are not yet supported.

		"""
		return False


	## Transactions ##

	def responseClass(self):
		"""Get the corresponding response class."""
		raise NotImplementedError

	def setTransaction(self, trans):
		"""Set a transaction container."""
		self._transaction = trans

	def transaction(self):
		"""Get the transaction container."""
		return self._transaction


	## Cleanup ##

	def clearTransaction(self):
		del self._transaction
