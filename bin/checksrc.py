#!/usr/bin/env python

"""checksrc.py


INTRODUCTION

This utility checks for violations of various source code conventions
in the hope of keeping the project clean and consistent.
Please see Webware/Documentation/StyleGuidelines.html for more information
including some guidelines not checked for by this utility.


COMMAND LINE

Running this program from the command line with -h will give you usage/help:
	> python checksrc.py -h

Examples:
	> python checksrc.py
	> python checksrc.py SomeDir
	> python checksrc.py -R SomeDir
	> python checksrc.py . results.text

And often you run it from the Webware directory like so:
	> cd Webware
	> python bin/checksrc.py


AS A MODULE AND CLASS

If you imported this as a module, you would use the CheckSrc class,
possibly like so:
	from CheckSrc import CheckSrc
	CheckSrc().check()

	# or:
	cs = CheckSrc()
	if cs.readArgs():
		cs.check()

	# or:
	cs = CheckSrc()
	cs.setOutput('results.text')
	cs.check()

And of course, you could subclass CheckSrc() to customize it,
which is why even command line utils get done with classes
(rather than collections of functions and nekkid code).

You can also setDirectory(), setOutput() setRecurse() and setVerbose()
the defaults of which are '.', sys.stdout, 1 and 0.


CAVEATS

Note that checksrc.py takes a line oriented approach. Since it does not
actually properly parse Python code, it can be fooled in some cases.
Therefore, it's possible to get false alarms. While we could implement
a full parser to close the gap, doing so would be labor intensive with
little pay off. So we live with a few false alarms.


CONFIG FILES

You can modify the behavior of checksrc.py for a particular directory
by creating a .checksrc.config file like so:

{
	'SkipDirs': ['Cache'],
	'SkipFiles': ['fcgi.py', 'zCookieEngine.py'],
	'DisableErrors': {
		'UncapFN': '*',
		'ExtraUnder': ['MiddleObject'],
	}
}

Some notes:
	* You can specify some or all of the options.
	* SkipDirs and SkipFiles both require lists of filenames.
	* DisableError keys are error codes defined by checksrc.py.
	  You can find these out by running checksrc with the
	  -h command line option or checking the source below.
	* The value for disabling an error:
		* Can be an individual filename or a list of filenames.
		* Can be '*' for "all files".


RULES

	* File names start with capital letter.
	* (On POSIX) Files don't contain \r.
	* Spaces are not used for indentation.
	* Tabs are used only for initial indentation.
	* Class names start with a capital letter.
	* Method names start with a lower case letter.
	* Methods do not start with "get".
	* Data attributes start with an underscore _,
	  and are followed by a lower case letter
	* Method and attribute names have no underscores after the first character.
	* Expressions following if, while and return
	  are not enclosed in parenthesees, ().
	* Class defs and category comments, ## Like this ##
	  are preceded by 2 blank lines and are followed by one blank line
	  (unless the class implementation is pass).


FUTURE

Consider (optionally) displaying the source line.

Maybe: Experiment with including the name of the last seen method/function
with the error messages to help guide the user to where the error occurred.

Consider using the parser or tokenize modules of the standard library.

"""


import re, sys, os
from types import StringType


class NoDefault:
	pass


