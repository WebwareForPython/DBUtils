from WebKit.HTTPServlet import HTTPServlet


class Forward3(HTTPServlet):

	def respond(self, trans):
		trans.application().forward(trans, '../Forward3Target' + trans.request().extraURLPath())
