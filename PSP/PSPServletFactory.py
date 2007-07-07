
"""This module handles requests from the application for PSP pages.

	(c) Copyright by Jay Love, 2000 (mailto:jsliv@jslove.org)

	Permission to use, copy, modify, and distribute this software and its
	documentation for any purpose and without fee or royalty is hereby granted,
	provided that the above copyright notice appear in all copies and that
	both that copyright notice and this permission notice appear in
	supporting documentation or portions thereof, including modifications,
	that you make.

	THE AUTHORS DISCLAIM ALL WARRANTIES WITH REGARD TO
	THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
	FITNESS, IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL,
	INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING
	FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
	NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
	WITH THE USE OR PERFORMANCE OF THIS SOFTWARE !

"""

import os, sys, time
from glob import glob
from WebKit.ServletFactory import ServletFactory
from PSP import Context, PSPCompiler


class PSPServletFactory(ServletFactory):
	"""Servlet Factory for PSP files.

	Very sloppy. Need to come back and do a serious cleanup.

	"""

	def __init__(self, application):
		ServletFactory.__init__(self, application)
		self._cacheDir = os.path.join(application._cacheDir, 'PSP')
		sys.path.append(self._cacheDir)
		self._cacheClassFiles = self._cacheClasses
		t = ['_'] * 256
		from string import digits, letters
		for c in digits + letters:
			t[ord(c)] = c
		self._classNameTrans = ''.join(t)
		if application.setting('ClearPSPCacheOnStart', 0):
			self.clearFileCache()

	def uniqueness(self):
		return 'file'

	def extensions(self):
		return ['.psp']

	def flushCache(self):
		"""Clean out the cache of classes in memory and on disk."""
		ServletFactory.flushCache(self)
		self.clearFileCache()

	def clearFileCache(self):
		"""Clear class files stored on disk."""
		files = glob(os.path.join(self._cacheDir, '*.*'))
		map(os.remove, files)

	def computeClassName(self, pagename):
		"""Generates a (hopefully) unique class/file name for each PSP file.

		Argument: pagename: the path to the PSP source file
		Returns: a unique name for the class generated fom this PSP source file

		"""
		# Compute class name by taking the path and substituting
		# underscores for all non-alphanumeric characters:
		return os.path.splitdrive(pagename)[1].translate(self._classNameTrans)

	def loadClassFromFile(self, transaction, filename, classname):
		"""Create an actual class instance.

		The module containing the class is imported as though it were a
		module within the context's package (and appropriate subpackages).

		"""
		module = self.importAsPackage(transaction, filename)
		assert module.__dict__.has_key(classname), \
			'Cannot find expected class named %s in %s.' \
				% (repr(classname), repr(filename))
		theClass = getattr(module, classname)
		return theClass

	def loadClass(self, transaction, path):
		classname = self.computeClassName(path)
		classfile = os.path.join(self._cacheDir, classname + ".py")
		mtime = os.path.getmtime(path)
		if not os.path.exists(classfile) \
				or os.path.getmtime(classfile) != mtime:
			context = Context.PSPCLContext(path, transaction)
			context.setClassName(classname)
			context.setPythonFileName(classfile)
			clc = PSPCompiler.Compiler(context)
			clc.compile()
			# Set the modification time of the compiled file
			# to be the same as the source file;
			# that's how we'll know if it needs to be recompiled:
			os.utime(classfile, (os.path.getatime(classfile), mtime))
		theClass = self.loadClassFromFile(transaction, classfile, classname)
		return theClass
