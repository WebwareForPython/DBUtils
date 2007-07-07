#!/usr/bin/env python

"""The AppServer singleton.

The `AppServer` singleton is the controlling object/process/thread.
`AppServer` receives requests and dispatches them to `Application`
(via `Application.dispatchRawRequest`).

There is only one instance of AppServer, `globalAppServer` contains
that instance. Use it like:

    from WebKit.AppServer import globalAppServer

`ThreadedAppServer` completes the implementation, dispatching
these requests to separate threads. `AppServer`, at least in the
abstract, could support different execution models and environments,
but that support is not yet realized (Will it ever be realized?).

The distinction between `AppServer` and `Application` is somewhat
vague -- both are global singletons and both handle dispatching requests.
`AppServer` works on a lower level, handling sockets and threads.

"""

from threading import Thread, Event

from Common import *
from Object import Object
from Application import Application
from ImportManager import ImportManager
from PlugIn import PlugIn
from PidFile import PidFile, ProcessRunning
from ConfigurableForServerSidePath import ConfigurableForServerSidePath
import Profiler

defaultConfig = {
	'PrintConfigAtStartUp': True,
	'Verbose': True,
	'PlugIns': [],
	'PlugInDirs': [],
	'CheckInterval': 100,
	'PidFile': 'appserver.pid',
}

# This actually gets set inside AppServer.__init__
globalAppServer = None


