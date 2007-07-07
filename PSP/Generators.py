
"""Generate Python code from PSP templates.

	This module holds the classes that generate the Python code resulting from the PSP template file.
	As the parser encounters PSP elements, it creates a new Generator object for that type of element.
	Each of these elements is put into a list maintained by the ParseEventHandler object.  When it comes
	time to output the Source Code, each generator is called in turn to create it's source.

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

import os, re
import PSPUtils, BraceConverter

# These are global so that the ParseEventHandler and this module agree:
ResponseObject = 'res'
AwakeCreated = 0


class GenericGenerator:
	""" Base class for the generators """

	def __init__(self, ctxt=None):
		self._ctxt = ctxt
		self.phase = 'Service'


class ExpressionGenerator(GenericGenerator):
	"""This class handles expression blocks.

	It simply outputs the (hopefully) python expression within the block
	wrapped with a _formatter() call.

	"""

	def __init__(self, chars):
		self.chars = chars
		GenericGenerator.__init__(self)

	def generate(self, writer, phase=None):
		writer.println('res.write(_formatter(' + PSPUtils.removeQuotes(self.chars) + '))')


class CharDataGenerator(GenericGenerator):
	"""This class handles standard character output, mostly HTML.

	It just dumps it out. Need to handle all the escaping of characters.
	It's just skipped for now.

	"""

	def __init__(self, chars):
		GenericGenerator.__init__(self)
		self.chars = chars

	def generate(self, writer, phase=None):
		# Quote any existing backslash so generated Python will not interpret it when running.
		self.chars = self.chars.replace('\\', r'\\')
		# Quote any single quotes so it does not get confused with our triple-quotes:
		self.chars = self.chars.replace('"', r'\"')
		self.generateChunk(writer)

	def generateChunk(self, writer, start=0, stop=None):
		writer.printIndent() # gives a tab
		writer.printChars(ResponseObject+'.write("""')
		writer.printChars(self.chars)
		writer.printChars('""")')
		writer.printChars('\n')

	def mergeData(self, cdGen):
		self.chars += cdGen.chars


class ScriptGenerator(GenericGenerator):
	"""Generate scripts."""

	def __init__(self, chars, attrs):
		GenericGenerator.__init__(self)
		self.chars = chars

	def generate(self, writer, phase=None):
		self.chars = PSPUtils.normalizeIndentation(self.chars, writer._indent)
		if writer._useBraces:
			# Send lines to be output by the braces generator:
			bc = BraceConverter.BraceConverter()
			lines = PSPUtils.splitLines(PSPUtils.removeQuotes(self.chars))
			for line in lines:
				bc.parseLine(line, writer)
			return
		# Check for whitespace at the beginning and if less than 2 spaces, remove:
		if self.chars[:1] == ' ' and self.chars[:2] != '  ':
			self.chars = self.chars.lstrip()
		lines = PSPUtils.splitLines(PSPUtils.removeQuotes(self.chars))
		# userIndent check
		if len(lines[-1]) > 0 and lines[-1][-1] == '$':
			lastline = lines[-1] = lines[-1][:-1]
			if lastline == '':
				lastline = lines[-2] # handle endscript marker on its own line
			count = 0
			while lastline[count].isspace():
				count += 1
			userIndent = lastline[:count]
		else:
			userIndent = writer._emptyString
			lastline = lines[-1]
		# Print out code (moved from above):
		writer._userIndent = writer._emptyString # reset to none
		writer.printList(lines)
		writer.printChars('\n')
		# Check for a block:
		# lastline = string.splitfields(PSPUtils.removeQuotes(self.chars), '\n')[-1]
		commentstart = lastline.find('#') # @@ this fails if '#' part of string
		if commentstart > 0:
			lastline = lastline[:commentstart]
		blockcheck = lastline.rstrip()
		if len(blockcheck) > 0 and blockcheck[-1] == ':':
			writer.pushIndent()
			writer.println()
			writer._blockcount = writer._blockcount+1
			# Check for end of block, "pass" by itself:
		if self.chars.strip() == 'pass' and writer._blockcount > 0:
			writer.popIndent()
			writer.println()
			writer._blockcount -= 1
		# Set userIndent for subsequent HTML:
		writer._userIndent = userIndent


class EndBlockGenerator(GenericGenerator):

	def __init__(self):
		GenericGenerator.__init__(self)

	def generate(self, writer, phase=None):
		if writer._blockcount > 0:
			writer.popIndent()
			writer.println()
			writer._blockcount -= 1
		writer._userIndent = writer._emptyString


class ScriptFileGenerator(GenericGenerator):
	"""Add Python code at the file/module level."""

	def __init__(self, chars, attrs):
		GenericGenerator.__init__(self)
		self.phase = 'psp:file'
		self.attrs = attrs
		self.chars = chars

	def generate(self, writer, phase=None):
		writer.println('\n# File level user code')
		pySrc = PSPUtils.normalizeIndentation(self.chars, writer._indent)
		pySrc = PSPUtils.splitLines(PSPUtils.removeQuotes(pySrc))
		writer.printList(pySrc)