class CheckSrc:


	## Init ##

	_maxLineSize = 100

	_errors = {
		'UncapFN':
			'Uncapitalized filename.',
		'CarRet':
			'Carriage return \\r found.',
		'StrayTab':
			'Stray tab after other characters.'
			' No tabs allowed other than initial indentation.',
		'LineSize':
			'Limit line to a maximum of %d characters.' % _maxLineSize,
		'SpaceIndent':
			'Found space as part of indentation. Use only tabs.',
		'NoBlankLines':
			'%(what)s should be preceded by %(separator)s.',
		'ClassNotCap':
			'Class names should start with capital letters.',
		'MethCap':
			'Method name "%(name)s" should start with a lower case letter.',
		'GetMeth':
			'Method name "%(name)s" should not start with "get".',
		'NoUnderAttr':
			'Data attributes should start with an underscore: %(attribute)s.',
		'NoLowerAttr':
			'Data attributes should start with an underscore and then'
			' a lower case letter: %(attribute)s.',
		'ExtraUnder':
			'Attributes and methods should not have underscores past'
			' the first character: %(attribute)s.',
		'ExtraParens':
			'No outer parentheses should be used for "%(keyword)s".',
		'ObsExpr':
			'"%(old)s" is obsolescent, use "%(new)s" instead.',
		'OpNoSpace':
			'Operator "%(op)s" should be padded with one blank.',
		'CommaNoSpace':
			'Commas and semicolons should be followed by a blank.',
		'PaddedParens':
			'Parentheses should not be padded with blanks.',
		'NoCompStmts':
			'Compound statements are generally discouraged.',
		'AugmStmts':
			'Consider using augmented assignment "%(op)s."',
	}

	def __init__(self):
		# Grab our own copy of errors with lower case keys
		self._errors = {}
		self._errorCodes = []
		for key, value in self.__class__._errors.items():
			self._errorCodes.append(key)
			self._errors[key.lower()] = value

		# Misc init
		self._config = {}

		# Set default options
		self.setDirectory('.')
		self.setOutput(sys.stdout)
		self.setRecurse(1)
		self.setVerbose(0)


	## Options ##

	def directory(self):
		return self._directory

	def setDirectory(self, dir):
		"""Sets the directory that checking starts in."""
		self._directory = dir

	def output(self):
		return self._out

	def setOutput(self, output):
		"""Set the destination output.

		It can either be an object which must respond to write() or
		a string which is a filename used for one invocation of check().

		"""
		if type(output) is StringType:
			self._out = open(output, 'w')
			self._shouldClose = 1
		else:
			self._out = output
			self._shouldClose = 0

	def recurse(self):
		return self._recurse

	def setRecurse(self, flag):
		"""Set whether or not to recurse into subdirectories."""
		self._recurse = flag

	def verbose(self):
		return self._verbose

	def setVerbose(self, flag):
		"""Set whether or not to print extra information during check.

		For instance, print every directory and file name scanned.
		"""
		self._verbose = flag


	## Command line use ##

	def readArgs(self, args=sys.argv):
		"""Read a list of arguments in command line style (e.g., sys.argv).

		You can pass your own args if you like, otherwise sys.argv is used.
		Returns 1 on success; 0 otherwise.

		"""
		setDir = setOut = 0
		for arg in args[1:]:
			if arg == '-h' or arg == '--help':
				self.usage()
				return 0
			elif arg == '-r':
				self.setRecurse(1)
			elif arg == '-R':
				self.setRecurse(0)
			elif arg == '-v':
				self.setVerbose(1)
			elif arg == '-V':
				self.setVerbose(0)
			elif arg[0] == '-':
				self.usage()
				return 0
			else:
				if not setDir:
					self.setDirectory(arg)
					setDir = 1
				elif not setOut:
					self.setOutput(arg)
					setOut = 1
				else:
					self.write('Error: %s\n' % repr(arg))
					self.usage()
					return 0
		return 1

	def usage(self):
		progName = sys.argv[0]
		wr = self.write
		wr('Usage: %s [options] [startingDir [outputFilename]]\n' % progName)
		wr('''       -h --help = help
       -r -R = recurse, do not recurse. default -r
       -v -V = verbose, not verbose. default -V

Examples:
    > python checksrc.py
    > python checksrc.py SomeDir
    > python checksrc.py -R SomeDir
    > python checksrc.py . results.text

Error codes and their messages:
''')

		# Print a list of error codes and their messages
		keys = self._errorCodes[:]
		keys.sort()
		maxLen = 0
		for key in keys:
			if len(key) > maxLen:
				maxLen = len(key)
		for key in keys:
			paddedKey = key.ljust(maxLen)
			wr('  %s = %s\n' % (paddedKey, self._errors[key.lower()]))
		wr('\n')

		wr('.checksrc.config options include SkipDirs, SkipFiles and DisableErrors.\n'
			'See the checksrc.py doc string for more info.\n')


	## Printing, errors, etc. ##

	def write(self, *args):
		"""Invoked by self for all printing.

		This allows output to be easily redirected.

		"""
		write = self._out.write
		for arg in args:
			write(str(arg))

	def error(self, msgCode, args=NoDefault):
		"""Invoked by self when a source code error is detected.

		Prints the error message and it's location.
		Does not raise exceptions or halt the program.

		"""
		# Implement the DisableErrors option
		disableNames = self.setting('DisableErrors', {}).get(msgCode, [])
		if '*' in disableNames or self._fileName in disableNames \
				or os.path.splitext(self._fileName)[0] in disableNames:
			return
		if not self._printedDir:
			self.printDir()
		msg = self._errors[msgCode.lower()]
		if args is not NoDefault:
			msg %= args
		self.write(self.location(), msg, '\n')

	def fatalError(self, msg):
		"""Report a fatal error and raise CheckSrcError.

		For instance, handle an invalid configuration file.

		"""
		self.write('FATAL ERROR: %s\n' % msg)
		raise CheckSrcError

	def location(self):
		"""Return a string indicating the current location.

		The string format is "fileName:lineNum:charNum:".
		The string may be shorter if the latter components are undefined.

		"""
		s = ''
		if self._fileName is not None:
			s += self._fileName
			if self._lineNum is not None:
				s += ':' + str(self._lineNum)
				if self._charNum is not None:
					s += ':' + str(self._charNum)
		if s:
			s += ':'
		return s

	def printDir(self):
		"""Self utility method to print the directory being processed."""
		self.write('\n', self._dirName, '\n')
		self._printedDir = 1


	## Configuration ##

	def readConfig(self, dirName):
		filename = os.path.join(dirName, '.checksrc.config')
		try:
			contents = open(filename).read()
		except IOError:
			return
		try:
			dict = eval(contents)
		except:
			self.fatalError('Invalid config file at %s.' % filename)
		# For DisableErrors, we expect a dictionary keyed by error codes.
		# For each code, we allow a value that is either a string or a list.
		# But for ease-of-use purposes, we now convert single strings to
		# lists containing the string.
		de = dict.get('DisableErrors', None)
		if de:
			for key, value in de.items():
				if type(value) is StringType:
					de[key] = [value]
		self._config = dict

	def setting(self, name, default=NoDefault):
		if default is NoDefault:
			return self._config[name]
		else:
			return self._config.get(name, default)


	## Checking ##

	def check(self):
		if self._recurse:
			os.path.walk(self._directory, self.checkDir, None)
		else:
			self.checkDir(None, self._directory, os.listdir(self._directory))
		if self._shouldClose:
			self._out.close()

	def checkDir(self, arg, dirName, names):
		"""Invoked by os.path.walk() which is kicked off by check().

		Recursively checks the given directory and all it's subdirectories.

		"""
		# Initialize location attributes.
		# These are updated while processing and
		# used when reporting errors.
		self._dirName = dirName
		self._fileName = None
		self._lineNum = None
		self._charNum = None
		self._printedDir = 0

		if self._verbose:
			self.printDir()

		self.readConfig(dirName)

		# Prune directories based on configuration:
		skipDirs = self.setting('SkipDirs', [])
		for dir in skipDirs:
			try:
				index = names.index(dir)
			except ValueError:
				continue
			print '>> skipping', dir
			del names[index]

		skipFiles = self.setting('SkipFiles', [])
		for name in names:
			if len(name) > 2 and name[-3:] == '.py' \
					and name not in skipFiles \
					and os.path.splitext(name)[0] not in skipFiles:
				try:
					self.checkFile(dirName, name)
				except CheckSrcError:
					pass

	def checkFile(self, dirName, name):
		self._fileName = name
		if self._verbose:
			self.write('  %s\n' % self._fileName)

		self.checkFilename(name)

		filename = os.path.join(dirName, name)
		contents = open(filename, 'rb').read()
		self.checkFileContents(contents)

		lines = open(filename).readlines()
		self.checkFileLines(lines)

	def checkFilename(self, filename):
		if filename[0] != filename[0].upper():
			self.error('UncapFN')

	def checkFileContents(self, contents):
		if os.name == 'posix':
			if '\r' in contents:
				self.error('CarRet')

	def checkFileLines(self, lines):
		self._lineNum = 1
		self._blankLines = 2
		self._inMLS = None # MLS = multi-line string
		for line in lines:
			self.checkFileLine(line)

	def checkFileLine(self, line):
		line = line.rstrip()
		if line:
			self.checkLineSize(line)
			line = self.clearStrings(line)
			if line:
				self.checkTabsAndSpaces(line)
				lineleft = line.lstrip()
				indent = line[:len(line) - len(lineleft)]
				line = lineleft
				parts = line.split()
				self.checkBlankLines(line)
				self.checkCompStmts(parts, line)
				self.checkAugmStmts(parts)
				self.checkClassName(parts)
				self.checkMethodName(parts, indent)
				self.checkExtraParens(parts, line)
				self.checkPaddedParens(line)
				self.checkAttrNames(line)
				self.checkOperators(line)
				self.checkCommas(line)
				self._blankLines = 0
			else:
				self._blankLines = 1
		else:
			self._blankLines += 1
		self._lineNum += 1

	def checkLineSize(self, line):
		if len(line) > self._maxLineSize:
			self.error('LineSize')

	def clearStrings(self, line):
		"""Return line with all quoted strings cleared."""
		index = 0
		quote = self._inMLS
		while index != -1:
			if quote:
				index2 = index
				while 1:
					index2 = line.find(quote, index2)
					if index2 > 0 and line[index2 - 1] == '\\':
						index2 += 1
						continue
					break
				if index2 == -1:
					if index < len(line):
						line = line[:index] + '...'
					break
				if index < index2:
					line = line[:index] + '...' + line[index2:]
					index += 3
				index += len(quote)
				quote = None
			index3 = line.find('#', index)
			index2 = line.find("'", index)
			index = line.find('"', index)
			if index2 != -1 and (index == -1 or index2 < index):
				index = index2
			if index3 != -1 and (index == -1 or index3 < index):
				if line[index3+1:index3+2] == '#' \
						and not line[:index3].rstrip():
					# keep category comments
					line = line[:index3+2]
				else:
					# remove any other comment
					line = line[:index3].rstrip()
				break
			if index != -1:
				quote = line[index]
				if line[index:index+3] == quote*3:
					quote *= 3
				index += len(quote)
		if quote and len(quote) < 3:
			quote = None
		self._inMLS = quote
		return line

	def checkBlankLines(self, line):
		if line.startswith('##') and self._blankLines < 2:
			what = 'Category comments'
			separator = 'two blank lines'
		elif (line.startswith('class ') and self._blankLines < 2
				and not line.endswith('Exception):')
				and not line.endswith('Error):')
				and not line.endswith('pass')):
			what = 'Class definitions'
			separator = 'two blank lines'
		elif (line.startswith('def ') and self._blankLines < 1
				and not line.endswith('pass')):
			what = 'Function definitions'
			separator = 'one blank line'
		else:
			return
		self.error('NoBlankLines', locals())

	def checkTabsAndSpaces(self, line):
		foundTab = foundSpace = foundOther = 0
		for c in line:
			if c == '\t':
				foundTab = 1
				if foundSpace or foundOther:
					self.error('StrayTab')
					break
			elif c == ' ':
				foundSpace = 1
				if not foundOther:
					self.error('SpaceIndent')
					break
			else:
				foundOther = 1

	def checkClassName(self, parts):
		if 'class' in parts: # e.g. if 'class' is a standalone word
			index = parts.index('class')
			if index == 0: # e.g. if start of the line
				name = parts[1]
				if name and name[0] != name[0].upper():
					self.error('ClassNotCap')

	def checkMethodName(self, parts, indent):
		if 'def' in parts: # e.g. if 'def' is a standalone word
			index = parts.index('def')
			if index == 0 and indent:
				# e.g. if start of the line, and indented (indicating method and not function)
				name = parts[1]
				name = name[:name.find('(')]
				if name and name[0] != name[0].lower():
					self.error('MethCap', locals())
				if len(name) > 3 and name[:3].lower() == 'get':
					self.error('GetMeth', locals())

	_exprKeywords = {}
	for k in 'assert for if return while with yield'.split():
		_exprKeywords[k] = None

	def checkExtraParens(self, parts, line):
		if (len(parts) > 1 and self._exprKeywords.has_key(parts[0])
				and parts[1][0] == '('
				and parts[-1].replace(':', '').rstrip()[-1:] == ')'
				and not line.count(')') < line.count('(')):
			keyword = parts[0]
			self.error('ExtraParens', locals())

	_blockKeywords = {}
	for k in 'if elif else: try: except: while for with'.split():
		_blockKeywords[k] = None

	def checkCompStmts(self, parts, line):
		if (len(parts) > 1 and self._blockKeywords.has_key(parts[0])
				and line.find(': ') != -1 and line[-1] != ':'):
			self.error('NoCompStmts')
		else:
			index = line.find(';')
			if index != -1:
				if line.find('"') < index and line.find("'") < index:
					self.error('NoCompStmts')

	# Any kind of access of self
	_accessRE = re.compile(r'self\.(\w+)\s*(\(?)')
	# Irregular but allowed attribute names
	_allowedAttrNames = {}
	for k in 'assert_ has_key'.split():
		_allowedAttrNames[k] = None

	def checkAttrNames(self, line):
		for match in self._accessRE.findall(line):
			attribute = match[0]
			isMethod = match[1] == '('
			if not isMethod:
				if not attribute[0] == '_':
					# Attribute names that are data (and not methods)
					# should start with an underscore.
					self.error('NoUnderAttr', locals())
				elif attribute[-2:] != '__' and not attribute[1:2].islower():
					# The underscore should be followed by a lower case letter.
					self.error('NoLowerAttr', locals())
			# Attribute names should have no underscores after the first one.
			if len(attribute) > 2 and attribute[:2] == '__':
				inner = attribute[2:]
				if len(inner) > 2 and inner[-2:] == '__':
					inner = inner[:-2]
			else:
				if len(attribute) > 1 and attribute[0] == '_':
					inner = attribute[1:]
				else:
					inner = attribute
			if inner.find('_') >= 0 \
					and not self._allowedAttrNames.has_key(inner):
				self.error('ExtraUnder', locals())

	# Assignment operators
	_assignRE = re.compile(
		r'^[^\(]*?[^\s=<>!\+\-\*/%&\^\|](\s*)=[^\s=](\s*)')
	# Strict comparison Operators
	_compareRE = re.compile(r'(\s*)(<|>)[^\s=<>](\s*)')
	# Other comparison Operators and augmented assignments
	_augmentRE = re.compile(
		r'(\s*)(=|<|>|!|\+|-|\*|/|%|\*\*|>>|<<|&|\^|\|)=(\s*)')

	def checkOperators(self, line):
		if line.find('<>') != -1:
			self.error('ObsExpr', {'old': '<>', 'new': '!='})
		for match in self._assignRE.findall(line):
			if match[0] != ' ' or match[1] != ' ':
				if not line.count(')') > line.count('('):
					self.error('OpNoSpace', {'op': '='})
		for match in self._compareRE.findall(line):
			if match[0] != ' ' or match[2] != ' ':
				self.error('OpNoSpace', {'op': match[1]})
		for match in self._augmentRE.findall(line):
			if match[0] != ' ' or match[2] != ' ':
				self.error('OpNoSpace', {'op': match[1] + '='})

	# Augmented assignment operators
	_augmOp = {}
	for k in '+ - * / % ** >> << & ^ |'.split():
		_augmOp[k] = None

	def checkAugmStmts(self, parts):
		if len(parts) > 4 and parts[1] == '=' \
				and parts[0] == parts[2] \
				and self._augmOp.has_key(parts[3]):
			self.error('AugmStmts', {'op': parts[3] + '='})

	# Commas and semicolons not followed by a blank
	_commaRE = re.compile('(,|;)[^\s\)]')

	def checkCommas(self, line):
		if self._commaRE.search(line):
			self.error('CommaNoSpace')

	# Parens padded with blanks
	_parensRE = re.compile('[(\(\{\[]\s+|\s+[\)\}\]]')

	def checkPaddedParens(self, line):
		if self._parensRE.search(line):
			self.error('PaddedParens')


class CheckSrcError(Exception):
	pass


class _DummyWriter:

	def write(self, msg):
		pass


if __name__ == '__main__':
	cs = CheckSrc()
	if cs.readArgs():
		cs.check()
