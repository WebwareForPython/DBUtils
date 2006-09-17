# KidKit
# Webware for Python

def InstallInWebKit(appServer):
	app = appServer.application()
	from WebKit.PlugIn import PlugInError
	try:
		try:
			from KidKit.Properties import requiredSoftware
		except ImportError:
			raise PlugInError, 'Cannot determine required software.'
		for soft in requiredSoftware:
			if soft['name'] == 'kid':
				requiredKidVersion = soft['version']
				break
		else:
			raise PlugInError, 'Cannot determine required Kid version.'
		try:
			import kid
		except ImportError:
			raise PlugInError, \
				'Cannot import Kid. This needs to be installed to use KidKit.'
		try:
			kidVersion = tuple(map(lambda s:
					int('0' + ''.join(filter(lambda c: c.isdigit(), s))),
				kid.__version__.split('.', 3)[:3]))
		except ImportError:
			raise PlugInError, 'Cannot determine Kid version.'
		if kidVersion < requiredKidVersion:
			raise PlugInError, \
				'KidKit needs at least Kid version %s (installed is %s).' \
				% ('.'.join(map(str, requiredKidVersion)),
					'.'.join(map(str, kidVersion)))
		try:
			from KidServletFactory import KidServletFactory
			app.addServletFactory(KidServletFactory(app))
		except:
			from traceback import print_exc
			print_exc()
			raise PlugInError, 'Cannot install Kid servlet factory.'
	except PlugInError, e:
		print e
		print "KidKit will not be loaded, '.kid' extension will be ignored."
		# We need to disable the '.kid' extension because otherwise the kid
		# templates would be delivered as ordinary files (security problem).
		e = app.setting('ExtensionsToIgnore', [])
		if '.kid' not in e:
			e.append('.kid')
			app.setSetting('ExtensionsToIgnore', e)
		e = app.setting('FilesToHide', [])
		if '*.kid' not in e:
			e.append('*.kid')
			app.setSetting('FilesToHide', e)
		from WebKit.URLParser import initParser
		initParser(app)
