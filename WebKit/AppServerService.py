#!/usr/bin/env python

"""AppServerService.py

For general notes, see `ThreadedAppServer`.

This version of the app server is a threaded app server that runs as
a Windows NT Service.  This means it can be started and stopped from
the Control Panel or from the command line using ``net start`` and
``net stop``, and it can be configured in the Control Panel to
auto-start when the machine boots.

This requires the win32all__ package to have been installed.

__ http://www.python.org/windows/win32all/

To see the options for installing, removing, starting, and stopping
the service, just run this program with no arguments.  Typical usage is
to install the service to run under a particular user account and startup
automatically on reboot with::

    python AppServerService.py --username mydomain\myusername \
        --password mypassword --startup auto install

Then, you can start the service from the Services applet in the Control Panel,
where it will be listed as "WebKit Threaded Application Server".  Or, from
the command line, it can be started with either of the following commands::

    net start WebKit
    python AppServerService.py start

The service can be stopped from the Control Panel or with::

    net stop WebKit
    python AppServerService.py stop

And finally, to uninstall the service, stop it and then run::

    python AppServerService.py remove

You can change several parameters in the top section of this script.
For instance, by changing the serviceName and serviceDisplayName, you
can have several instances of this service running on the same system.
Please note that the AppServer looks for the pid file in the working
directory, so use different working directories for different services.
And of course, you have to adapt the respective AppServer.config files
so that there will be no conflicts in the used ports.

"""

# FUTURE
# * This shares a lot of code with ThreadedAppServer.py and Launch.py.
#   Try to consolidate these things. The default settings below in the
#   global variables could go completely into AppServer.config.
# * Optional NT event log messages on start, stop, and errors.
# * Allow the option of installing multiple copies of WebKit with different
#   configurations and different service names.
# * Allow it to work with wkMonitor, or some other fault tolerance mechanism.
# CREDITS
# * Contributed to Webware for Python by Geoff Talvola
# * Changes by Christoph Zwerschke


## Options ##

# You can change the following parameters:

# The path to the app server working directory, if you do not
# want to use the directory containing this script:
workDir = None

# The path to the Webware root directory; by default this will
# be the parent directory of the directory containing this script:
webwareDir = None

# A list of additional directories (usually some libraries)
# that you want to include into the search path for modules:
libraryDirs = []

# To get profiling going, set runProfile = 1 (see also
# the description in the docstring of Profiler.py):
runProfile = 0

# The path to the log file, if you want to redirect the
# standard output and standard error to a log file:
logFile = 'Logs/webkit.log'

# The default app server to be used:
appServer = 'ThreadedAppServer'

# The service name:
serviceName = 'WebKit'

# The service display name:
serviceDisplayName = 'WebKit Application Server'

# The service descrpition:
serviceDescription = "This is the threaded application server" \
	" that belongs to the WebKit package" \
	" of the Webware for Python web framework."

# Sequence of service names on which this depends:
serviceDeps = []


## Win32 Service ##

import sys, os, time
import win32service, win32serviceutil

# The ThreadedAppServer calls signal.signal which is not possible
# if it is installed as a service, since signal only works in main thread.
# So we sneakily replace signal.signal with a no-op:
def _dummy_signal(*args, **kwargs):
	pass
import signal
signal.signal = _dummy_signal


