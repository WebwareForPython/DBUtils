
"""BraceConverter.py

	Contributed 2000-09-04 by Dave Wallace (dwallace@delanet.com)

	Converts Brace-blocked Python into normal indented Python.
	Brace-blocked Python is non-indentation aware and blocks are delimited by ':{' and '}' pairs.

	Thus:
		for x in range(10) :{
			if x%2 :{ print x } else :{ print z }
		}

	Becomes (roughly, barring some spurious newlines):
		for x in range(10) :
			if x%2 :
				print x
			else :
				print z

	This implementation is fed a line at a time via parseLine(), outputs to
	a PSPServletWriter, and tracks the current quotation and block levels internally.

"""

import re
import sys


class BraceConverter:

	CSKIP = re.compile("(^[^\"'{}:#]+)")
	COLONBRACE = re.compile(":\s*{\s*([^\s].*)?$")

	def __init__(self):
		self.inquote = 0
		self.dictlevel = 0

	def parseLine(self, line, writer):
		"""Parse a line.

		The only public method of this class, call with subsequent lines
		and an instance of PSPServletWriter.

		"""
		self.line = line
		if self.inquote and self.line:
			self.skipquote(writer)
		self.line = self.line.lstrip()
		if not self.line:
			writer.printChars('\n')
			return
		writer.printIndent()
		while self.line:
			while self.inquote and self.line:
				self.skipquote(writer)
			match = self.CSKIP.search(self.line)
			if match:
				writer.printChars(self.line[:match.end(1)])
				self.line = self.line[match.end(1):]
			else:
				ch = self.line[0]
				if ch == "'":
					self.handleQuote("'", writer)
					self.skipquote(writer)
				elif ch == '"':
					self.handleQuote('"', writer)
					self.skipquote(writer)
				elif ch == '{':
					self.openBrace(writer)
				elif ch == '}':
					self.closeBrace(writer)
				elif ch == ':':
					self.openBlock(writer)
				elif ch == '#':
					writer.printChars(self.line)
					self.line = ""
				else:
					# should never get here
					raise Exception()
		else:
			writer.printChars('\n')

	def openBlock(self, writer):
		"""Open a new block."""
		match = self.COLONBRACE.match(self.line)
		if match and not self.dictlevel:
			writer.printChars(":")
			writer.pushIndent()
			if match.group(1):
				# text follows :{, if its a comment leave it on the same line
				# else start a new line and leave the text for processing
				if match.group(1)[0] == '#':
					writer.printChars(" " + match.group(1))
					self.line = ""
				else:
					writer.printChars('\n')
					writer.printIndent()
					self.line = match.group(1)
			else:
				self.line = ""
		else:
			writer.printChars(":")
			self.line = self.line[1:]

	def openBrace(self, writer):
		"""Open brace encountered."""
		writer.printChars("{")
		self.line = self.line[1:]
		self.dictlevel += 1

	def closeBrace(self, writer):
		"""Close brace encountered."""
		if self.dictlevel:
			writer.printChars("}")
			self.line = self.line[1:]
			self.dictlevel -= 1
		else:
			writer.popIndent()
			self.line = self.line[1:].lstrip()
			if self.line:
				writer.printChars('\n')
				writer.printIndent()

	def skipquote(self, writer):
		"""Skip to end of quote.

		Skip over all chars until the line is exhausted
		or the current non-escaped quote sequence is encountered.

		"""
		pos = self.line.find(self.quotechars)
		if pos == -1:
			writer.printChars(self.line)
			self.line = ""
		elif (pos > 0) and self.line[pos-1] == '\\':
			pos += 1
			writer.printChars(self.line[:pos])
			self.line = self.line[pos:]
			self.skipquote(writer)
		else:
			pos += len(self.quotechars)
			writer.printChars(self.line[:pos])
			self.line = self.line[pos:]
			self.inquote = 0

	def handleQuote(self, quote, writer):
		"Check and handle if current pos is a single or triple quote."""
		self.inquote = 1
		triple = quote*3
		if self.line[0:3] == triple:
			self.quotechars = triple
			writer.printChars(triple)
			self.line = self.line[3:]
		else:
			self.quotechars = quote
			writer.printChars(quote)
			self.line = self.line[1:]


## Testing ##

if __name__ == "__main__":
	from ServletWriter import ServletWriter


	class DummyWriter(ServletWriter):
		"""For stand alone testing."""

		def __init__(self):
			self._filehandle = sys.stdout
			self._tabcnt = 0
			self._blockcount = 0 # a hack to handle nested blocks of Python code
			self._indentSpaces = ServletWriter._spaces
			self._useTabs = 1
			self._useBraces = 0
			self._indent = '\t'
			self._userIndent = ServletWriter._emptyString

	test = r'''
	for x in range(10): { q = {
	'test': x
	}
	print x
	}

	for x in range(10): { q= {'test': x}; print x} else: { print "\"done\"" #""}{
	x = { 'test1': {'sub2': {'subsub1': 2}} # yee ha
	}
	} print "all done"

	'''
	p = BraceConverter()
	dw = DummyWriter()
	for line in test.split('\n'):
		p.parseLine(line, dw)
