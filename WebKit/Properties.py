name = 'WebKit'

version = ('X', 'Y', 0)

docs = [
	{'name': 'Install Guide', 'file': 'InstallGuide.html'},
	{'name': "User's Guide", 'file': 'UsersGuide.html'},
	{'name': 'Configuration Guide', 'file': 'Configuration.html'},
	{'name': 'Beginner Tutorial', 'file': 'Tutorial.html'},
	{'name': 'Application Development', 'file': 'ApplicationDevelopment.html'},
	{'name': 'Developing Webware', 'file': 'Developing.html'},
	{'name': 'Future Work', 'file': 'Future.html'},
]

status = 'beta'

requiredPyVersion = (2, 0, 0)

synopsis = """WebKit provides Python classes for generating dynamic content from a web-based, server-side application. It is a significantly more powerful alternative to CGI scripts for application-oriented development, while still being nearly as easy to use as CGI. WebKit is analogous to NeXT/Apple's WebObjects and Sun's Servlets."""

WebKitConfig = {
	'examplePages': [
		'Welcome',
		'ShowTime',
		'CountVisits',
		'Error',
		'View',
		'Introspect',
		'Colors',
		'ListBox',
		'Forward',
		'SecureCountVisits',
		'FileUpload',
		'PushServlet',
		'RequestInformation',
		'Image',
		'AjaxSuggest',
	]
}
