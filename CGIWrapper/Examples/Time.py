
print '''
<html>
	<head>
		<title>Time</title>
	</head>
	<body>'''

import time

print '<p>', time.asctime(time.localtime(time.time()))

print '''
	</body>
</html>'''