class ScriptClassGenerator(GenericGenerator):
	"""Add Python code at the class level."""

	def __init__(self, chars, attrs):
		GenericGenerator.__init__(self)
		self.phase = 'psp:class'
		self.attrs = attrs
		self.chars = chars

	def generate(self, writer, phase=None):
		writer.println('# Class level user code\n')
		pySrc = PSPUtils.normalizeIndentation(self.chars, writer._indent)
		pySrc = PSPUtils.splitLines(PSPUtils.removeQuotes(pySrc))
		writer.printList(pySrc)


class MethodGenerator(GenericGenerator):
	"""Generate class methods defined in the PSP page.

	There are two parts to method generation.
	This class handles getting the method name and parameters set up.

	"""

	def __init__(self, chars, attrs):
		GenericGenerator.__init__(self)
		self.phase = 'Declarations'
		self.attrs = attrs

	def generate(self, writer, phase=None):
		writer.printIndent()
		writer.printChars('def ')
		writer.printChars(self.attrs['name'])
		writer.printChars('(')
		# self.attrs['params']
		writer.printChars('self')
		if self.attrs.has_key('params') and self.attrs['params'] != '':
			writer.printChars(', ')
			writer.printChars(self.attrs['params'])
		writer.printChars('):\n')
		if self.attrs['name'] == 'awake':
			# This is hacky, need better method, but it works.
			# @@ Maybe I should require a standard parent and do the intPSP call in that awake?
			AwakeCreated = 1
			# Below indented on 6/1/00, was outside if block:
			writer.pushIndent()
			writer.println('self.initPSP()\n')
			writer.popIndent()
			writer.println()


class MethodEndGenerator(GenericGenerator):
	"""Part of class method generation.

	After MethodGenerator, MethodEndGenerator actually generates
	the code for the method body.

	"""

	def __init__(self, chars, attrs):
		GenericGenerator.__init__(self)
		self.phase = 'Declarations'
		self.attrs = attrs
		self.chars = chars

	def generate(self, writer, phase=None):
		writer.pushIndent()
		writer.printList(PSPUtils.splitLines(PSPUtils.removeQuotes(self.chars)))
		writer.printChars('\n')
		writer.popIndent()


class IncludeGenerator(GenericGenerator):
	"""Handle psp:include directives.

	This is a new version of this directive that actually
	forwards the request to the specified page.

	"""

	# _theFunction = """
	# __pspincludepath = self.transaction().request().urlPathDir() + "%s"
	# self.transaction().application().includeURL(self.transaction(), __pspincludepath)
	# """
	_theFunction = """
__pspincludepath = "%s"
self.transaction().application().includeURL(self.transaction(), __pspincludepath)
"""

	def __init__(self, attrs, param, ctxt):
		GenericGenerator.__init__(self, ctxt)
		self.attrs = attrs
		self.param = param
		self.scriptgen = None

		self.url = attrs.get('path')
		if self.url is None:
			raise "No path attribute in Include"

		self.scriptgen = ScriptGenerator(self._theFunction % self.url, None)

	def generate(self, writer, phase=None):
		"""Just insert theFunction."""
		self.scriptgen.generate(writer, phase)


class InsertGenerator(GenericGenerator):
	"""Include files designated by the psp:insert syntax.

	If the attribute 'static' is set to True or 1, we include the file now,
	at compile time. Otherwise, we use a function added to every PSP page
	named __includeFile, which reads the file at run time.

	"""

	def __init__(self, attrs, param, ctxt):
		GenericGenerator.__init__(self, ctxt)
		self.attrs = attrs
		self.param = param
		self.scriptgen = None

		self.page = attrs.get('file')
		if not self.page:
			raise "No file attribute in include"
		thepath = self._ctxt.resolveRelativeURI(self.page)
		if not os.path.exists(thepath):
			print self.page
			raise "Invalid included file", thepath
		self.page = thepath

		self.static = str(attrs.get('static')).lower() in ('true', 'yes', '1')
		if not self.static:
			self.scriptgen = ScriptGenerator("self.__includeFile('%s')"
				% thepath.replace('\\', '\\\\'), None)

	def generate(self, writer, phase=None):
		# JSP does this in the servlet. I'm doing it here because
		# I have triple quotes. # Note: res.write statements inflate
		# the size of the resulting classfile when it is cached.
		# Cut down on those by using a single res.write on the whole
		# file, after escaping any triple-double quotes."""
		if self.static:
			data = open(self.page).read()
			data= data.replace('"""', r'\"""')
			writer.println('res.write("""'+data+'""")')
			writer.println()
		else:
			self.scriptgen.generate(writer, phase)
