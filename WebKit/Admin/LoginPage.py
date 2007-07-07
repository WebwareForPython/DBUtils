from random import randint
from time import time, localtime

from AdminPage import AdminPage


class LoginPage(AdminPage):
	"""The log-in screen for the admin pages."""

	def writeContent(self):
		if self.loginDisabled():
			self.write(self.loginDisabled())
			return
		self.writeln('<div style="margin-left:auto;margin-right:auto;width:20em">'
			'<p>&nbsp;</p>')
		extra = self.request().field('extra', None)
		if extra:
			self.writeln('<p style="color:#333399">%s</p>' % self.htmlEncode(extra))
		self.writeln('''<p>Please log in to view Administration Pages.
The username is <tt>admin</tt>. The password has been set during installation and is
stored in the <tt>Application.config</tt> file in the <tt>WebKit/Configs</tt> directory.</p>
<form method="post">
<table cellpadding="4" cellspacing="4" style="background-color:#CCCCEE;border:1px solid #3333CC;width:20em">
<tr><td align="right"><label for="username">Username:</label></td>
<td><input type="text" name="username" value="admin"></td></tr>
<tr><td align="right"><label for="password">Password:</label></td>
<td><input type="password" name="password" value=""></td></tr>
<tr><td colspan="2" align="right"><input type="submit" name="login" value="Login"></td></tr>
</table>''')
		for name, value in self.request().fields().items():
			if name.lower() not in ('username', 'password', 'login', 'logout', 'loginid'):
				if type(value) != type([]):
					value = [value]
				for v in value:
					self.writeln('<input type="hidden" name="%s" value="%s">' % (name, v))
		if self.session().hasValue('loginid'):
			loginid = self.session().value('loginid')
		else:
			# Create a "unique" login id and put it in the form as well as in the session.
			# Login will only be allowed if they match.
			loginid = ''.join(map(lambda x: '%02d' % x,
					localtime(time())[:6])) + str(randint(10000, 99999))
			self.session().setValue('loginid', loginid)
		self.writeln('<input type="hidden" name="loginid" value="%s">' % loginid)
		self.writeln('</form>\n<p>&nbsp;</p></div>')
