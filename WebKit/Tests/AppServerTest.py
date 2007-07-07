import unittest
import os
import time
from re import compile as reCompile
from threading import Thread
from Queue import Queue, Empty
from urllib import urlopen

try: # for Python < 2.3
	True, False
except NameError:
	True, False = 1, 0


class AppServerTest(unittest.TestCase):

	def setUp(self):
		"""Setup fixture and test starting."""
		workdir = self.workDir()
		dirname = os.path.dirname
		webwaredir = dirname(dirname(dirname(workdir)))
		launch = os.path.join(workdir, 'Launch.py')
		cmd = "python %s --webware-dir=%s --work-dir=%s" \
			" ThreadedAppServer" % (launch, webwaredir, workdir)
		self._output = os.popen(cmd)
		# Setting the appserver output to non-blocking mode
		# could be done as follows on Unix systems:
		# fcntl.fcntl(self._output.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)
		# But, since this does not work on Windows systems,
		# we will pull the output in a separate thread:
		def pullStream(stream, queue):
			while stream:
				line = stream.readline()
				if not line:
					break
				queue.put(line)
		self._queue = Queue()
		self._thread = Thread(target=pullStream,
			args=(self._output, self._queue))
		self._thread.start()
		self.assertAppServerSays('^WebKit AppServer ')
		self.assertAppServerSays(' Webware for Python.$')
		self.assertAppServerSays(' by Chuck Esterbrook.')
		self.assertAppServerSays('^WebKit and Webware are open source.$')
		self.assertAppServerSays('^EnableHTTP\s*=\s*(True|1)$')
		self.assertAppServerSays('^HTTPPort\s*=\s*8080$')
		self.assertAppServerSays('^Host\s*=\s*(localhost|127.0.0.1)$')
		self.assertAppServerSays('^Ready (.*).$')
		# We will also test the built-in HTTP server with this:
		try:
			data = urlopen('http://localhost:8080').read()
		except IOError:
			data = '<h2>Could not read page.</h2>'
		assert data.find('<h1>Welcome to Webware!</h1>') > 0
		assert data.find('<h2>Test passed.</h2>') > 0

	def assertAppServerSays(self, pattern, wait=5):
		"""Check that the appserver output contains the specified pattern.

		If the appserver does not output the pattern within the given number
		of seconds, an assertion is raised.

		"""
		if not self.waitForAppServer(pattern, wait):
			assert False, "Expected appserver to say '%s',\n" \
				"but after waiting %d seconds it said:\n%s" \
				% (pattern, wait, self._actualAppServerOutput)

	def waitForAppServer(self, pattern, wait=5):
		"""Check that the appserver output contains the specified pattern.

		Returns True or False depending on whether the pattern was seen.

		"""
		start = time.time()
		comp = reCompile(pattern)
		lines = []
		found = False
		while 1:
			try:
				line = self._queue.get_nowait()
			except Empty:
				line = None
			if line is None:
				now = time.time()
				if now - start > wait:
					break
				time.sleep(0.2)
			else:
				if len(lines) > 9:
					del lines[0]
				lines.append(line)
				if comp.search(line):
					found = True
					break
		self._actualAppServerOutput = ''.join(lines)
		return found

	def tearDown(self):
		"""Teardown fixture and test stopping."""
		try:
			data = urlopen('http://localhost:8080/stop').read()
		except IOError:
			data = '<h2>Could not read page.</h2>'
		assert data.find('<h2>The AppServer has been stopped.</h2>') > 0
		self.assertAppServerSays('^AppServer has been shutdown.$')
		self._output = None
