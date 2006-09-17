import os, string, time


print '''
<html>
	<head>
		<title>Webware View CGI Source</title>
	</head>
	<body>
		<p><font size=+1><b>Webware View CGI Source</b></font>
'''

if not fields.has_key('filename'):
	print '<p>No filename specified.'
else:
	if fields.has_key('tabSize'):
		tabSize = int(fields['tabSize'].value)
	else:
		tabSize = 4
	filename = fields['filename'].value
	filename = filename + '.py'
	contents = open(filename).read()
	if tabSize>0:
		contents = string.expandtabs(contents, tabSize)
	contents = string.replace(contents, '&', '&amp;')
	contents = string.replace(contents, '<', '&lt;')
	contents = string.replace(contents, '>', '&gt;')
	print '<br><i>%s</i><hr><pre>%s</pre>' % (filename, contents)

print '''
	</body>
</html>'''
