import os, mimetypes

from ServletFactory import ServletFactory
import HTTPExceptions
from HTTPServlet import HTTPServlet
from MiscUtils.Configurable import Configurable

debug = 0

try:
	mimetypes.common_types
except AttributeError: # fallback for Python < 2.2
	if not mimetypes.types_map.has_key('.css'):
		mimetypes.types_map['.css'] = 'text/css'
	def guess_type(url, strict=1):
		return mimetypes.guess_type(url)
else:
	guess_type = mimetypes.guess_type


class UnknownFileTypeServletFactory(ServletFactory):
	"""The servlet factory for unknown file types.

	I.e. all files other than .py, .psp, .kid and the other types we support.

	"""

	def uniqueness(self):
		return 'file'

	def extensions(self):
		return ['.*']

	def servletForTransaction(self, transaction):
		return UnknownFileTypeServlet(transaction.application())

	def flushCache(self):
		pass


fileCache = {}
	# A cache of the files served up by UnknownFileTypeServlet cached by
	# absolute, server side path. Each content is another dictionary with keys:
	# content, mimeType, mimeEncoding.
	# Previously, this content was stored directly in the attributes of the
	# UnknownFileTypeServlets, but with that approach subclasses cannot
	# dynamically serve content from different locations.


class UnknownFileTypeServlet(HTTPServlet, Configurable):
	"""Servlet for unknown file types.

	Normally this class is just a "private" utility class for WebKit's
	purposes. However, you may find it useful to subclass on occasion,
	such as when the server side file path is determined by something
	other than a direct correlation to the URL. Here is such an example:


	from WebKit.AppServer import globalAppServer
	from WebKit.UnknownFileTypeServlet import UnknownFileTypeServlet
	import os

	class Image(UnknownFileTypeServlet):

		imageDir = '/var/images'

		def filename(self, trans):
			filename = trans.request().field('i')
			filename = os.path.join(self.imageDir, filename)
			return filename

	"""


	## Candidates for subclass overrides ##

	def filename(self, trans):
		"""Return the filename to be served.

		A subclass could override this in order to serve files from other
		disk locations based on some logic.

		"""
		filename = getattr(self, '_serverSideFilename', None)
		if filename is None:
			filename = trans.request().serverSidePath()
			self._serverSideFilename = filename # cache it
		return filename

	def shouldCacheContent(self):
		"""Return whether the content should be cached or not.

		Returns a boolean that controls whether or not the content served
		through this servlet is cached. The default behavior is to return
		the CacheContent setting. Subclasses may override to always True
		or False, or incorporate some other logic.

		"""
		return self.setting('CacheContent')


	## Init et al ##

	def __init__(self, application=None):
		HTTPServlet.__init__(self)
		Configurable.__init__(self)
		if application is None:
			from AppServer import globalAppServer
			application = globalAppServer.application()
			assert application is not None
		self._application = application

	def defaultConfig(self):
		"""Get the default config.

		Taken from Application's 'UnknownFileTypes' default setting.

		"""
		return self._application.defaultConfig()['UnknownFileTypes']

	def userConfig(self):
		"""Get the user config.

		Taken from Application's 'UnknownFileTypes' user setting.

		"""
		return self._application.userConfig().get('UnknownFileTypes', {})

	def configFilename(self):
		return self._application.configFilename()

	def canBeReused(self):
		return self.setting('ReuseServlets')

	def validTechniques(self):
		return ['serveContent', 'redirectSansAdapter']

	def respondToGet(self, trans):
		"""Respond to GET request.

		Responds to the transaction by invoking self.foo() for foo is
		specified by the 'Technique' setting.

		"""
		technique = self.setting('Technique')
		assert technique in self.validTechniques(), 'technique = %s' % technique
		method = getattr(self, technique)
		method(trans)

	respondToHead = respondToGet

	def respondToPost(self, trans):
		"""Respond to POST request.

		Invoke self.respondToGet().

		Since posts are usually accompanied by data, this might not be
		the best policy. However, a POST would most likely be for a CGI,
		which currently no one is mixing in with their WebKit-based web sites.

		"""
		# @@ 2001-01-25 ce: See doc string for why this might be a bad idea.
		self.respondToGet(trans)

	def redirectSansAdapter(self, trans):
		"""Redirect to web server.

		Sends a redirect to a URL that doesn't contain the adapter name.
		Under the right configuration, this will cause the web server to
		then be responsible for the URL rather than the app server.
		This has only been test with "*.[f]cgi" adapters.
		Keep in mind that links off the target page will *not* include
		the adapter in the URL.

		"""
		# @@ 2000-05-08 ce: the following is horribly CGI specific and hacky
		env = trans.request()._environ
		# @@ 2001-01-25 ce: isn't there a func in WebUtils to get script name?
		# because some servers are different?
		newURL = os.path.split(env['SCRIPT_NAME'])[0] + env['PATH_INFO']
		newURL = newURL.replace('//', '/') # hacky
		trans.response().sendRedirect(newURL)

	def lastModified(self, trans):
		try:
			return os.path.getmtime(self.filename(trans))
		except OSError:
			return None

	def serveContent(self, trans):
		response = trans.response()

		maxCacheContentSize = self.setting('MaxCacheContentSize')
		readBufferSize = self.setting('ReadBufferSize')

		# start sending automatically
		response.streamOut().setAutoCommit()

		filename = self.filename(trans)
		try:
			f = open(filename, 'rb')
		except IOError:
			raise HTTPExceptions.HTTPNotFound

		stat = os.fstat(f.fileno())
		fileSize, mtime = stat[6], stat[8]

		if debug:
			print '>> UnknownFileType.serveContent()'
			print '>> filename =', filename
			print '>> size=', fileSize
		file = fileCache.get(filename, None)
		if file is not None and mtime != file['mtime']:
			# Cache is out of date; clear it.
			if debug:
				print '>> changed, clearing cache'
			del fileCache[filename]
			file = None
		if file is None:
			if debug:
				print '>> not found in cache'
			fileType = guess_type(filename, 0)
			mimeType = fileType[0]
			mimeEncoding = fileType[1]
			if mimeType is None:
				mimeType = 'application/octet-stream'
		else:
			mimeType, mimeEncoding = file['mimeType'], file['mimeEncoding']
		response.setHeader('Content-type', mimeType)
		response.setHeader('Content-Length', str(fileSize))
		if mimeEncoding:
			response.setHeader('Content-encoding', mimeEncoding)
		if trans.request().method() == 'HEAD':
			f.close()
			return
		if file is None and self.setting('ReuseServlets') \
				and self.shouldCacheContent() \
				and fileSize < maxCacheContentSize:
			if debug:
				print '>> caching'
			file = {
				'content':      f.read(),
				'mimeType':     mimeType,
				'mimeEncoding': mimeEncoding,
				'mtime':        mtime,
				'size':         fileSize,
				'filename':     filename,
			}
			fileCache[filename] = file
		if file is not None:
			if debug:
				print '>> sending content from cache'
			response.write(file['content'])
		else: # too big or not supposed to cache
			if debug:
				print '>> sending directly'
			numBytesSent = 0
			while numBytesSent < fileSize:
				data = f.read(min(fileSize-numBytesSent, readBufferSize))
				if data == '':
					break # unlikely, but safety first
				response.write(data)
				numBytesSent += len(data)
		f.close()
