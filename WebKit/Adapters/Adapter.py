import os, sys, time, socket
from marshal import dumps
from WebKit.Object import Object
from MiscUtils.Configurable import Configurable
import struct


class Adapter(Configurable, Object):

	def __init__(self, webKitDir):
		Configurable.__init__(self)
		Object.__init__(self)
		self._webKitDir = webKitDir
		self._respData = []

	def name(self):
		return self.__class__.__name__

	def defaultConfig(self):
		return {
			'NumRetries':            20,
			'SecondsBetweenRetries': 3
		}

	def configFilename(self):
		return os.path.join(self._webKitDir, 'Configs', '%s.config' % self.name())

	def transactWithAppServer(self, env, myInput, host, port):
		"""Get response from the application server.

		Used by subclasses that are communicating with a separate app server
		via socket. Returns the unmarshaled response dictionary.

		"""
		dict = {
				'format': 'CGI',
				'time':   time.time(),
				'environ': env,
				}

		# @@ gat 2002-03-21: Changed retry strategy.  Now, we'll only retry the initial
		# connection to the appserver.  After that, any failure means the request failed.
		# This is to avoid processing a request twice.
		retries = 0
		while 1:
			try:
				# Send our request to the AppServer
				s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				s.connect((host, port))
				break
			except socket.error:
				# Retry
				if retries <= self.setting('NumRetries'):
					retries += 1
					time.sleep(self.setting('SecondsBetweenRetries'))
				else:
					raise 'timed out waiting for connection to app server'

		data = dumps(dict)
		s.send(dumps(int(len(data))))
		s.send(data)

		sent = 0
		inputLength = len(myInput)
		while sent < inputLength:
			chunk = s.send(myInput[sent:])
			sent += chunk
		s.shutdown(1)

		# Get the response from the AppServer
		bufsize = 8*1024
		# @@ 2000-04-26 ce: this should be configurable, also we should run some tests on different sizes
		# @@ 2001-01-25 jsl: It really doesn't make a massive difference.  8k is fine and recommended.

		# Wait for 0.5 seconds for data:
		# s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, struct.pack('ll',0,5))

		while 1:
			data = s.recv(bufsize)
			if not data:
				break
			self.processResponse(data)

		return ''.join(self._respData)

	def processResponse(self, data):
		"""Process response data as it arrives."""
		self._respData.append(data)
