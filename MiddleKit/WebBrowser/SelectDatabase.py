from MiscUtils.DataTable import DataTable
from MiscUtils.Funcs import hostName as HostName
from SitePage import SitePage


class SelectDatabase(SitePage):

	def writeSideBar(self):
		self.writeln('<a href="?showHelp=1" class="SideBarLink">Help</a>')

	def writeContent(self):
		self.saveFieldsToCookies()
		self.writeDBForm(action='BrowseClasses')
		self.writeRecentDatabases()
		self.writeKnownDatabases()
		if self.request().hasField('showHelp'):
			self.writeHelp()

	def writeDBForm(self, method='get', action=''):
		if method:
			method = 'method="%s"' % method
		if action:
			action = 'action="%s"' % action
		source = '''\
name,type,comment,value
database,text,"e.g., MySQL"
host,text
user,text
password,password
'''
		fields = DataTable()
		fields.readString(source)
		req = self.request()
		wr = self.writeln

		self.writeHeading('Enter database connection info:')
		wr('<form %(method)s %(action)s>' % locals())
		wr('<table border="0" cellpadding="2" cellspacing="0">')
		for field in fields:
			field['value'] = req.value(field['name'], '')
			wr('<tr><td>%(name)s:</td><td></td><td>'
				'<input type="%(type)s" name="%(name)s" value="%(value)s">'
				'</td><td>%(comment)s</td></tr>' % field)
		wr('<tr><td colspan="2">&nbsp;</td><td align="right">'
			'<input type="submit" value="OK"></td><td>&nbsp;</td></tr>')
		wr('</table></form>')

	def writeRecentDatabases(self):
		self.writeHeading('Select a recent database:')
		self.writeln('<p>None</p>')

	def writeKnownDatabases(self):
		self.writeHeading('Select a known database:')
		knownDBs = self.setting('KnownDatabases')
		hostName = HostName()
		if not hostName:
			hostName = '_default_'
		dbs = knownDBs.get(hostName, []) + knownDBs.get('_all_', [])
		if dbs:
			for db in dbs:
				self.writeDB(db)
		else:
			self.writeln('<p>None</p>')

	def writeDB(self, db):
		# Set title
		title = '%(database)s on %(host)s' % db
		if db.get('user', ''):
			title += ' with ' + db['user']

		# Build up args for links
		args = []
		for key in self.dbKeys():
			if db.has_key(key):
				args.append('%s=%s' % (key, db[key]))
		args = '&'.join(args)

		# If the db connection info specifies a password, then
		# the user can click through immediately.
		# Otherwise, the click goes back to the same page with
		# the fields filled out so that the user can enter the password.
		if db.get('password', None):
			self.write('<p><a href="BrowseClasses?%s">%s</a>'
				' (password included)' % (args, title))
		else:
			self.writeln('<p><a href="?%s">%s</a>'
				' (password required)' % (args, title))

	def dbKeys(self):
		"""Get keys for database connections.

		Returns a list of the valid keys that can be used for a
		"database connection dictionary". These dictionaries are
		found in the config file and in the recent list.

		"""
		return ['database', 'host', 'user', 'password']
