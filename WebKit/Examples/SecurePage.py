from ExamplePage import ExamplePage
from MiscUtils.Configurable import Configurable


class SecurePage(ExamplePage, Configurable):
	"""Password-based security example.

	This class is an example of how to implement username and password-based
	security using WebKit. Use a SecurePage class like this one as the
	base class for any pages that you want to require login. Modify
	the isUserNameAndPassword method to perform validation in whatever
	way you desire, such as a back-end database lookup. You might also
	want to modify loginUser so that it automatically brings in additional
	information about the user and stores it in session variables.

	You can turn off security by creating a config file called SecurePage.config
	in the Configs directory with the following contents:

		RequireLogin = 0

	To do: Integrate this functionality with the upcoming UserKit.
	Make more of the functionality configurable in the config file.

	"""

	def __init__(self):
		ExamplePage.__init__(self)
		Configurable.__init__(self)

	def awake(self, trans):
		ExamplePage.awake(self, trans) # awaken our superclass
		if self.setting('RequireLogin'):
			# Handle four cases: login attempt, logout, already logged in, and not already logged in.
			session = trans.session()
			request = trans.request()
			app = trans.application()
			# Are they logging out?
			if request.hasField('logout'):
				# They are logging out. Clear all session variables:
				session.values().clear()
				request.setField('extra', 'You have been logged out.')
				request.setField('action', request.urlPath().split('/')[-1])
				app.forward(trans, 'LoginPage')
			# Is the session expired?
			elif request.isSessionExpired():
				# Login page with a "logged out" message.
				session.values().clear()
				request.setField('extra', 'Your session has expired.')
				request.setField('action', request.urlPath().split('/')[-1])
				app.forward(trans, 'LoginPage')
			# Are they already logged in?
			elif self.loggedInUser():
				return
			# Are they logging in?
			elif request.hasField('login') \
					and request.hasField('username') \
					and request.hasField('password'):
				# They are logging in. Get login id and clear session:
				loginid = session.value('loginid', None)
				session.values().clear()
				# Get request fields:
				username = request.field('username')
				password = request.field('password')
				# Check if they can successfully log in.
				# The loginid must match what was previously sent.
				if request.field('loginid', 'nologin') == loginid \
					and self.loginUser(username, password):
					# Successful login.
					# Clear out the login parameters:
					request.delField('username')
					request.delField('password')
					request.delField('login')
					request.delField('loginid')
				else:
					# Failed login attempt; have them try again:
					request.setField('extra', 'Login failed. Please try again.')
					request.setField('action', request.urlPath().split('/')[-1])
					app.forward(trans, 'LoginPage')
			else:
				# They need to log in.
				session.values().clear()
				# Send them to the login page:
				request.setField('action', request.urlPath().split('/')[-1])
				app.forward(trans, 'LoginPage')
		else:
			# No login is required.
			session = self.session()
			request = self.request()
			# Are they logging out?
			if request.hasField('logout'):
				# They are logging out.  Clear all session variables.
				session.values().clear()
			# Write the page:
			ExamplePage.writeHTML(self)

	def respond(self, trans):
		# If the user is already logged in, then process this request normally.
		# Otherwise, do nothing.
		# All of the login logic has already happened in awake().
		if self.loggedInUser():
			ExamplePage.respond(self, trans)

	def isValidUserAndPassword(self, username, password):
		# Replace this with a database lookup,
		# or whatever you're using for authentication...
		users = ('alice', 'bob')
		return username.lower() in users and password == username

	def loginUser(self, username, password):
		# We mark a user as logged-in by setting a session variable
		# called authenticated_user to the logged-in username.
		# Here, you could also pull in additional information about
		# this user (such as a user ID or user preferences) and store
		# that information in session variables.
		if self.isValidUserAndPassword(username, password):
			self.session().setValue('authenticated_user', username)
			return 1
		else:
			self.session().setValue('authenticated_user', None)
			return 0

	def loggedInUser(self):
		# Gets the name of the logged-in user, or returns None
		# if there is no logged-in user.
		return self.session().value('authenticated_user', None)

	def defaultConfig(self):
		return {'RequireLogin': 1}

	def configFilename(self):
		return 'Configs/SecurePage.config'
