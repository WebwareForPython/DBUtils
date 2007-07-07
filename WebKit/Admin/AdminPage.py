import os

from WebKit.SidebarPage import SidebarPage


class AdminPage(SidebarPage):
	"""AdminPage

	This is the abstract superclass of all WebKit administration pages.

	Subclasses typically override title() and writeContent(), but may
	customize other methods.

	"""

	def cornerTitle(self):
		return 'WebKit AppServer'

	def writeSidebar(self):
		self.writeAdminMenu()
		self.writeWebKitSidebarSections()

	def writeAdminMenu(self):
		self.menuHeading('Admin')
		self.menuItem('Home', 'Main')
		self.menuItem('Activity log', 'Access',
			self.fileSize('ActivityLogFilename'))
		self.menuItem('Error log', 'Errors',
			self.fileSize('ErrorLogFilename'))
		self.menuItem('Config', 'Config')
		self.menuItem('Plug-ins', 'PlugIns')
		self.menuItem('Servlet cache', 'ServletCache')
		self.menuItem('Application Control', 'AppControl')
		self.menuItem('Logout', 'Main?logout=yes')

	def fileSize(self, filename):
		"""Utility method for writeMenu() to get the size of a configuration file.

		Returns an HTML string.

		"""
		filename = self.application().setting(filename)
		if os.path.exists(filename):
			size = '%0.0f KB' % (os.path.getsize(filename)/1024.0)
		else:
			size = 'not existent'
		return '<span style="font-size:smaller">(%s)</span>' % size

	def loginDisabled(self):
		"""Return None if login is enabled, else a message about why not."""
		if self.application().setting('AdminPassword'):
			return None
		return '<p>Logins to admin pages are disabled until' \
			' you supply an AdminPassword in Application.config.</p>'
