
"""This module holds the actual file writer class.

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

import os, sys, tempfile
from MiscUtils.Funcs import mkstemp
from Context import *


class ServletWriter:
	"""This file creates the servlet source code.

	Well, it writes it out to a file at least.

	"""

	_tab = '\t'
	_spaces = '    ' # 4 spaces
	_emptyString = ''

	def __init__(self, ctxt):
		self._pyfilename = ctxt.getPythonFileName()
		fd, self._temp = mkstemp('tmp', dir=os.path.dirname(self._pyfilename))
		self._filehandle = os.fdopen(fd, 'w')
		self._tabcnt = 0
		self._blockcount = 0 # a hack to handle nested blocks of python code
		self._indentSpaces = self._spaces
		self._useTabs = 1
		self._useBraces = 0
		self._indent = '\t'
		self._userIndent = self._emptyString

	def setIndentSpaces(self, amt):
		self._indentSpaces = ' '*amt
		self.setIndention()

	def setIndention(self):
		if self._useTabs:
			self._indent = '\t'
		else:
			self._indent = self._indentSpaces # ' '*self._indentSpaces

	def setIndentType(self, type):
		if type == "tabs":
			self._useTabs = 1
			self.setIndention()
		elif type == "spaces":
			self._useTabs = 0
			self.setIndention()
		elif type == "braces":
			self._useTabs = 0
			self._useBraces = 1
			self.setIndention()

	def close(self):
		self._filehandle.close()
		if os.path.exists(self._pyfilename):
			os.remove(self._pyfilename)
		try:
				os.rename(self._temp, self._pyfilename)
		except OSError:
			# The operation may fail on some Unix flavors
			# if the files are on different filesystems.
			# In this case, we try to move the files manually:
			f = open(self._pyfilename, 'wb')
			try:
				f.write(open(self._temp, 'rb').read())
			finally:
				f.close()
			os.remove(self._temp)

	def pushIndent(self):
		"""this is very key, have to think more about it"""
		self._tabcnt += 1

	def popIndent(self):
		if self._tabcnt > 0:
			self._tabcnt -= 1

	def printComment(self, start, stop, chars):
		if start and stop:
			self.println('## from ' + str(start))
			self.println('## from ' + str(stop))
		if chars:
			sp = chars.split('\n')
			for i in sp:
				self._filehandle.write(self.indent(''))
				self._filehandle.write('##')
				self._filehandle.write(i)

	def quoteString(self, s):
		"""Escape the string."""
		if s is None:
			return 'None'
			# this probably won't work, I'll be back for this
		return 'r'+s

	def indent(self, st):
		"""Indent the string."""
		# added userIndent 6/18/00
		if self._tabcnt > 0:
			return self._userIndent + self._indent*self._tabcnt + st
		return st

	def println(self, line=None):
		"""Print with indentation and a newline if none supplied."""
		if line:
			self._filehandle.write(self.indent(line))
		else:
			self._filehandle.write(self.indent('\n'))
		if line and line[:-1] != '\n':
			self._filehandle.write('\n')

	def printChars(self, st):
		"""Just prints what its given."""
		self._filehandle.write(st)

	def printMultiLn(self, st):
		raise 'NotImplemented Error'

	def printList(self, strlist):
		"""Prints a list of strings with indentation and a newline."""
		for i in strlist:
			self.printChars(self.indent(i))
			self.printChars('\n')

	def printIndent(self):
		"""Just prints tabs."""
		self.printChars(self.indent(''))
