"""The PSP parser.

	This module handles the actual reading of the characters in the source
	PSP file and checking it for valid psp tokens. When it finds one,
	it calls ParseEventHandler with the characters it found.

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

from Generators import *

try:
	from cStringIO import StringIO
except:
	from StringIO import StringIO


class PSPParser:
	"""The main PSP parser class.

	The PSPParser class does the actual sniffing through the input file
	looking for anything we're interested in. Basically, it starts by
	looking at the code looking for a '<' symbol. It looks at the code by
	working with a PSPReader object, which handle the current location in
	the code. When it finds one, it calls a list of functions, the xxxChecks,
	asking each if it recognizes the characters as its kind of input.
	When the check functions look at the characters, if they want it,
	they go ahead and gobble it up and set up to create it in the servlet
	when the time comes.  When they return, they return true if they accept
	the character, and the PSPReader object cursor is positioned past the
	end of the block that the check function accepted.

	"""

	checklist = []

	def __init__(self, ctxt):
		self._reader = ctxt.getReader()
		self._writer = ctxt.getServletWriter()
		self._handler = None
		self.cout = StringIO() # This is where we dump straight HTML code that none of the checks want
		self.tmplStart = 0 # marks the start of HTML code
		self.tmplStop = 0 #marks the end of HTML code
		self.currentFile = self._reader.Mark().getFile()

	def setEventHandler(self, handler):
		"""Set the handler this parser will use when it finds PSP code."""
		self._handler = handler

	def flushCharData(self, start, stop):
		"""Dump everything to the char data handler.

		Dump all the HTML that we've accumulated over to the character data
		handler in the event handler object.

		"""
		data = self.cout.getvalue()
		self.cout.close()
		if len(data) > 0: # make sure there's something there
			self._handler.handleCharData(start, stop, data)
		self.cout = StringIO()

	def commentCheck(self, handler, reader):
		"""Comments just get eaten."""
		OPEN_COMMENT = '<%--'
		CLOSE_COMMENT = '--%>'
		if reader.Matches(OPEN_COMMENT):
			reader.Advance(len(OPEN_COMMENT))
			start = reader.Mark()
			stop = reader.skipUntil(CLOSE_COMMENT)
			if stop is None:
				raise 'ParseException'
			self.flushCharData(self.tmplStart, self.tmplStop)
			return 1
		return 0

	checklist.append(commentCheck) # add this checker to the list that the parse function will call

	def checkExpression(self, handler, reader):
		"""Look for "expressions" and handle them"""
		OPEN_EXPR = '<%='
		CLOSE_EXPR = '%>'
		end_open = None
		attrs = None
		if not reader.Matches(OPEN_EXPR):
			return 0
		reader.Advance(len(OPEN_EXPR)) # eat the opening tag
		if end_open is not None:
			attrs = reader.parseTagAttributes()
			reader.skipSpaces()
			if not reader.matches(end_open):
				raise 'ParseException'
			reader.Advance(len(end_open))
			reader.skipSpaces()
		# below not implemented
		# PSPUtil.checkAttrs('Expression',attrs,validAttrs)
		reader.peekChar()
		reader.skipSpaces()
		start = reader.Mark()
		stop = reader.skipUntil(CLOSE_EXPR)
		if stop is None:
			raise 'ParserException'
		handler.setTemplateInfo(self.tmplStart, self.tmplStop)
		handler.handleExpression(start, stop, attrs)
		return 1

	checklist.append(checkExpression)

	def checkDirective(self, handler, reader):
		"""Check for directives. I support two right now, page and include."""
		validDirectives = ['page', 'include']
		OPEN_DIRECTIVE = r'<%@'
		CLOSE_DIRECTIVE = r'%>'
		if reader.Matches(OPEN_DIRECTIVE):
			opening = OPEN_DIRECTIVE
			close = CLOSE_DIRECTIVE
		else:
			return 0
		start = reader.Mark()
		reader.Advance(len(OPEN_DIRECTIVE))
		match = None
		reader.skipSpaces()
		for i in validDirectives:
			if reader.Matches(i):
				match = i
				break
		if match is None:
			raise 'Invalid Directive'
		reader.Advance(len(match))
		# parse the directive attr:val pair dictionary
		attrs = reader.parseTagAttributes()
		# not checking for validity yet
		# if match == 'page':
		# 	PSPUtils.checkAttributes('Page Directive', attrs, pageDvalidAttrs)
		# elif match == 'include':
		# 	PSPUtils.checkAttributes('Include Directive', attrs, includeDvalidAttrs)
		# elif match == 'taglib':
		# 	raise 'Not Implemented Error'
		# match close
		reader.skipSpaces() #skip to where we expect a close tag
		if not reader.Matches(close):
			raise 'Unterminated directive error'
		else:
			reader.Advance(len(close)) #advance past it
		stop = reader.Mark()
		handler.setTemplateInfo(self.tmplStart, self.tmplStop)
		handler.handleDirective(match, start, stop, attrs)
		return 1

	checklist.append(checkDirective)

	def checkEndBlock(self, handler, reader):
		OPEN_SCRIPT = '<%'
		CLOSE_SCRIPT = '%>'
		CLOSE_SCRIPT2 = '$%>'
		CENTER_SCRIPT = 'end'
		start = reader.Mark()
		if reader.Matches(OPEN_SCRIPT):
			reader.Advance(len(OPEN_SCRIPT))
			reader.skipSpaces()
			if reader.Matches(CENTER_SCRIPT):
				reader.Advance(len(CENTER_SCRIPT))
				reader.skipSpaces()
				if reader.Matches(CLOSE_SCRIPT):
					reader.Advance(len(CLOSE_SCRIPT))
					handler.setTemplateInfo(self.tmplStart, self.tmplStop)
					handler.handleEndBlock()
					return 1
				if reader.Matches(CLOSE_SCRIPT2):
					reader.Advance(len(CLOSE_SCRIPT2))
					handler.setTemplateInfo(self.tmplStart, self.tmplStop)
					handler.handleEndBlock()
					print ">>>>Putting a $ at the end of an end tag does nothing, I Say"
					return 1
		# that wasn't it
		reader.reset(start)
		return 0

	checklist.append(checkEndBlock)

	def checkScript(self, handler, reader):
		"""The main thing we're after. Check for embedded scripts."""
		OPEN_SCRIPT = '<%'
		CLOSE_SCRIPT = '%>'
		attrs = None
		end_open = None
		if reader.Matches(OPEN_SCRIPT):
			open = OPEN_SCRIPT
			close = CLOSE_SCRIPT
		else:
			return 0
		reader.Advance(len(open))# Matches advances it
		if end_open is not None:
			attrs = reader.parseTagAttributes()
			reader.skipSpaces()
			if not reader.Matches(end_open):
				raise 'Unterminated script'
			reader.Advance(len(end_open))
			reader.skipSpaces()
			PSPUtils.checkAttributes('Script', attrs, ValidAttributes)
		# reader.skipSpaces() # don't skip as spaces may be significant, leave this for the generator
		start = reader.Mark()
		try:
			stop = reader.skipUntil(close)
		except EOFError:
			raise EOFError("Reached EOF while looking for ending script tag")
		if stop is None:
			raise 'Unterminated Script'
		handler.setTemplateInfo(self.tmplStart, self.tmplStop)
		handler.handleScript(start, stop, attrs)
		return 1

	checklist.append(checkScript)

	def checkScriptFile(self, handler, reader):
		"""Check for file level code.

		Check for Python code that should go in the beginning of the generated module.

		<psp:file>
			import xyz
			print 'hi Mome!'
			def foo(): return 'foo'
		</psp:file>

		"""
		OPEN_SCRIPT = '<psp:file>'
		CLOSE_SCRIPT = '</psp:file>'
		attrs = None
		if reader.Matches(OPEN_SCRIPT):
			reader.Advance(len(OPEN_SCRIPT))
			start = reader.Mark()
			try:
				stop = reader.skipUntil(CLOSE_SCRIPT)
				if stop is None:
					raise 'Unterminated Script is %s block' % OPEN_SCRIPT
			except EOFError:
				raise EOFError("Reached EOF while looking for ending script tag (%s)" % CLOSE_SCRIPT)
			handler.setTemplateInfo(self.tmplStart, self.tmplStop)
			handler.handleScriptFile(start, stop, attrs)
			return 1
		return 0

	checklist.append(checkScriptFile)

	def checkScriptClass(self, handler, reader):
		"""Check for class level code.

		Check for Python code that should go in the class definition.

		<psp:class>
			def foo(self):
				return self.dosomething()
		</psp:class>

		"""
		OPEN_SCRIPT = '<psp:class>'
		CLOSE_SCRIPT = '</psp:class>'
		attrs = None
		if reader.Matches(OPEN_SCRIPT):
			reader.Advance(len(OPEN_SCRIPT))
			start = reader.Mark()
			try:
				stop = reader.skipUntil(CLOSE_SCRIPT)
				if stop is None:
					raise 'Unterminated Script is %s block' % OPEN_SCRIPT
			except EOFError:
				raise EOFError("Reached EOF while looking for ending script tag (%s)" % CLOSE_SCRIPT)
			handler.setTemplateInfo(self.tmplStart, self.tmplStop)
			handler.handleScriptClass(start, stop, attrs)
			return 1
		return 0

	checklist.append(checkScriptClass)

	def checkMethod(self, handler, reader):
		"""Check for class methods defined in the page.

		I only support one format for these,
		<psp:method name="xxx" params="xxx,xxx">
		Then the function BODY, then <psp:method>.

		"""
		OPEN_METHOD = '<psp:method'
		CLOSE_METHOD = '/>'
		CLOSE_METHOD_2 = '</psp:method>'
		CLOSE_METHOD_3 = '>'
		attrs = None
		validAttributes = ('name', 'params')
		if reader.Matches(OPEN_METHOD):
			start = reader.Mark()
			reader.Advance(len(OPEN_METHOD))
			attrs = reader.parseTagAttributes()
			# PSPUtils.checkAttributes('method',attrs,validAttributes)
			reader.skipSpaces()
			if not reader.Matches(CLOSE_METHOD_3):
				raise 'Expected method declaration close'
			reader.Advance(len(CLOSE_METHOD_3))
			stop = reader.Mark()
			handler.setTemplateInfo(self.tmplStart, self.tmplStop)
			handler.handleMethod(start, stop, attrs)
			start = stop
			stop = reader.skipUntil(CLOSE_METHOD_2) #skip past the close marker, return the point before the close marker
			handler.handleMethodEnd(start, stop, attrs)
			return 1
		return 0

	checklist.append(checkMethod)

	def checkInclude(self, handler, reader):
		"""Check for inserting another pages output in this spot."""
		OPEN_INCLUDE = '<psp:include'
		CLOSE_INCLUDE_NO_BODY = "/>"
		CLOSE_INCLUDE_BODY = ">"
		CLOSE_INCLUDE = "</psp:include>"
		OPEN_INDIVIDUAL_PARAM = "<psp:param"
		CLOSE_INDIVIDUAL_PARAM = "/>"
		if reader.Matches(OPEN_INCLUDE):
			param = {}
			start = reader.Mark()
			reader.Advance(len(OPEN_INCLUDE))
			reader.skipSpaces()
			attrs = reader.parseTagAttributes()
			#PSPUtils.checkTagAttributes()....
			reader.skipSpaces()
			if not reader.Matches(CLOSE_INCLUDE_BODY):
				raise "Include bodies not implemented"
			reader.Advance(len(CLOSE_INCLUDE_BODY))
			stop = reader.Mark()
			handler.setTemplateInfo(self.tmplStart, self.tmplStop)
			handler.handleInclude(attrs, param)
			return 1
		return 0

	checklist.append(checkInclude)

	def checkInsert(self, handler, reader):
		"""Check for straight character dumps.

		No big hurry for this. It's almost the same as the page include
		directive.  This is only a partial implementation of what JSP does.
		JSP can pull it from another server, servlet, JSP page, etc.

		"""
		OPEN_INSERT = '<psp:insert'
		CLOSE_INSERT_NO_BODY = "/>"
		CLOSE_INSERT_BODY = ">"
		CLOSE_INSERT = "</psp:insert>"
		OPEN_INDIVIDUAL_PARAM = "<psp:param"
		CLOSE_INDIVIDUAL_PARAM = "/>"
		if reader.Matches(OPEN_INSERT):
			param = {}
			start = reader.Mark()
			reader.Advance(len(OPEN_INSERT))
			reader.skipSpaces()
			attrs = reader.parseTagAttributes()
			# PSPUtils.checkTagAttributes()....
			reader.skipSpaces()
			if not reader.Matches(CLOSE_INSERT_BODY):
				raise "Insert bodies not implemented"
			reader.Advance(len(CLOSE_INSERT_BODY))
			stop = reader.Mark()
			handler.setTemplateInfo(self.tmplStart, self.tmplStop)
			handler.handleInsert(attrs, param)
			return 1
		return 0

	checklist.append(checkInsert)

	def parse(self, until=None, accept=None):
		"""Parse the PSP file."""
		noPspElement = 0
		reader = self._reader
		handler = self._handler
		while reader.hasMoreInput():
			# This is for XML style blocks, which I'm not handling yet
			if until is not None and reader.Matches(until):
				return
			#If the file the reader is working on has changed due to a push or pop,
			#flush any char data from the old file
			if not reader.Mark().getFile() == self.currentFile:
				self.flushCharData(self.tmplStart, self.tmplStop)
				self.currentFile = reader.Mark().getFile()
				self.tmplStart = reader.Mark()
		# in JSP, this is an array of valid tag type to check for,
		# I'm not using it now, # and I don't think JSP does either
			if accept:
				pass
			accepted = 0
			for checkfunc in self.checklist:
				if checkfunc(self, handler, reader):
					accepted = 1
					noPspElement = 0
					break
			if not accepted:
				if not noPspElement:
					self.tmplStart = reader.Mark()
					noPspElement = 1
				st = reader.nextContent() #skip till the next possible tag
				self.tmplStop = reader.Mark() #mark the end of HTML data
				self.cout.write(st) #write out the raw HTML data
			self.flushCharData(self.tmplStart, self.tmplStop) #dump remaining raw HTML
