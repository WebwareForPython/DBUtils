<?xml version='1.0' encoding='utf-8'?>
<?python
from KidKit.Examples.KidExamplePage import KidExamplePage
hook = KidExamplePage.writeContent
import os
def show(s):
	return repr(s).replace(r'\\', '\\').replace(';', '; ').replace(':/', ': /')
?>
<body py:strip="" xmlns:py="http://purl.org/kid/ns#">
<h1>Kid Servlet Info</h1>
<h2>Useful Variables</h2>
<?python
variables = {
	'servlet':
		'The servlet instance',
	'servlet.request()':
		'Used to access fields and other info about the request.',
	'servlet.request().cookies()':
		'Dictionary of all Cookies the client sent with this request.',
	'servlet.request().fields()':
		'Dictionary of all form fields contained by this request.',
	'servlet.request().serverDictionary()':
		'Dictionary with the data the web server gave us.',
	'servlet.request().serverSidePath()':
		'The absolute server-side path of the request.',
	'servlet.response()':
		'Used to set cookies other info as response.',
	'servlet.response().cookies()':
		'Dictionary of all cookies that will be sent with this response.',
	'servlet.response().headers()':
		'Dictionary of all headers contained by this request.',
	'__file__':
		'The file name of this servlet as a Python module.',
	'__orig_file__':
		'The file name of the Kid template that produced this Python module.'
	}
vars = variables.keys()
vars.sort()
?>
<div py:for="var in vars">
<h4 py:content="var" />
<p style="font-size:small" py:content="show(eval(var))" />
<p py:content="variables[var]" />
</div>
<h2>Environment</h2>
<div py:for="key, value in os.environ.items()">
<h5 py:content="key" />
<p style="font-size:small" py:content="show(value)" />
</div>
</body>