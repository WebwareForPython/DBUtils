#!/usr/bin/env python

#-----------------------------------------------------------------------------
# Name:        LRWPAdapter.py
#
# Purpose:     LRWP Adapter for the WebKit AppServer and the Xitami Web Server.
#              Adapted from the CGI Adapter for WebKit.
#
# Author:      Jim Madsen
#
# Created:     09/27/02
#-----------------------------------------------------------------------------

# Set Program Parameters

webwareDir = None

LRWPappName = 'testing'

LRWPhost = 'localhost'

LRWPport = 81

#-----------------------------------------------------------------------------

import os, sys
from lrwplib import LRWP
from Adapter import Adapter


if not webwareDir:
	webwareDir = os.path.dirname(os.path.dirname(os.getcwd()))
sys.path.insert(1, webwareDir)
webKitDir = os.path.join(webwareDir, 'WebKit')


class LRWPAdapter(Adapter):

	def __init__(self, webkitdir):
		Adapter.__init__(self, webkitdir)
		if sys.platform == 'win32':
			import msvcrt
			msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
			msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
		# Get Host and Port information for WebKit AppServer
		(self.host, self.port) = open(os.path.join(self._webKitDir, 'adapter.address')).read().split(':')
		self.port = int(self.port)

	def lrwpConnect(self, LRWPappName, LRWPhost, LRWPport):
		try:
			#Make connection to Xitami
			self.lrwp = LRWP(LRWPappName, LRWPhost, LRWPport)
			self.lrwp.connect()
			print ('\r\n Connected to Xitami -- Listening for ' + LRWPappName + '\r\n')
			self.LRWPappName = LRWPappName
		except:
			sys.exit('Could not make proper connection to Xitami')


	def handler(self):
		while 1:
			try:
				# Accept requests
				self.request = self.lrwp.acceptRequest()
				# Read input from request object
				self.myInput = ''
				if self.request.env.has_key('CONTENT_LENGTH'):
					length = int(self.request.env['CONTENT_LENGTH'])
					self.myInput = self.myInput + self.request.inp.read(length)
				# Fix environment variables due to the way Xitami reports them under LRWP
				self.request.env['SCRIPT_NAME'] = ('/' + self.LRWPappName)
				self.request.env['REQUEST_URI'] = ('/' + self.LRWPappName + self.request.env['PATH_INFO'])
				# Transact with the app server
				self.response = self.transactWithAppServer(self.request.env, self.myInput, self.host, self.port)
				# Log page handled to the console
				print self.request.env['REQUEST_URI']
				# Close request to handle another
				self.request.finish()
			# Capture Ctrl-C... Shutdown will occur on next request handled
			except KeyboardInterrupt:
				print '\r\n Closing connection to Xitami \r\n'
				self.lrwp.close()
				sys.exit(' Clean Exit')
			except:
				print 'Error handling requests'

	# Output through request object
	def processResponse(self, data):
		self.request.out.write(data)


def main():
	# Startup LRWP to WebKit interface
	lrwpInterface = LRWPAdapter(webKitDir)
	lrwpInterface.lrwpConnect(LRWPappName, LRWPhost, LRWPport)
	lrwpInterface.handler()


if __name__ == '__main__':
	main()