class AppServerService(win32serviceutil.ServiceFramework):

	_svc_name_ = serviceName
	_svc_display_name_ = serviceDisplayName
	_svc_description_ = serviceDescription
	_svc_deps_ = serviceDeps

	_workDir = workDir or os.path.dirname(__file__)
	_webwareDir = webwareDir
	_libraryDirs = libraryDirs
	_runProfile = runProfile
	_logFile = logFile
	_appServer = appServer

	def __init__(self, args):
		win32serviceutil.ServiceFramework.__init__(self, args)
		self._server = None

	def SvcStop(self):
		# Stop the service:
		# Tell the SCM we are starting the stop process:
		self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
		if self._server:
			if self._server._running > 2:
				self._server.initiateShutdown()
			for i in range(30): # wait at most 3 seconds for shutdown
				if not self._server:
					break
				time.sleep(0.1)

	def SvcDoRun(self):
		# Start the service:
		self._server = log = None
		try:
			try:
				# Figure out the work directory and make it the current directory:
				workDir = self._workDir
				if not workDir:
					workDir = os.path.dirname(__file__)
				os.chdir(workDir)
				workDir = os.curdir
				# Switch the output to the logFile specified above:
				stdout, stderr = sys.stdout, sys.stderr
				logFile = self._logFile
				if logFile: # logFile has been specified
					if os.path.exists(logFile):
						log = open(logFile, 'a', 1) # append line buffered
						log.write('\n' + '-' * 68 + '\n\n')
					else:
						log = open(logFile, 'w', 1) # write line buffered
				else: # no logFile
					# Make all output go nowhere. Otherwise, print statements
					# cause the service to crash, believe it or not.
					log = open('nul', 'w') # os.devnull on Windows
				sys.stdout = sys.stderr = log
				# By default, Webware is searched in the parent directory:
				webwareDir = self._webwareDir
				if not webwareDir:
					webwareDir = os.pardir
				# Remove the package component in the name of this module,
				# because otherwise the package path would be used for imports:
				global __name__
				__name__ = __name__.split('.')[-1]
				# Check the validity of the Webware directory:
				sysPath = sys.path # memorize the standard Python search path
				sys.path = [webwareDir] # now include only the Webware directory
				# Check whether Webware is really located here
				from Properties import name as webwareName
				from WebKit.Properties import name as webKitName
				if webwareName != 'Webware for Python' or webKitName != 'WebKit':
					raise ImportError
				# Now assemble a new clean Python search path:
				path = [] # the new search path will be collected here
				webKitDir = os.path.abspath(os.path.join(webwareDir, 'WebKit'))
				for p in [workDir, webwareDir] + self._libraryDirs + sysPath:
					if not p:
						continue  # do not include empty ("current") directory
					p = os.path.abspath(p)
					if p == webKitDir or p in path or not os.path.exists(p):
						continue # do not include WebKit and duplicates
					path.append(p)
				sys.path = path # set the new search path
				# Import the Profiler:
				from WebKit import Profiler
				Profiler.startTime = time.time()
				# Import the AppServer:
				appServer = self._appServer
				appServerModule = __import__('WebKit.' + appServer,
					None, None, appServer)
				if self._runProfile:
					print 'Profiling is on.', \
						'See docstring in Profiler.py for more info.'
					print
				self._server = getattr(appServerModule, appServer)(workDir)
				print
				sys.stdout.flush()
				if self._runProfile:
					from profile import Profile
					profiler = Profile()
					Profiler.profiler = profiler
					sys.stdout.flush()
					Profiler.runCall(self._server.mainloop)
				else:
					self._server.mainloop()
				print
				sys.stdout.flush()
				if self._server._running:
					self._server.initiateShutdown()
					self._server._closeThread.join()
				if self._runProfile:
					print
					print 'Writing profile stats to %s...' % Profiler.statsFilename
					Profiler.dumpStats()
					print 'WARNING: Applications run much slower when profiled,'
					print 'so turn off profiling the service when you are done.'
			except SystemExit, e:
				if log and logFile:
					print
					errorlevel = e[0]
					if errorlevel == 3:
						print 'Please switch off AutoReloading in AppServer.Config.'
						print 'It does currently not work with AppServerSercive.'
						print 'You have to reload the service manually.'
					else:
						print 'The AppServer has been signaled to terminate.'
					print
			except Exception, e:
				if log and logFile:
					print
					try:
						import traceback
						traceback.print_exc(file=sys.stderr)
						print 'Service stopped due to above exception.'
					except Exception:
						print 'ERROR:', e
						print 'Cannot print traceback.'
					print
				raise
			except:
				raise
		finally:
			if self._server and self._server._running:
				self._server.initiateShutdown()
				self._server._closeThread.join()
			self._server = None
			if log:
				sys.stdout, sys.stderr = stdout, stderr
				log.close()


## Main ##

def main():
	win32serviceutil.HandleCommandLine(AppServerService)

if __name__ == '__main__':
	main()
