import os
from WebUtils.Funcs import htmlEncode
from MiscUtils import StringIO

def encodeWithIndentation(html):
	html = htmlEncode(html).replace('  ', '&nbsp; ')
	return html.replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')

def validateHTML(html):
	"""
	Validate the input using Web Design Group's HTML validator
	available at http://www.htmlhelp.com/tools/validator/

	Make sure you install the offline validator (called
	"validate") which can be called from the command-line.  The
	"validate" script must be in your path.

	If no errors are found, an empty string is returned.
	Otherwise, the HTML with the error messages is returned.
	"""

	input, output = os.popen4('validate')
	input.write(html)
	input.close()
	out = output.readlines()
	output.close()

	errorLines = {}
	for line in out:
		if line[0:5] == 'Line ':
			i = line.find(',')
			if i != -1:
				linenum = int(line[5:i])
				errorLines[linenum] = line

	# Be quiet if all's well
	if not errorLines:
		return ''

	result = StringIO()
	result.write('<table style="background-color: #ffffff"><tr><td colspan="2">\n')
	result.write("<pre>%s</pre>" % "".join(out))
	result.write('</td></tr>\n')

	goodColors = ['#d0d0d0', '#e0e0e0']
	badColor = '#ffd0d0'
	lines = html.splitlines(1)
	i = 1
	for line in lines:
		if errorLines.has_key(i):
			result.write('<tr style="background-color: %s">'
				'<td rowspan="2">%d</td><td>%s</td></tr>\n'
				% (badColor, i, encodeWithIndentation(errorLines[i])))
			result.write('<tr style="background-color: %s">'
				'<td>%s</td></tr>\n'
				% (badColor, encodeWithIndentation(line)))
		else:
			color = goodColors[i % 2]
			result.write('<tr style="background-color: %s">'
				'<td>%d</td><td>%s</td></tr>\n'
				% (color, i, encodeWithIndentation(line)))
		i += 1
	result.write('</table>\n')
	return result.getvalue()
