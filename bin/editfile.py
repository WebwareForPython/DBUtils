#!/usr/bin/env python

editor = 'gnuclient (Emacs)'

editorCommands = {
	'gnuclient (Emacs)': 'gnuclient +%(line)s %(file)s',
	}

import os
from rfc822 import Message

def openFile(filename, line):
	os.system(editorCommands[editor] % {'file': filename,
										'line': line})

def parseFile(filename):
	file = open(filename)
	m = Message(file)
	openFile(m['filename'], m['line'])

if __name__ == '__main__':
	import sys
	parseFile(sys.argv[1])
	
