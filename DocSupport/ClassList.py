#!/usr/bin/env python
"""
ClassHierarchy.py

A quick, hacky script to contruct a class hierarchy list from a set of Python files.

"""


import os, re, sys, time
from glob import glob
from types import *


def EmptyString(klass):
	return ''


class Klass:
	"""Represents a Python class for our purposes."""

	def __init__(self, name, filename=''):
		self._name = name
		self._bases = []
		self._derived = []
		self._filename = filename

	def addBase(self, klass):
		assert isinstance(klass, Klass)
		if klass not in self._bases:
			self._bases.append(klass)
		klass.addDerived(self)

	def addDerived(self, klass):
		assert isinstance(klass, Klass)
		if klass not in self._derived:
			self._derived.append(klass)

	def name(self):
		return self._name

	def filename(self):
		return self._filename

	def setFilename(self, filename):
		self._filename = filename

	def printList(self, file=sys.stdout,
			indent=0, indentString='    ',
			prefix='', func=EmptyString, postfix='',
			multipleBasesMarker='*'):
		filename = self._filename
		if os.path.splitext(filename)[0] == self._name:
			filename = ''
		if len(self._bases) < 2:
			star = ''
		else:
			star = multipleBasesMarker
		file.write(''.join((prefix, indentString*indent,
			self._name, star, func(self), postfix)))
		indent += 1
		for klass in self._derived:
			klass.printList(file, indent, indentString, prefix, func, postfix)

	def __repr__(self):
		return '<%s, %s>' % (self.__class__.__name__, self._name)


class ClassList:
	"""Builds a class list for a package of Python modules."""

	def __init__(self, name):
		self._name = name
		self._splitter = re.compile(r"[(,):]")
		self._klasses = {}
		self._verbose = 0
		self._filesToIgnore = []

	def addFilesToIgnore(self, list):
		self._filesToIgnore.extend(list)

	def readFiles(self, filename):
		filenames = glob(filename)
		for name in filenames:
			self.readFile(name)

	def readFile(self, name):
		if name in self._filesToIgnore:
			if self._verbose:
				print 'Skipping %s...' % name
			return
		if self._verbose:
			print 'Reading %s...' % name
		lines = open(name).readlines()
		lineNum = 1
		for line in lines:
			if len(line) > 8 and \
				line[:5] == 'class' and \
				line[5] in ' \t' and \
				line.find(':') != -1:
				self.readLine(line, name, lineNum)
			lineNum += 1
		if self._verbose:
			print

	def readLine(self, line, filename=None, lineNum=None):
		# strip comments
		comment = line.find('#')
		if comment != -1:
			line = line[:comment]
		# split into words
		names = self._splitter.split(line[5:])
		# strip white space
		names = map(lambda part: part.strip(), names)
		# get rid of empty strings
		names = filter(None, names)
		# special case:  class foo(fi): pass
		if names[-1] == 'pass':
			del names[-1]
		# check for weirdos
		for name in names:
			if ' ' in name  or  '\t' in name:
				if name is not None:
					if lineNum is not None:
						print '%s:%s:' % (filename, lineNum),
					else:
						print '%s:' % (filename),
				print 'strange result:', names
				if not self._verbose:
					print 'Maybe you should set self._verbose and try again.'
				sys.exit(1)
		if self._verbose:
			print names
		# create the klasses as needed
		for name in names:
			if not self._klasses.has_key(name):
				self._klasses[name] = Klass(name)
		# connect them
		klass = self._klasses[names[0]]
		klass.setFilename(filename)
		for name in names[1:]:
			klass.addBase(self._klasses[name])

	def roots(self):
		roots = []
		for klass in self._klasses.values():
			if len(klass._bases) == 0:
				roots.append(klass)
		return roots

	def printList(self, file=sys.stdout):
		roots = self.roots()
		roots.sort(lambda a, b: cmp(a._name, b._name))
		for klass in roots:
			klass.printList(file=file)

	def printForWeb(self, hierarchic=0, file=sys.stdout):
		if type(file) is StringType:
			file = open(file, 'w')
			close = 1
		else:
			close = 0
		name = self._name
		title = 'Class %s of %s' % (
			hierarchic and 'Hierarchy' or 'List', name)
		other = ('<a href="Class%s.html">%s class list<a>'
			' and the <a href="FileList.html">list of files<a> of %s'
			% (hierarchic and 'List' or 'Hierarchy',
				hierarchic and 'alphabetical' or 'hierarchical', name))
		file.write('''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<head>
<title>%s</title>
<style type="text/css">
<!--
body { background: #FFF;
 font-family: Verdana, Arial, Helvetica, sans-serif;
 font-size: 10pt;
 padding: 6pt; }
th { background-color: #CCF; text-align: left; }
td { background-color: #EEF; }
.center { text-align: center; }
.center table { margin-left: auto; margin-right: auto; text-align: left; }
-->
</style>
</head>
<body><div class="center">
<h1>%s</h1>
<p>See also the %s.</p>
<table cellpadding="2" cellspacing="2">
''' % (title, title, other))
		file.write('<tr><th>Class Name</th><th>Source File</th>'
			'<th>Source</th><th>Doc</th><th>Summary</th></tr>\n')
		if hierarchic:
			classes = self.roots()
		else:
			classes = self._klasses.values()
		classes.sort(lambda a, b: cmp(a._name, b._name))
		for klass in classes:
			if hierarchic:
				klass.printList(file=file, prefix='<tr><td>',
					indentString='&nbsp;'*6,
					func=self.links, postfix='</tr>\n')
			else:
				file.write('<tr><td>%s%s</tr>\n'
					% (klass.name(), self.links(klass)))
		file.write('''</table>
</div></body>
</html>''')
		if close:
			file.close()

	def links(self, klass):
		"""In support of printForWeb()"""
		name = self._name
		filename = klass.filename()
		module = os.path.splitext(filename)[0]
		links = []
		# souce file
		if os.path.exists(filename):
			links.append('<a href="../../%s">%s</a>' % (filename, filename))
		else:
			links.append('&nbsp;')
		# highlighted source file
		if os.path.exists('Docs/Source/Files/%s.html' % module):
			links.append('<a href="Files/%s.html">source</a>' % module)
		else:
			links.append('&nbsp;')
		# doc file
		if os.path.exists('Docs/Source/Docs/%s.%s.html' % (name, module)):
			links.append('<a href="Docs/%s.%s.html">doc</a>' % (name, module))
		else:
			links.append('&nbsp;')
		# summary file
		if os.path.exists('Docs/Source/Summaries/%s.html' % module):
			links.append('<a href="Summaries/%s.html">summary</a>' % module)
		else:
			links.append('&nbsp;')
		# finish up
		links = '</td><td class="center">'.join(links)
		return '</td><td>%s</td>' % links


def main(args):
	classlist = ClassList()
	for filename in args:
		classlist.readFiles(filename)
	classlist.printList()


if __name__ == '__main__':
	main(sys.argv[1:])