class AppServer(ConfigurableForServerSidePath, Object):
	"""The AppServer singleton.

	Purpose and usage are explained in the module docstring.

	"""


	## Init ##

	def __init__(self, path=None):
		"""Sets up and starts the `AppServer`.

		`path` is the working directory for the AppServer
		(directory in which AppServer is contained, by default)

		This method loads plugins, creates the Application object,
		and starts the request handling loop.

		"""
		self._running = 0
		self._startTime = time.time()

		global globalAppServer
		if globalAppServer:
			raise ProcessRunning('More than one AppServer'
				' or __init__() invoked more than once.')
		globalAppServer = self

		# Set up the import manager:
		self._imp = ImportManager()

		ConfigurableForServerSidePath.__init__(self)
		Object.__init__(self)
		if path is None:
			path = os.path.dirname(__file__) # os.getcwd()
		self._serverSidePath = os.path.abspath(path)
		self._webKitPath = os.path.abspath(os.path.dirname(__file__))
		self._webwarePath = os.path.dirname(self._webKitPath)

		self.recordPID()

		self._verbose = self.setting('Verbose')
		self._plugIns = []
		self._requestID = 0

		self.checkForInstall()
		self.config() # cache the config
		self.printStartUpMessage()
		sys.setcheckinterval(self.setting('CheckInterval'))
		self._app = self.createApplication()
		self.loadPlugIns()

		# @@ 2003-03 ib: shouldn't this just be in a subclass's __init__?
		if self.isPersistent():
			self._closeEvent = Event()
			self._closeThread = Thread(target=self.closeThread,
				name="CloseThread")
			# self._closeThread.setDaemon(1)
			self._closeThread.start()
		self._running = 1

	def checkForInstall(self):
		"""Check whether Webware was installed.

		Exits with an error message if Webware was not installed.
		Called from `__init__`.

		"""
		if not os.path.exists(os.path.join(self._webwarePath, 'install.log')):
			sys.stdout = sys.stderr
			print 'ERROR: You have not installed Webware.'
			print 'Please run install.py from inside the Webware directory.'
			print 'For example:'
			print '> cd ..'
			print '> python install.py'
			print
			sys.exit(0)

	def readyForRequests(self):
		"""Declare ready for getting requests.

		Should be invoked by subclasses when they are finally ready to
		accept requests. Records some stats and prints a message.

		"""
		if Profiler.startTime is None:
			Profiler.startTime = self._startTime
		Profiler.readyTime = time.time()
		Profiler.readyDuration = Profiler.readyTime - Profiler.startTime
		print "Ready (%.2f seconds after launch)." % Profiler.readyDuration
		print
		sys.stdout.flush()
		sys.stderr.flush()

	def closeThread(self):
		"""This method is called when the shutdown sequence is initiated."""
		if self.isPersistent():
			self._closeEvent.wait()
		self.shutDown()

	def initiateShutdown(self):
		"""Ask the master thread to begin the shutdown."""
		if self.isPersistent():
			self._closeEvent.set()

	def recordPID(self):
		"""Save the pid of the AppServer to a file."""
		if self.setting('PidFile') is None:
			self._pidFile = None
			return
		pidpath = self.serverSidePath(self.setting('PidFile'))
		try:
			self._pidFile = PidFile(pidpath)
		except ProcessRunning:
			raise ProcessRunning('The file ' + pidpath + ' exists\n'
				'and contains a process id corresponding to a running process.\n'
				'This indicates that there is an AppServer already running.\n'
				'If this is not the case, delete this file and restart the AppServer.')

	def shutDown(self):
		"""Shut down the AppServer.

		Subclasses may override and normally follow this sequence:
			1. set self._running = 1 (request to shut down)
			2. class specific statements for shutting down
			3. Invoke super's shutDown() e.g., ``AppServer.shutDown(self)``
			4. set self._running = 0 (server is completely down)

		"""
		if self._running:
			print "AppServer is shutting down..."
			sys.stdout.flush()
			self._running = 1
			self._app.shutDown()
			del self._plugIns
			del self._app
			if self._pidFile:
				self._pidFile.remove() # remove the pid file
			if Profiler.profiler:
				# The profile stats will be dumped by Launch.py.
				# You might also considering having a page/servlet
				# that lets you dump the stats on demand.
				print 'AppServer ran for %0.2f seconds.' % (
					time.time() - Profiler.startTime)
			print "AppServer has been shutdown."
			sys.stdout.flush()
			sys.stderr.flush()
			self._running = 0


	## Configuration ##

	def defaultConfig(self):
		"""The default AppServer.config."""
		return defaultConfig # defined on the module level

	def configFilename(self):
		"""Return the name of the AppServer configuration file."""
		return self.serverSidePath('Configs/AppServer.config')

	def configReplacementValues(self):
		"""Get config values that need to be escaped."""
		# Since these strings may be eval'ed as ordinary strings,
		# we need to use forward slashes instead of backslashes.
		# Note: This is only needed for old style config files.
		# In new style config files, they are note eval'ed, but used
		# directly, so double escaping would be a bad idea here.
		return {
			'WebwarePath': self._webwarePath.replace('\\', '/'),
			'WebKitPath': self._webKitPath.replace('\\', '/'),
			'serverSidePath': self._serverSidePath.replace('\\', '/'),
			}


	## Network Server ##

	def createApplication(self):
		"""Create and return an application object. Invoked by __init__."""
		return Application(server=self)

	def printStartUpMessage(self):
		"""Invoked by __init__, prints a little intro."""
		print 'WebKit AppServer', self.version()
		print 'Part of Webware for Python.'
		print 'Copyright 1999-2007 by Chuck Esterbrook. All Rights Reserved.'
		print 'WebKit and Webware are open source.'
		print 'Please visit: http://www.webwareforpython.org'
		print
		print 'Process id is', os.getpid()
		print 'Date/time is', asclocaltime()
		print 'Python is', sys.version.replace(') [', ')\n[')
		print
		if self.setting('PrintConfigAtStartUp'):
			self.printConfig()


	## Plug-in loading ##

	def plugIns(self):
		"""Return a list of the plug-ins loaded by the app server.

		Each plug-in is a Python package.

		"""
		return self._plugIns

	def plugIn(self, name, default=NoDefault):
		""" Return the plug-in with the given name. """
		# @@ 2001-04-25 ce: linear search. yuck.
		# Plus we should guarantee plug-in name uniqueness anyway
		for plugin in self._plugIns:
			if plugin.name() == name:
				return plugin
		if default is NoDefault:
			raise KeyError, name
		else:
			return default

	def loadPlugIn(self, path):
		"""Load and return the given plug-in.

		May return None if loading was unsuccessful (in which case this method
		prints a message saying so). Used by `loadPlugIns` (note the **s**).

		"""
		plugIn = None
		path = self.serverSidePath(path)
		try:
			plugIn = PlugIn(self, path)
			willNotLoadReason = plugIn.load()
			if willNotLoadReason:
				print '    Plug-in %s cannot be loaded because:\n' \
					'    %s' % (path, willNotLoadReason)
				return None
			plugIn.install()
		except Exception:
			print
			print 'Plug-in', path, 'raised exception.'
			raise
		return plugIn

	def loadPlugIns(self):
		"""Load all plug-ins.

		A plug-in allows you to extend the functionality of WebKit without
		necessarily having to modify its source. Plug-ins are loaded by
		AppServer at startup time, just before listening for requests.
		See the docs in `WebKit.PlugIn` for more info.

		"""
		plugIns = self.setting('PlugIns')
		plugIns = map(lambda path, ssp=self.serverSidePath: ssp(path), plugIns)

		# Scan each directory named in the PlugInDirs list.
		# If those directories contain Python packages (that don't have
		# a "dontload" file) then add them to the plugs in list.
		for plugInDir in self.setting('PlugInDirs'):
			plugInDir = self.serverSidePath(plugInDir)
			fileNames = os.listdir(plugInDir)
			fileNames.sort()
			for filename in fileNames:
				filename = os.path.normpath(os.path.join(plugInDir, filename))
				if (os.path.isdir(filename)
					and os.path.exists(os.path.join(filename, '__init__.py'))
					and os.path.exists(os.path.join(filename, 'Properties.py'))
					and not os.path.exists(os.path.join(filename, 'dontload'))
					and os.path.basename(filename) != 'WebKit'
					and filename not in plugIns):
					plugIns.append(filename)

		print 'Plug-ins list:', ', '.join(plugIns) or 'empty'

		# Now that we have our plug-in list, load them...
		for plugInPath in plugIns:
			plugIn = self.loadPlugIn(plugInPath)
			if plugIn:
				self._plugIns.append(plugIn)
		print


	## Accessors ##

	def version(self):
		"""Return WebKit version."""
		if not hasattr(self, '_webKitVersionString'):
			from MiscUtils.PropertiesObject import PropertiesObject
			props = PropertiesObject(os.path.join(self.webKitPath(), 'Properties.py'))
			self._webKitVersionString = props['versionString']
		return self._webKitVersionString

	def application(self):
		"""Return the Application singleton."""
		return self._app

	def startTime(self):
		"""Return the time the app server was started.

		The time is given as seconds, like time().

		"""
		return self._startTime

	def numRequests(self):
		"""Return the number of requests.

		Returns the number of requests received by this app server
		since it was launched.

		"""
		return self._requestID

	def isPersistent(self):
		"""Check whether the AppServer is persistent.

		When using ``OneShot``, the AppServer will exist only for a single
		request, otherwise it will stay around indefinitely.

		"""
		raise AbstractError, self.__class__

	def serverSidePath(self, path=None):
		"""Return the absolute server-side path of the WebKit app server.

		If the optional path is passed in, then it is joined with the
		server side directory to form a path relative to the app server.

		"""
		if path:
			return os.path.normpath(os.path.join(self._serverSidePath, path))
		else:
			return self._serverSidePath

	def webwarePath(self):
		"""Return the Webware path."""
		return self._webwarePath

	def webKitPath(self):
		"""Return teh WebKit path."""
		return self._webKitPath


