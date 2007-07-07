from WebKit.HTTPServlet import HTTPServlet


class Forward2(HTTPServlet):

	def respond(self, trans):
		trans.application().forward(trans, 'Dir/Forward2Target' + trans.request().extraURLPath())
