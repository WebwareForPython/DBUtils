from WebKit.HTTPServlet import HTTPServlet


class Forward1(HTTPServlet):

	def respond(self, trans):
		trans.application().forward(trans, 'Forward1Target' + trans.request().extraURLPath())
