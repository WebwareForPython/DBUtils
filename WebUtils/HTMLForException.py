import sys, traceback
from Funcs import htmlEncode
import re, urllib, os


HTMLForExceptionOptions = {
	'table': 'background-color:#F0F0F0',
	'default': 'color:#000000',
	'row.location': 'color:#000099',
	'row.code': 'color:#990000',
	'editlink': None,
}


fileRE = re.compile(r'File "([^"]*)", line ([0-9]+), in ([^ ]*)')

def HTMLForException(excInfo=None, options=None):
	"""Get HTML for displaying an exception.

	Returns an HTML string that presents useful information to the developer
	about the exception. The first argument is a tuple such as returned by
	sys.exc_info() which is in fact, invoked if the tuple isn't provided.

	"""
	# @@ 2000-04-17 ce: Maybe excInfo should default to None and get set
	# to sys.excInfo() if not specified. If so, then clean up other code.

	# Get the excInfo if needed:
	if excInfo is None:
		excInfo = sys.exc_info()

	# Set up the options:
	if options:
		opt = HTMLForExceptionOptions.copy()
		opt.update(options)
	else:
		opt = HTMLForExceptionOptions

	# Create the HTML:
	res = ['<table style="%s" width=100%%'
		' cellpadding="2" cellspacing="2">\n' % opt['table'],
		'<tr><td><pre style="%s">\n' % opt['default']]
	out = traceback.format_exception(*excInfo)
	for line in out:
		match = fileRE.search(line)
		if match:
			parts = map(htmlEncode, line.split('\n'))
			parts[0] = '<span style="%s">%s</span>' \
				% (opt['row.location'], parts[0])
			if opt['editlink']:
				parts[0] = '%s <a href="%s?filename=%s&line=%s">[edit]</a>' \
					% (parts[0], opt['editlink'], urllib.quote(
						os.path.join(os.getcwd(), match.group(1))),
						match.group(2))
			parts[1] = '<span style="%s">%s</span>' \
				% (opt['row.code'], parts[1])
			line = '\n'.join(parts)
			res.append(line)
		else:
			res.append(htmlEncode(line))
	if out:
		if res[-1][-1] == '\n':
			res[-1] = res[-1].rstrip()
	res.extend(['</pre></td></tr>\n', '</table>\n'])
	return ''.join(res)
