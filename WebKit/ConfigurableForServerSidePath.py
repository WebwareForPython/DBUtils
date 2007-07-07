from MiscUtils.Configurable import Configurable, NoDefault


class ConfigurableForServerSidePath(Configurable):

	"""
	This is a version of `MiscUtils.Configurable.Configurable`
	that provides a customized `setting` method for classes which
	have a `serverSidePath` method. If a setting's name ends with
	``Filename`` or ``Dir``, its value is passed through
	`serverSidePath` before being returned.

	In other words, relative filenames and directory names are
	expanded with the location of the object, NOT the current
	directory.

	Application and AppServer are two well known users of this
	mix-in. Any class that has a `serverSidePath` method and a
	`Configurable` base class, should inherit this class instead.

	This is used with for MakeAppWorkDir, which changes the
	serverSidePath.
	"""

	def setting(self, name, default=NoDefault):
		"""
		Returns the setting, filtered by
		self.serverSidePath(), if the name ends with
		``Filename`` or ``Dir``.
		"""

		value = Configurable.setting(self, name, default)
		if name[-8:] == 'Filename' or name[-3:] == 'Dir':
			value = self.serverSidePath(value)
		return value
