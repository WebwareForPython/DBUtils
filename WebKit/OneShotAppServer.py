#!/usr/bin/env python

"""OneShotAppServer

This version of the app server is in support of the OneShot adapter.

This class creates an application that has no session sweeper thread,
and it provides the convenience method dispatchRawRequest().

See also: OneShot.cgi and OneShotAdapter.py.

"""

from AppServer import AppServer
from Application import Application


class OneShotAppServer(AppServer):

	def __init__(self, path=None):
		AppServer.__init__(self, path)
		self.readyForRequests()

	def recordPID(self):
		self._pidFile = None

	def isPersistent(self):
		return 0

	def createApplication(self):
		return Application(server=self, useSessionSweeper=0)

	def dispatchRawRequest(self, newRequestDict, strmOut):
		self._requestID += 1
		newRequestDict['requestID'] = self._requestID
		return self._app.dispatchRawRequest(newRequestDict, strmOut)
