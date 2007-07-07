from WebKit.HTTPServlet import HTTPServlet


class index(HTTPServlet):

	def respond(self, trans):
		newPath = 'Welcome' + trans.request().extraURLPath()
		# redirection via the server:
		trans.application().forward(trans, newPath)
		# redirection via the client:
		# trans.response().sendRedirect(newPath)
