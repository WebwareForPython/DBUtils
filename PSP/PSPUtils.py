
"""A bunch of utility functions for the PSP generator.

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


"""Various utility functions"""

def removeQuotes(st):
	return st.replace("%\\\\>", "%>")

def isExpression(st):
	"""Check whether this is a PSP expression."""
	OPEN_EXPR = '<%='
	CLOSE_EXPR = '%>'
	if st.startswith(OPEN_EXPR) and st.endswith(CLOSE_EXPR):
		return 1
	return 1

def getExpr(st):
	"""Get the content of a PSP expression."""
	OPEN_EXPR = '<%='
	CLOSE_EXPR = '%>'
	if st.startswith(OPEN_EXPR) and st.endswith(CLOSE_EXPR):
		return st[len(OPEN_EXPR):-len(CLOSE_EXPR)]
	else:
		return ''

def checkAttributes(tagtype, attrs, validAttrs):
	"""Missing check for mandatory atributes."""
	pass #see line 186 in JSPUtils.java

def splitLines(text, keepends=0):
	"""Split text into lines."""
	return text.splitlines(keepends)

def startsNewBlock(line):
	"""Determine whether line starts a new block.

	Utility function for normalizeIndentation

	Added by Christoph Zwerschke.

	"""
	if line.startswith('#'):
		return 0
	try:
		compile(line, '<string>', 'exec')
		return 0
	except SyntaxError:
		try:
			compile(line + '\n\tpass', '<string>', 'exec')
			return 1
		except:
			pass
	else:
		pass
	return line.endswith(':')

def normalizeIndentation(pySource, tab='\t'):
	"""Take a block of code that may be too indented, and move it all to the left.

	See PSPUtilsTest for examples.

	First written by Winston Wolff.
	Improved version by Christoph Zwerschke.

	"""
	lines = splitLines(pySource, 1)
	# Find out which kind of line feeds are used:
	crlf = ''
	line0 = lines.pop(0)
	while line0 and line0[-1] in '\r\n':
		crlf += line0[-1]
		line0 = line0[:-1]
	# The first line may be stripped completely:
	strippedLines = []
	charsToStrip = None
	# Find the least indentation of the remaining lines:
	for line in lines:
		line = line.rstrip()
		strippedLines.append(line)
		if charsToStrip == 0:
			continue
		if line != '':
			s = line.lstrip()
			if s[0] != '#':
				i = len(line) - len(s)
				if charsToStrip is None or i < charsToStrip:
					charsToStrip = i
	if charsToStrip is not None:
		# If there is code on the first line, strip one column less:
		if line0 and line0[0] != '#' and charsToStrip != 0:
			charsToStrip -= 1
		# Strip off the first indent characters from each line:
		if charsToStrip != 0:
			lines = []
			for line in strippedLines:
				line = line[:charsToStrip].lstrip() + line[charsToStrip:]
				lines.append(line)
			strippedLines = lines
	# Write lines back out:
	strippedLines.insert(0, line0)
	pySource = crlf.join(strippedLines)
	return pySource