## Main ##

def main():
	"""Start the Appserver."""
	try:
		server = AppServer()
		print "Ready."
		print
		print "WARNING: There is nothing to do here with the abstract AppServer."
		print "Use one of the adapters such as WebKit.cgi (with ThreadedAppServer)"
		print "or OneShot.cgi"
		server.shutDown()
	except Exception, exc: # Need to kill the sweeper thread somehow
		print "Caught exception:", exc
		print "Exiting AppServer..."
		server.shutDown()
		del server
		sys.exit()

def kill(pid):
	"""Kill a process."""
	try:
		from signal import SIGTERM
		os.kill(pid, SIGTERM)
	except Exception:
		if os.name == 'nt':
			import win32api
			handle = win32api.OpenProcess(1, 0, pid)
			win32api.TerminateProcess(handle, 0)
		else:
			raise

def stop(*args, **kw):
	"""Stop the AppServer (which may be in a different process)."""
	print "Stopping the AppServer..."
	if kw.has_key('workDir'):
		# app directory
		pidfile = os.path.join(kw['workDir'], "appserver.pid")
	else:
		# pidfile is in WebKit directory
		pidfile = os.path.join(os.path.dirname(__file__), "appserver.pid")
	try:
		pid = int(open(pidfile).read())
	except Exception:
		print "Cannot read process id from pidfile."
	else:
		try:
			kill(pid)
		except Exception:
			from traceback import print_exc
			print_exc(1)
			print "WebKit cannot terminate the running process."

if __name__ == '__main__':
	main()
