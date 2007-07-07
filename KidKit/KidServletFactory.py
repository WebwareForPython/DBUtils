"""Servlet factory for Kid templates.

This allows you to run Kid template files directly from within Webware.
Compiled templates are cached either along with the templates or in the
KidKit subdirectory of the WebKit Cache directory.

Note that the Kid package itself is not part of Webware; you need to install
it separately (see http://www.kid-templating.org for more information).


CREDITS:

* Kid has been developed by Ryan Tomayko (rtomayko<at>gmail.com).
* KidKit was contributed by Winston Wolff (winstonw<at>stratolab.com).
  Based on the Cheetah servlet factory. No caching, fixed servlet hook.
* Improved version contributed by Christoph Zwerschke (cito<at>online.de).
  Based on the PSP servlet factory. Supports caching and servlet hooks.

"""

import os, sys, time
from glob import glob
from WebKit.ServletFactory import ServletFactory
from WebKit.Servlet import Servlet
from WebKit.Page import Page
defaultHook = Page.respond # the default hook for Kid servlets
defaultOutput = 'html' # the default Kid output method
defaultFormat = 'default' # the default Kid output format

from kid import load_template, output_methods
try: # output formatting exists in newer Kid versions only
	from kid.format import output_formats
except:
	output_formats = None
from kid.compiler import KidFile


def kidClass(module):
	"""Return a WebKit servlet class for a Kid template module."""

	try:
		hook = module.hook
	except AttributeError:
		hook = defaultHook
	assert type(hook) == type(defaultHook)
	ServletClass = hook.im_class
	assert issubclass(ServletClass, Servlet)
	writeMethod = hook.__name__
	try:
		output = module.output
	except:
		output = defaultOutput
	assert output in output_methods
	if output_formats is None:
		format = None
	else:
		try:
			format = module.format
		except:
			format = defaultFormat
		assert format in output_formats

	class KidServlet(ServletClass):
		"""The base class for a Kid servlet."""

		_module = module
		_template = module.Template()
		_output = output
		_format = format

		def writeTemplate(self, *args, **kwargs):
			self._template.servlet = self
			response = self._response
			fragment = response.size() > 0
			if format is None:
				self._template.write(self._response,
					fragment=fragment, output=output)
			else:
				self._template.write(self._response,
					fragment=fragment, output=output, format=format)

	setattr(KidServlet, writeMethod, KidServlet.writeTemplate)
	return KidServlet


class KidServletFactory(ServletFactory):
	"""Servlet factory for Kid templates."""

	def __init__(self, application):
		ServletFactory.__init__(self, application)
		setting = application.setting
		global defaultOutput # the default output method
		defaultOutput = setting('KidOutputMethod', defaultOutput)
		global defaultFormat # the default output format
		defaultFormat = setting('KidOutputFormat', defaultFormat)
		self._cacheTemplates = setting('CacheKidTemplates', True)
		self._useCache = setting('UseKidKitCache', False)
		if self._useCache:
			self._cacheSource = setting('CacheKidSource', True)
			self._clearCache = setting('ClearKidCacheOnStart', False)
			self._cacheDir = os.path.join(application._cacheDir, 'KidKit')
			if self._clearCache:
				self.clearFileCache()
		else:
			self._cacheSource = self._clearCache = False
			self._cacheDir = None
		t = ['_'] * 256
		from string import digits, letters
		for c in digits + letters:
			t[ord(c)] = c
		self._classNameTrans = ''.join(t)

	def uniqueness(self):
		return 'file'

	def extensions(self):
		return ['.kid']

	def flushCache(self):
		"""Clean out the cache of classes in memory and on disk."""
		ServletFactory.flushCache(self)
		if self._clearCache:
			self.clearFileCache()

	def clearFileCache(self):
		"""Clear class files stored on disk."""
		files = glob(os.path.join(self._cacheDir, '*.*'))
		map(os.remove, files)

	def computeClassName(self, pagename):
		"""Generate a (hopefully) unique class/file name for each Kid file.

		Argument: pagename: the path to the Kid template file
		Returns: a unique name for the class generated fom this Kid file

		"""
		# Compute class name by taking the path and substituting
		# underscores for all non-alphanumeric characters:
		return os.path.splitdrive(pagename)[1].translate(self._classNameTrans)

	def loadClass(self, transaction, path):
		"""Load servlet class for the given Kid template."""
		classname = self.computeClassName(path)
		if self._cacheTemplates and self._useCache:
			# Cache the compiled templates separately:
			mtime = os.path.getmtime(path)
			classfile = os.path.join(self._cacheDir, classname + ".py")
			if not self._cacheSource:
				classfile += __debug__ and 'c' or 'o'
			if not os.path.exists(classfile) \
					or os.path.getmtime(classfile) != mtime:
				kidFile = KidFile(path)
				if self._cacheSource:
					kidFile.dump_source(classfile)
				else:
					kidFile.dump_code(classfile)
				# Set the modification time of the compiled file
				# to be the same as the source file;
				# that's how we'll know if it needs to be recompiled:
				os.utime(classfile, (os.path.getatime(classfile), mtime))
			module = self.importAsPackage(transaction, classfile)
		else:
			# Let Kid care about the caching:
			module = load_template(path, cache=self._cacheTemplates)
		# Setting __orig_file__ here is already too late,
		module.__orig_file__ = path
		# so we need to tell ImportSpy explicitely about the file:
		self._imp.watchFile(path)
		theClass = kidClass(module)
		theClass._orig_file = path
		theClass.__name__ = self.computeClassName(path)
		return theClass
