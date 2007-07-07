#!/usr/bin/env python
"""
FileList.py

A quick, hacky script to contruct a file list from a set of Python files.
"""


import os, re, sys
from glob import glob
from types import *


class FileList:
	"""Builds a file list for a package of Python modules."""

	def __init__(self, name):
		self._name = name
		self._files = []
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
		self._files.append(name)

	def printForWeb(self, file=sys.stdout):
		if type(file) is StringType:
			file = open(file, 'w')
			close = 1
		else:
			close = 0
		name = self._name
		title = 'File list of %s' % name
		other = ('<a href="ClassList.html">alphabetical class list<a>'
			' and <a href="ClassHierarchy.html">class hierarchy</a>'
			' of %s' % name)
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
		file.write('<tr><th>Source File</th>'
			'<th>Source</th><th>Doc</th><th>Summary</th></tr>\n')
		files = self._files
		files.sort(lambda a, b: cmp(a.lower(), b.lower()))
		for filename in files:
			file.write('<tr><td>%s</td></tr>\n' % self.links(filename))
		file.write('''</table>
</div></body>
</html>''')
		if close:
			file.close()

	def links(self, filename):
		"""In support of printForWeb()"""
		name = self._name
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
		return '</td><td class="center">'.join(links)


def main(args):
	filelist = FileList()
	for filename in args:
		filelist.readFiles(filename)
	filelist.printList()


if __name__ == '__main__':
	main(sys.argv[1:])
