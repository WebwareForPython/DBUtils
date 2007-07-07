import os
from MiscUtils.Funcs import hostName as HostName
from SitePage import SitePage


class SelectModel(SitePage):

	def writeSideBar(self):
		self.writeln('<a href="?showHelp=1" class="SideBarLink">Help</a>')

	def writeContent(self):
		self.writeModelForm()
		self.writeRecentModels()
		self.writeKnownModels()
		if self.request().hasField('showHelp'):
			self.writeHelp()

	def writeModelForm(self, method='get', action='SelectDatabase'):
		self.writeHeading('Enter a model filename:')
		if method:
			method = 'method="%s"' % method
		if action:
			action = 'action="%s"' % action
		value = self.request().value('modelFilename', None)
		if value:
			value = 'value="%s"' % value
		self.writeln('''
<form %(method)s %(action)s>
	<!-- Model filename: -->
	<input type="text" name="modelFilename" size="50" %(value)s>
	&nbsp;
	<input type="submit" value="OK">
</form>
''' % locals())

	def writeRecentModels(self):
		wr = self.writeln
		self.writeHeading('Select a recent model:')
		recentModels = self.request().cookie('recentModels', [])
		if recentModels:
			recentModels = recentModels.split(';')
		if recentModels:
			for modelFilename in recentModels:
				self.writeModelLink(modelFilename)
		else:
			wr('<p>None</p>')

	def writeKnownModels(self):
		wr = self.writeln
		self.writeHeading('Select a known model:')
		knownModels = self.setting('KnownModels')
		hostName = HostName()
		if not hostName:
			hostName = '_default_'
		filenames = knownModels.get(hostName, []) + knownModels.get('_all_', [])
		if filenames:
			for filename in filenames:
				self.writeModelLink(filename)
		else:
			wr('<p>None</p>')

	def writeModelLink(self, filename):
		prettyName = os.path.split(filename)
		prettyName = '%s - %s' % (prettyName[1], prettyName[0])
		self.writeln('<p><a href="SelectDatabase?modelFilename=%s">%s</a></p>'
			% (filename, prettyName))
