from AdminSecurity import AdminSecurity


class PlugIns(AdminSecurity):

	def writeContent(self):
		# @@ 2000-06-02 ce: We should allow a custom admin link
		# for each plug-in (if it provides one)
		# @@ 2001-01-25 ce: We should pick up more of the info
		# in plugIn.properties()
		wr = self.writeln
		plugIns = self.application().server().plugIns()
		if plugIns:
			wr('<h4 style="text-align:center">'
				'The following Plug-ins were found:</h4>')
			path = self.request().servletPath()
			wr('<table cellspacing="2" cellpadding="2" align="center"'
				' style="margin-left:auto;margin-right:auto">')
			wr('<tr style="background-color:#555;color:white">'
				'<th colspan="3">Plug-ins</th></tr>')
			wr('<tr style="background-color:#DDD">'
				'<th>Name</th><th>Version</th><th>Directory</th></tr>')
			for plugIn in plugIns:
				name, dir, ver = plugIn.name(), plugIn.directory(), \
					plugIn.properties()['versionString']
				wr('<tr style="background-color:#EEE;text-align:left">'
					'<td><a href="%(path)s/%(name)s/Docs/index.html">'
					'%(name)s</a></td>'
					'<td style="text-align:center">%(ver)s</td>'
					'<td>%(dir)s</td></tr>' % locals())
			self.writeln('</table>')
		else:
			wr('<h4 style="text-align:center">No Plug-ins found.</h4>')
