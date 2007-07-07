import sys, os
from types import DictType
from MiscUtils import AbstractError, NoDefault
from Funcs import valueForString


class ConfigurationError(Exception):
	pass


class Configurable:
	"""Abstract superclass for configuration file functionality.

	Subclasses should override:

		* defaultConfig()  to return a dictionary of default settings
		                   such as { 'Frequency': 5 }

		* configFilename() to return the filename by which users can
		                   override the configuration such as
		                   'Pinger.config'

	Subclasses typically use the setting() method, for example:

		time.sleep(self.setting('Frequency'))

	They might also use the printConfig() method, for example:

		self.printConfig()      # or
		self.printConfig(file)

	Users of your software can create a file with the same name as
	configFilename() and selectively override settings. The format of
	the file is a Python dictionary.

	Subclasses can also override userConfig() in order to obtain the
	user configuration settings from another source.

	"""


	## Init ##

	def __init__(self):
		self._config = None


	## Configuration

	def config(self):
		"""Return the configuration of the object as a dictionary.

		This is a combination of defaultConfig() and userConfig().
		This method caches the config.

		"""
		if self._config is None:
			self._config = self.defaultConfig()
			self._config.update(self.userConfig())
			self._config.update(self.commandLineConfig())
		return self._config

	def setting(self, name, default=NoDefault):
		"""Return the value of a particular setting in the configuration."""
		if default is NoDefault:
			try:
				return self.config()[name]
			except KeyError:
				raise KeyError, \
					'%s config keys are: %s' % (name, self.config().keys())
		else:
			return self.config().get(name, default)

	def setSetting(self, name, value):
		"""Set a particular configuration setting."""
		self.config()[name] = value

	def hasSetting(self, name):
		"""Check whether a configuration setting has been changed."""
		return self.config().has_key(name)

	def defaultConfig(self):
		"""Return a dictionary with all the default values for the settings.

		This implementation returns {}. Subclasses should override.

		"""
		return {}

	def configFilename(self):
		"""Return the full name of the user config file.

		Users can override the configuration by this config file.
		Subclasses must override to specify a name.
		Returning None is valid, in which case no user config file
		will be loaded.

		"""
		raise AbstractError, self.__class__

	def configName(self):
		"""Return the name of the configuration file without the extension.

		This is the portion of the config file name before the '.config'.
		This is used on the command-line.

		"""
		return os.path.splitext(os.path.basename(self.configFilename()))[0]

	def configReplacementValues(self):
		"""Return a dictionary for substitutions in the config file.

		This must be a dictionary suitable for use with "string % dict"
		that should be used on the text in the config file.
		If an empty dictionary (or None) is returned, then no substitution
		will be attempted.

		"""
		return {}

	def userConfig(self):
		"""Return the user config overrides.

		These settings can be found in the optional config file.
		Returns {} if there is no such file.

		The config filename is taken from configFilename().

		"""
		filename = self.configFilename()
		if not filename:
			return {}
		try:
			# open the config file in universal newline mode,
			# in case it has been edited on a different platform
			contents = open(filename, 'rU').read()
		except IOError, e:
			print 'WARNING: Config file', filename
			print '  not loaded: %s.' % e.strerror
			print
			return {}
		isDict = contents.lstrip().startswith('{')
		from WebKit.AppServer import globalAppServer
		if globalAppServer:
			globalAppServer._imp.watchFile(filename)
		replacements = self.configReplacementValues()
		if replacements and isDict:
			try:
				contents %= replacements
			except:
				raise ConfigurationError, \
					'Unable to embed replacement text in %s.' % filename
		evalContext = replacements.copy()
		try:
			True, False
		except NameError: # Python < 2.3
			evalContext['True'] = 1
			evalContext['False'] = 0
		try:
			if isDict:
				config = eval(contents, evalContext)
			else:
				exec contents in evalContext
				config = evalContext
				for name in config.keys():
					if name.startswith('_'):
						del config[name]
		except Exception, e:
			raise ConfigurationError, \
				'Invalid configuration file, %s (%s).' % (filename, e)
		if type(config) is not DictType:
			raise ConfigurationError, 'Invalid type of configuration.' \
				' Expecting dictionary, but got %s.' % type(config)
		try:
			True, False
		except NameError: # Python < 2.3
			del evalContext['True']
			del evalContext['False']
		return config

	def printConfig(self, dest=None):
		"""Print the configuration to the given destination.

		The default destionation is stdout. A fixed with font is assumed
		for aligning the values to start at the same column.

		"""
		if dest is None:
			dest = sys.stdout
		keys = self.config().keys()
		keys.sort()
		width = max(map(len, keys))
		for key in keys:
			dest.write('%s = %s\n'
				% (key.ljust(width), str(self.setting(key))))
		dest.write('\n')

	def commandLineConfig(self):
		"""Return the settings that came from the command-line.

		These settings come via addCommandLineSetting().

		"""
		return _settings.get(self.configName(), {})


## Command line settings ##

_settings = {}

def addCommandLineSetting(name, value):
	"""Override the configuration with a command-line setting.

	Take a setting, like "AppServer.Verbose=0", and call
	addCommandLineSetting('AppServer.Verbose', '0'), and
	it will override any settings in AppServer.config

	"""
	configName, settingName = name.split('.', 1)
	value = valueForString(value)
	if not _settings.has_key(configName):
		_settings[configName] = {}
	_settings[configName][settingName] = value

def commandLineSetting(configName, settingName, default=NoDefault):
	"""Retrieve a command-line setting.

	You can use this with non-existent classes, like "Context.Root=/WK",
	and then fetch it back with commandLineSetting('Context', 'Root').

	"""
	if default is NoDefault:
		return _settings[configName][settingName]
	else:
		return _settings.get(configName, {}).get(settingName, default)
