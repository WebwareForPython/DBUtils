
"""Utility class for keeping track of the context.

	A utility class that holds information about the file we are parsing
	and the environment we are doing it in.

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

	This software is based in part on work done by the Jakarta group.

"""

from ParseEventHandler import *
import os


class PSPContext:
	"""PSPContext is an abstract base class for Context classes.

	Holds all the common stuff that various parts of the compilation
	will need access to. The items in this class will be used by both
	the compiler and the class generator.

	"""

	def __init__(self):
		raise NotImplementedError

	def getClassPath(self):
		raise NotImplementedError

	def getReader(self):
		raise NotImplementedError

	def getWriter(self):
		raise NotImplementedError

	def getOutputDirectory(self):
		"""Provide directory to dump PSP source file to."""
		raise NotImplementedError

	def getServletClassName(self):
		"""Return the class name of the servlet being generated."""
		raise NotImplementedError

	def getFullClassName(self):
		"""Return class name including package prefixes.

		Won't use this for now.
		"""
		raise NotImplementedError

	def getPythonFileName(self):
		"""the filename that we are generating to"""
		raise NotImplementedError

	def setPSPReader(self):
		"""Set the PSPReader for this context."""
		raise NotImplementedError

	def setServletWriter(self):
		"""Set the PSPWriter instance for this context."""
		raise NotImplementedError

	def setPythonFileName(self):
		"""Set the name of the .py file to generate."""
		raise NotImplementedError


class PSPCLContext(PSPContext):
	"""A context for command line compilation.

	Currently used for both cammand line and PSPServletEngine compilation.
	This class provides all the information necessary during the parsing
	and page generation steps of the PSP compilation process.

	"""

	def __init__(self, pspfile, trans=None):
		# self._transactrion = trans # I don't think I need this
		self._baseUri, self._pspfile = os.path.split(pspfile)
		self._fullpath = pspfile

	def getClassPath(self):
		raise NotImplementedError

	def getReader(self):
		"""Return the PSPReader object assigned to this context."""
		return self._pspReader

	def getServletWriter(self):
		"""Return the ServletWriter object assigned to this context"""
		return self._servletWriter

	def getOutputDirectory(self):
		"""Provide directory to dump PSP source file to.

		I am probably doing this in reverse order at the moment.
		I should start with this and get the python filename from it.

		"""
		return os.path.split(self._pyFileName)[0]

	def getServletClassName(self):
		"""Return the class name of the servlet being generated.

		"""
		return self._className

	def getFullClassName(self):
		"""Return class name including package prefixes.

		Won't use this for now.
		"""
		raise NotImplementedError

	def getPythonFileName(self):
		"""The filename that we are generating to."""
		return self._pyFileName

	def getPspFileName(self):
		return self._pspfile

	def getFullPspFileName(self):
		return self._fullpath

	def setPSPReader(self, reader):
		"""Set the PSPReader for this context."""
		self._pspReader = reader

	def setServletWriter(self, writer):
		"""Set the ServletWriter instance for this context."""
		self._servletWriter = writer

	def setPythonFileName(self, name):
		"""Sets the name of the .py file to generate."""
		self._pyFileName = name

	def setClassName(self , name):
		"""Set the class name to create."""
		self._className = name

	def resolveRelativeURI(self, uri):
		"""This is used mainly for including files.

		It simply returns the location relative to the base context
		directory, ie Examples/. If the filename has a leading /,
		it is assumed to be an absolute path.

		"""
		if os.path.isabs(uri):
			return uri
		else:
			return os.path.join(self._baseUri, uri)

	def getBaseUri(self):
		return self._baseUri
