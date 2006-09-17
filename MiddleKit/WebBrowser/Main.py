from SitePage import SitePage
import os, sys


class Main(SitePage):

	def writeHTML(self):
		self.response().sendRedirect('SelectModel')
