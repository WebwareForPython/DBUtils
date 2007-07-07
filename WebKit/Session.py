import re

from Common import *
from MiscUtils.Funcs import uniqueId


class SessionError(Exception):
	pass


class Session(Object):
	"""Implementation of client sessions.

	All methods that deal with time stamps, such as creationTime(),
	treat time as the number of seconds since January 1, 1970.

	Session identifiers are stored in cookies. Therefore, clients
	must have cookies enabled.

	Unlike Response and Request, which have HTTP subclass versions
	(e.g., HTTPRequest and HTTPResponse respectively), Session does
	not. This is because there is nothing protocol specific in
	Session. (Is that true considering cookies? @@ 2000-04-09 ce)
	2000-04-27 ce: With regards to ids/cookies, maybe the notion
	of a session id should be part of the interface of a Request.

	Note that the session id should be a string that is valid
	as part of a filename. This is currently true, and should
	be maintained if the session id generation technique is
	modified. Session ids can be used in filenames.

	FUTURE

		* invalidate()
		* Sessions don't actually time out and invalidate themselves.
		* Should this be called 'HTTPSession'?
		* Should "numTransactions" be exposed as a method? Should it
		  be common to all transaction objects that do the
		  awake()-respond()-sleep() thing? And should there be an
		  abstract super class to codify that?
	"""


	## Init ##

	def __init__(self, trans, identifier=None):
		Object.__init__(self)

		self._lastAccessTime = self._creationTime = time.time()
		self._isExpired = False
		self._numTrans = 0
		self._values = {}
		app = trans.application()
		self._timeout = app.sessionTimeout(trans)
		self._prefix = app.sessionPrefix(trans)
		self._sessionName = app.sessionName(trans)

		if identifier:
			if re.search(r'[^\w\.\-]', identifier) is not None:
				raise SessionError, "Illegal characters in session identifier"
			if len(identifier) > 80:
				raise SessionError, "Session identifier too long"
			self._identifier = identifier
		else:
			attempts = 0
			while attempts < 10000:
				self._identifier = self._prefix + ''.join(
					map(lambda x: '%02d' % x,
						time.localtime(time.time())[:6])) + '-' + uniqueId(self)
				if not app.hasSession(self._identifier):
					break
				attempts += 1
			else:
				raise SessionError, \
					"Can't create valid session id after %d attempts." % attempts

		if app.setting('Debug')['Sessions']:
			print '>> [session] Created session, ' \
				'timeout = %s, id = %s, self = %s' \
				% (self._timeout, self._identifier, self)


	## Access ##

	def creationTime(self):
		"""Return the time when this session was created."""
		return self._creationTime

	def lastAccessTime(self):
		"""Get last access time.

		Returns the last time the user accessed the session through
		interaction. This attribute is updated in awake(), which is
		invoked at the beginning of a transaction.

		"""
		return self._lastAccessTime

	def identifier(self):
		"""Return a string that uniquely identifies the session.

		This method will create the identifier if needed.

		"""
		return self._identifier

	def isExpired(self):
		"""Check whether the session has been previously expired.

		See also: expiring()

		"""
		return getattr(self, '_isExpired', False) or self._timeout == 0

	def isNew(self):
		"""Check whether the session is new."""
		return self._numTrans < 2

	def timeout(self):
		"""Return the timeout for this session in seconds."""
		return self._timeout

	def setTimeout(self, timeout):
		"""Set the timeout on this session in seconds."""
		self._timeout = timeout


	## Invalidate ##

	def invalidate(self):
		"""Invalidate the session.

		It will be discarded the next time it is accessed.

		"""
		self._lastAccessTime = 0
		self._values = {}
		self._timeout = 0


	## Values ##

	def value(self, name, default=NoDefault):
		if default is NoDefault:
			return self._values[name]
		else:
			return self._values.get(name, default)

	def hasValue(self, name):
		return self._values.has_key(name)

	def setValue(self, name, value):
		self._values[name] = value

	def delValue(self, name):
		del self._values[name]

	def values(self):
		return self._values

	def __getitem__(self, name):
		return self.value(name)

	def __setitem__(self, name, value):
		self.setValue(name, value)

	def __delitem__(self, name):
		self.delValue(name)

	def __contains__(self, name):
		return self.hasValue(name)


	## Transactions ##

	def awake(self, trans):
		"""Let the session awake.

		Invoked during the beginning of a transaction, giving a Session an
		opportunity to perform any required setup. The default implementation
		updates the 'lastAccessTime'.

		"""
		self._lastAccessTime = time.time()
		self._numTrans += 1

	def respond(self, trans):
		"""Let the session respond to a request.

		The default implementation does nothing, but could do something
		in the future. Subclasses should invoke super.

		"""
		pass

	def sleep(self, trans):
		"""Let the session sleep again.

		Invoked during the ending of a transaction, giving a Session an
		opportunity to perform any required shutdown. The default
		implementation does nothing, but could do something in the future.
		Subclasses should invoke super.

		"""
		pass

	def expiring(self):
		"""Let the session expire.

		Called when session is expired by the application.
		Subclasses should invoke super.
		Session store __delitem__()s should invoke if not isExpired().

		"""
		self._isExpired = True


	## Utility ##

	def sessionEncode(self, url):
		"""Encode the session ID as a parameter to a url."""
		import urlparse
		url = list(urlparse.urlparse(url)) # make a list
		if url[4]:
			url[4] += '&'
		url[4] += '%s=%s' % (self._sessionName, self.identifier())
		url = urlparse.urlunparse(url)
		return url


	## Exception reports ##

	_exceptionReportAttrNames = \
		'lastAccessTime isExpired numTrans timeout values'.split()

	def writeExceptionReport(self, handler):
		handler.writeTitle(self.__class__.__name__)
		handler.writeAttrs(self, self._exceptionReportAttrNames)
