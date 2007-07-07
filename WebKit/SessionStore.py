from Common import *


class SessionStore(Object):
	"""A general session store.

	SessionStores are dictionary-like objects used by Application to
	store session state. This class is abstract and it's up to the
	concrete subclass to implement several key methods that determine
	how sessions are stored (such as in memory, on disk or in a
	database).

	Subclasses often encode sessions for storage somewhere. In light
	of that, this class also defines methods encoder(), decoder() and
	setEncoderDecoder(). The encoder and decoder default to the load()
	and dump() functions of the cPickle or pickle module. However,
	using the setEncoderDecoder() method, you can use the functions
	from marshal (if appropriate) or your own encoding scheme.
	Subclasses should use encoder() and decoder() (and not
	pickle.load() and pickle.dump()).

	Subclasses may rely on the attribute self._app to point to the
	application.

	Subclasses should be named SessionFooStore since Application
	expects "Foo" to appear for the "SessionStore" setting and
	automatically prepends Session and appends Store. Currently, you
	will also need to add another import statement in Application.py.
	Search for SessionStore and you'll find the place.

	TO DO

	* Should there be a check-in/check-out strategy for sessions to
	  prevent concurrent requests on the same session? If so, that can
	  probably be done at this level (as opposed to pushing the burden
	  on various subclasses).

	"""


	## Init ##

	def __init__(self, app):
		""" Subclasses must invoke super. """
		Object.__init__(self)
		self._app = app
		try:
			import cPickle as pickle
		except ImportError:
			import pickle
		if hasattr(pickle, 'HIGHEST_PROTOCOL'):
			def dumpWithHighestProtocol(obj, f,
					proto=pickle.HIGHEST_PROTOCOL, dump=pickle.dump):
				return dump(obj, f, proto)
			self._encoder = dumpWithHighestProtocol
		else:
			self._encoder = pickle.dump
		self._decoder = pickle.load


	## Access ##

	def application(self):
		return self._app


	## Dictionary-style access ##

	def __len__(self):
		raise AbstractError, self.__class__

	def __getitem__(self, key):
		raise AbstractError, self.__class__

	def __setitem__(self, key, item):
		raise AbstractError, self.__class__

	def __delitem__(self, key):
		"""Delete an item.

		Subclasses are responsible for expiring the session as well.
		Something along the lines of:
			sess = self[key]
			if not sess.isExpired():
				sess.expiring()

		"""
		raise AbstractError, self.__class__

	def has_key(self, key):
		raise AbstractError, self.__class__

	def keys(self):
		raise AbstractError, self.__class__

	def clear(self):
		raise AbstractError, self.__class__

	def setdefault(self, key, default):
		raise AbstractError, self.__class__


	## Application support ##

	def storeSession(self, session):
		raise AbstractError, self.__class__

	def storeAllSessions(self):
		raise AbstractError, self.__class__

	def cleanStaleSessions(self, task=None):
		"""Clean stale sessions.

		Called by the Application to tell this store to clean out all
		sessions that have exceeded their lifetime.

		"""
		curTime = time.time()
		for key in self.keys():
			try:
				sess = self[key]
			except KeyError:
				pass # session was already deleted by some other thread
			else:
				if curTime - sess.lastAccessTime() >= sess.timeout() \
						or sess.timeout() == 0:
					try:
						del self[key]
					except KeyError:
						pass # already deleted by some other thread


	## Convenience methods ##

	def items(self):
		itms = []
		for k in self.keys():
			try:
				itms.append((k, self[k]))
			except KeyError:
				# since we aren't using a lock here, some keys
				# could be already deleted again during this loop
				pass
		return itms

	def values(self):
		vals = []
		for k in self.keys():
			try:
				vals.append(self[k])
			except KeyError:
				pass
		return vals

	def get(self, key, default=None):
		try:
			return self[key]
		except KeyError:
			return default


	## Encoder/decoder ##

	def encoder(self):
		return self._encoder

	def decoder(self):
		return self._decoder

	def setEncoderDecoder(self, encoder, decoder):
		self._encoder = encoder
		self._decoder = decoder


	## As a string ##

	def __repr__(self):
		d = {}
		for key, value in self.items():
			d[key] = value
		return repr(d)
