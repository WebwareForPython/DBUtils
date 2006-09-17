"""
cgitb.py
  By Ka-Ping Yee <ping@lfw.org> http://web.lfw.org/python/
  Modified for Webware by Ian Bicking <ianb@colorstudy.com>
"""

import sys, os, types, keyword, linecache, tokenize
# We include a copy of pydoc but since it's in the Python 2.1
# standard library, we'll try to import it there first.
try:
	import pydoc
except ImportError:
	from MiscUtils import pydoc
# But we need to use a fixed version of inspect
# so we won't use the one that comes with Python 2.1.
from MiscUtils import inspect

DefaultOptions = {

	'table': 'background-color:#F0F0F0',
	'default': 'color:#000000',
	'row.location': 'color:#000099',
	'row.code': 'color:#990000',
	'header': 'color:#FFFFFF;background-color:#999999',
	'subheader': 'color:#000000;background-color:#F0F0F0;font-size:10pt',
	'code.accent': 'background-color:#FFFFCC',
	'code.unaccent': 'color:#999999;font-size:10pt',
}

def breaker():
	return ('<body style="background-color:#F0F0FF">' +
		'<span style="color:#F0F0FF;font-size:small"> > </font> ' +
		'</table>' * 5)

def html(context=5, options=None):
	if options:
		opt = DefaultOptions.copy()
		opt.update(options)
	else:
		opt = DefaultOptions

	etype, evalue = sys.exc_info()[:2]
	if type(etype) is types.ClassType:
		etype = etype.__name__
	inspect_trace = inspect.trace(context)
	inspect_trace.reverse()

	pyver = 'Python ' + sys.version.split()[0] + '<br>' + sys.executable
	javascript = """
	<script language="JavaScript"><!--
	function popup_repr(title, value) {
		var w = window.open('', '_blank',
			'directories=no,height=200,width=400,location=no,menubar=yes,scrollbars=yes,status=no,toolbar=no');
		w.document.write('<html><head><title>' + title + '</title></head><body bgcolor="#ffffff">');
		w.document.write(value);
		w.document.write('<form><input type="button" onClick="window.close()" value="Close"></form></body></html>');
	}
	// --></script>"""

	traceback_summary = []

	for frame, file, lnum, func, lines, index in inspect_trace:
		if file:
			file = os.path.abspath(file)
		else:
			file = "not found"
		traceback_summary.append('<a href="#%s%i" style="%s">%s</a>:'
			'<tt style="font-family:Courier,sans-serif">%s</tt>'
			% (file.replace('/', '_').replace('\\', '_'), lnum,
				opt['header'], os.path.splitext(os.path.basename(file))[0],
				("%5i" % lnum).replace(' ', '&nbsp;')))

	head = ('<table width="100%%" style="%s" cellspacing="0" cellpadding="2" border="0">'
		'<tr><td valign="top" align="left">'
		'<strong style="font-size:x-large">%s</strong>: %s</td>'
		'<td rowspan="2" valign="top" align="right">%s</td></tr>'
		'<tr><td valign="top" bgcolor="#ffffff">\n'
		'<p style="%s">A problem occurred while running a Python script.</p>'
		'<p style="%s">Here is the sequence of function calls leading up to'
		' the error, with the most recent (innermost) call first.</p>\n'
		'</td></tr></table>\n'
		% (opt['header'], str(etype), pydoc.html.escape(str(evalue)),
		'<br>\n'.join(traceback_summary), opt['default'], opt['default']))

	indent = '<tt><small>%s</small>&nbsp;</tt>' % ('&nbsp;' * 5)
	traceback = []
	for frame, file, lnum, func, lines, index in inspect_trace:
		if file:
			file = os.path.abspath(file)
		else:
			file = "not found"
		try:
			file_list = file.split('/')
			display_file = '/'.join(
				file_list[file_list.index("Webware") + 1:])
		except ValueError:
			display_file = file
		if display_file[-3:] == ".py":
			display_file = display_file[:-3]
		link = '<a name="%s%i"></a><a href="file:%s">%s</a>' % (
			file.replace('/', '_').replace('\\', '_'),
			lnum, file, pydoc.html.escape(display_file))
		args, varargs, varkw, locals = inspect.getargvalues(frame)
		if func == '?':
			call = ''
		else:
			call = 'in <strong>%s</strong>' % func + inspect.formatargvalues(
				args, varargs, varkw, locals,
				formatvalue=lambda value: '=' + html_repr(value))

		names = []
		dotted = [0, []]
		def tokeneater(type, token, start, end, line, names=names, dotted=dotted):
			if type == tokenize.OP and token == ".":
				dotted[0] = 1
			if type == tokenize.NAME and token not in keyword.kwlist:
				if dotted[0]:
					dotted[0] = 0
					dotted[1].append(token)
					if token not in names:
						names.append(dotted[1][:])
				elif token not in names:
					if token != "self": names.append(token)
					dotted[1] = [token]
			if type == tokenize.NEWLINE: raise IndexError
		def linereader(file=file, lnum=[lnum]):
			line = linecache.getline(file, lnum[0])
			lnum[0] = lnum[0] + 1
			return line

		try:
			tokenize.tokenize(linereader, tokeneater)
		except IndexError: pass
		lvals = []
		for name in names:
			if type(name) is type([]):
				if locals.has_key(name[0]) or frame.f_globals.has_key(name[0]):
					name_list, name = name, name[0]
					if locals.has_key(name_list[0]):
						value = locals[name_list[0]]
					else:
						value = frame.f_globals[name_list[0]]
						name = "<em>global</em> %s" % name
					for subname in name_list[1:]:
						if hasattr(value, subname):
							value = getattr(value, subname)
							name = name + "." + subname
						else:
							name = name + "." + "(unknown: %s)" % subname
							break
					name = '<strong>%s</strong>' % name
					if type(value) is types.MethodType and 1:
						value = None
					else:
						value = html_repr(value)
			elif name in frame.f_code.co_varnames:
				if locals.has_key(name):
					value = html_repr(locals[name])
				else:
					value = '<em>undefined</em>'
				name = '<strong>%s</strong>' % name
			else:
				if frame.f_globals.has_key(name):
					value = html_repr(frame.f_globals[name])
				else:
					value = '<em>undefined</em>'
				name = '<em>global</em> <strong>%s</strong>' % name
			if value is not None:
				lvals.append('%s&nbsp;= %s' % (name, value))
		if lvals:
			lvals = ', '.join(lvals)
			lvals = indent + '<span style="%s">%s</span><br>\n' % (
				opt['code.unaccent'], lvals)
		else:
			lvals = ''

		level = ('<br><table width="100%%" style="%s"'
			' cellspacing="0" cellpadding="2" border="0">'
			'<tr><td>%s %s</td></tr></table>'
			% (opt['subheader'], link, call))
		excerpt = []
		try:
			i = lnum - index
		except TypeError:
			i = lnum
		lines = lines or ['file not found']
		for line in lines:
			number = '&nbsp;' * (5-len(str(i))) + str(i)
			number = '<span style="%s">%s</span>' % (
				opt['code.unaccent'], number)
			line = '<tt>%s&nbsp;%s</tt>' % (
				number, pydoc.html.preformat(line))
			if i == lnum:
				line = ('<table width="100%%" style="%s"'
					' cellspacing="0" cellpadding="0" border="0">'
					'<tr><td>%s</td></tr></table>'
					% (opt['code.accent'], line))
			excerpt.append('\n' + line)
			if i == lnum:
				excerpt.append(lvals)
			i = i + 1
		traceback.append(level + '\n'.join(excerpt))

	exception = '<p><strong>%s</strong>: %s\n' % (str(etype), str(evalue))
	attribs = []
	if type(evalue) is types.InstanceType:
		for name in dir(evalue):
			value = html_repr(getattr(evalue, name))
			attribs.append('<br>%s%s&nbsp;= %s\n' % (indent, name, value))
	return javascript + head + ''.join(traceback) \
		+ exception + ''.join(attribs) + '</p>\n'

def handler():
	print breaker()
	print html()

def html_repr(value):
	html_repr_instance = pydoc.html._repr_instance
	enc_value = pydoc.html.repr(value)
	if len(enc_value) > html_repr_instance.maxstring:
		plain_value = pydoc.html.escape(repr(value))
		return ('%s <a href="#" onClick="popup_repr(\'Long repr\','
			' \'Full representation:&lt;br&gt;\\n%s\');'
			' return false">(complete)</a>'
			% (enc_value, pydoc.html.escape(plain_value).replace(
				"'", "\\'").replace('"', '&quot;')))
	else:
		return enc_value

if __name__ == '__main__':
	try:
		import tester
	except:
		handler()
