import os
import unittest
from WebKit.Tests.AppServerTest import AppServerTest


class TestBasicFunctionality(AppServerTest):

	def workDir(self):
		return os.path.dirname(os.path.join(os.getcwd(), __file__))

	def testAppServerStarts(self):
		pass


if __name__ == '__main__':
	unittest.main()
