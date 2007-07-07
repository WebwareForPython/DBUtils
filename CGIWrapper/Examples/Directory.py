import os
from stat import *

print '''
<html>
	<head>
		<title>Webware CGI Examples Directory</title>
	</head>
	<body>
		<p align=center><font size=+1><b>Webware CGI Examples</b></font></p>
'''

def sizeSorter(a, b):
	"""
	Used for sorting when the elements are dictionaries and the
	attribute to sort by is 'size'.
	"""
	return a['size'] - b['size']

# Create a list of dictionaries, where each dictionary stores information about
# a particular script.
scripts = []
for filename in os.listdir(os.curdir):
	if len(filename) > 3 and filename[-3:] == '.py':
		script = {}
		script['pathname']  = filename
		script['size']      = os.stat(script['pathname'])[ST_SIZE]
		script['shortname'] = filename[:-3]
		scripts.append(script)
scripts.sort(sizeSorter)

print '<p><table cellspacing=0 align=center>'
print '<tr> <th align=right>Size</th> <th align=left>Script</th> <th align=left>View</th> </tr>'

for script in scripts:
	print '<tr>',
	print '<td align=right> %d </td>' % script['size'],
	print '<td> <a href=%s>%s</a> </td>' % (script['shortname'], script['shortname']),
	print '<td> <a href=View?filename=%s>view</a> </td>' % script['shortname'],
	print '<tr>'

print '</table>'

print '''
	</body>
</html>'''
