import sys, traceback
from Funcs import htmlEncode


HTMLForExceptionOptions = {
	'table': 'background-color:#F0F0F0;font-size:10pt',
	'default': 'color:#000000',
	'row.location': 'color:#000099',
	'row.code': 'color:#990000',
	'editlink': None,
}


def ExpansiveHTMLForException(context=5, options=None):
	from WebUtils import cgitb
	if options:
		opt = HTMLForExceptionOptions.copy()
		opt.update(options)
	else:
		opt = HTMLForExceptionOptions
	return cgitb.html(context=context, options=opt)
