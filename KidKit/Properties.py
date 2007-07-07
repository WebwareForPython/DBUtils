name = 'KidKit'

version = ('X', 'Y', 0)

docs = [{'name': "User's Guide", 'file': 'UsersGuide.html'}]

status = 'beta'

requiredPyVersion = (2, 3, 0)

requiredSoftware = [{'name': 'kid', 'version': (0, 6, 0)}]

synopsis = """KidKit is a Webware plug-in that allows Kid templates
to be automatically compiled and run as servlets by the WebKit application server.
Kid is a simple templating language for XML based vocabularies written in Python.
You need to install the Kid package before you can use the KidKit plug-in."""

WebKitConfig = {
	'examplePages': [
		'Welcome', 'Time1', 'Time2', 'Files',
		'ServletInfo', 'SimpleForm', 'MandelbrotSet',
	]
}

def willRunFunc():
	# WebKit doesn't check requiredSoftware yet. So we do so:
	try:
		for soft in requiredSoftware:
			__import__(soft['name'])
	except ImportError:
		success = 0
	else:
		# The required version will be checked in __init__.py.
		success = 1
	if not success:
		return 'The kid package is required to use KidKit.'
