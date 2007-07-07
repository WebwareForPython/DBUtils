#!/usr/bin/env python

"""Launch.py

DESCRIPTION

Python launch script for the WebKit application server.

This launch script will run in its standard location in the Webware/WebKit
directory as well as in a WebKit work directory outside of the Webware tree.

USAGE

Launch.py [StartOptions] [AppServer [AppServerOptions]]

StartOptions:
  -d, --work-dir=...     Set the path to the app server working directory.
                         By default this is the directory containing Lauch.py.
  -w, --webware-dir=...  Set the path to the Webware root directory.
                         By default this is the parent directory.
  -l, --library=...      Other directories to be included in the search path.
                         You may specify this option multiple times.
  -p, --run-profile      Set this to get profiling going (see Profiler.py).
  -o, --log-file=...     Redirect standard output and error to this file.
  -i, --pid-file=...     Set the file path to hold the app server process id.
                         This option is fully supported under Unix only.
  -u, --user=...         The name or uid of the user to run the app server.
                         This option is supported under Unix only.
  -g, --group=...        The name or gid of the group to run the app server.
                         This option is supported under Unix only.

AppServer:
  The name of the application server module.
  By default, the ThreadedAppServer will be used.

AppServerOptions:
  Options that shall be passed to the application server.
  For instance, the ThreadedAppServer accepts: start, stop, daemon
  You can also change configuration settings here by passing
  arguments of the form ClassName.SettingName=value

Please note that the default values for the StartOptions and the AppServer
can be easily changed at the top of the Launch.py script.
"""

# FUTURE
# * This shares a lot of code with ThreadedAppServer.py and Launch.py.
#   Try to consolidate these things. The default settings below in the
#   global variables could go completely into AppServer.config.
# CREDITS
# * Contributed to Webware for Python by Chuck Esterbrook
# * Improved by Ian Bicking
# * Improved by Christoph Zwerschke


## Default options ##

# You can change the following default values:

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
# standard output and error to a log file:
logFile = None

# The pass to the pid file, if you want to check and terminate
# a running server by storing its server process id:
pidFile = None

# The name or uid of the server process user, if you want
# to run the server under a different user:
user = None

# The name or uid of the server process group, if you want
# to run the server under a different group:
group = None

# The default app server to be used:
appServer = 'ThreadedAppServer'


## Launch app server ##

import os, sys

def usage():
	"""Print the docstring and exit with error."""
	sys.stdout.write(__doc__)
	sys.exit(2)

def launchWebKit(appServer=appServer, workDir=None, args=None):
	"""Import and launch the specified WebKit app server.

	appServer  -- the name of the WebKit app server module
	workDir -- the server-side work directory of the app server
	args -- other options that will be given to the app server

	"""
	# Set up the arguments for the app server:
	if args is None:
		args = []
	if workDir:
		args.append('workdir=' + workDir)
	# Allow for a .py on the server name:
	if appServer[-3:] == '.py':
		appServer = appServer[:-3]
	# Import the app server's main() function:
	try:
		appServerMain = __import__('WebKit.' + appServer, None, None, 'main').main
	except ImportError, e:
		print 'Error: Cannot import the AppServer module.'
		print 'Reason:', str(e)
		sys.exit(1)
	# Set Profiler.startTime if this has not been done already:
	from WebKit import Profiler
	if Profiler.startTime is None:
		from time import time
		Profiler.startTime = time()
	# Run the app server:
	return appServerMain(args) # go!


## Main ##

def main(args=None):
	"""Evaluate the command line arguments and call launchWebKit."""
	global workDir, webwareDir, libraryDirs, runProfile, \
		logFile, pidFile, user, group, appServer
	if args is None:
		args = sys.argv[1:]
	# Accept AppServer even if placed before StartOptions:
	if args and not args[0].startswith('-'):
		arg2 = args.pop(0)
	else:
		arg2 = None
	# Accept AppServerOptions that look like StartOptions:
	args1 = []
	args2 = []
	while args:
		arg = args.pop(0)
		if arg.startswith('--') and \
			2 < arg.find('.', 2) < arg.find('=', 5):
			args2.append(arg)
		else:
			args1.append(arg)
	# Get all launch options:
	from getopt import getopt, GetoptError
	try:
		opts, args1 = getopt(args1, 'd:w:l:po:i:u:g:', [
			'work-dir=', 'webware-dir=', 'library=', 'run-profile',
			'log-file=', 'pid-file=', 'user=', 'group='])
	except GetoptError, error:
		print str(error)
		print
		usage()
	for opt, arg in opts:
		if opt in ('-d', '--work-dir'):
			workDir = arg
		elif opt in ('-w', '--webware-dir'):
			webwareDir = arg
		elif opt in ('-l', '--library'):
			libraryDirs.append(arg)
		elif opt in ('-p', '--run-profile'):
			runProfile = 1
		elif opt in ('-o', '--log-file'):
			logFile = arg
		elif opt in ('-i', '--pid-file'):
			pidFile = arg
		elif opt in ('-u', '--user'):
			user = arg
		elif opt in ('-g', '--group'):
			group = arg
	if arg2:
		appServer = arg2
	elif args1 and not args1[0].startswith('-') \
		and args1[0].find('=') < 0:
		appServer = args1.pop(0)
	args = args2 + args1
	# Figure out the group id:
	gid = group
	if gid is not None:
		try:
			gid = int(gid)
		except ValueError:
			try:
				import grp
				entry = grp.getgrnam(gid)
			except KeyError:
				print 'Error: Group %r does not exist.' % gid
				sys.exit(2)
			except ImportError:
				print 'Error: Group names are not supported.'
				sys.exit(2)
			gid = entry[2]
	# Figure out the user id:
	uid = user
	if uid is not None:
		try:
			uid = int(uid)
		except ValueError:
			try:
				import pwd
				entry = pwd.getpwnam(uid)
			except KeyError:
				print 'Error: User %r does not exist.' % uid
				sys.exit(2)
			except ImportError:
				print 'Error: User names are not supported.'
				sys.exit(2)
			if not gid:
				gid = entry[3]
			uid = entry[2]
	# Figure out the work directory and make it the current directory:
	if workDir:
		workDir = os.path.expanduser(workDir)
	else:
		scriptName = sys.argv and sys.argv[0]
		if not scriptName or scriptName == '-c':
			scriptName = 'Launch.py'
		workDir = os.path.dirname(os.path.abspath(scriptName))
	try:
		os.chdir(workDir)
	except OSError, error:
		print 'Error: Could not set working directory.'
		print 'The path %r cannot be used.' % workDir
		print error.strerror
		print 'Check the --work-dir option.'
		sys.exit(1)
	workDir = os.curdir
	# Expand user components in directories:
	if webwareDir:
		webwareDir = os.path.expanduser(webwareDir)
	else:
		webwareDir = os.pardir
	if libraryDirs:
		libraryDirs = map(os.path.expanduser, libraryDirs)
	# Remove the package component in the name of this module,
	# because otherwise the package path would be used for imports, too:
	global __name__
	name = __name__.split('.')[-1]
	if name != __name__:
		sys.modules[name] = sys.modules[__name__]
		del sys.modules[__name__]
		__name__ = name
	# Check the validity of the Webware directory:
	sysPath = sys.path # memorize the standard Python search path
	sys.path = [webwareDir] # now include only the Webware directory
	try: # check whether Webware is really located here
		from Properties import name as webwareName
		from WebKit.Properties import name as webKitName
	except ImportError:
		webwareName = None
	if webwareName != 'Webware for Python' or webKitName != 'WebKit':
		print 'Error: Cannot find the Webware directory.'
		print 'The path %r seems to be wrong.' % webwareDir
		print 'Check the --webware-dir option.'
		sys.exit(1)
	if not os.path.exists(os.path.join(webwareDir, 'install.log')):
		print 'Error: Webware has not been installed.'
		print 'Please run install.py in the Webware directory:'
		print '> cd', os.path.abspath(webwareDir)
		print '> python install.py'
		sys.exit(1)
	# Now assemble a new clean Python search path:
	path = [] # the new search path will be collected here
	webKitDir = os.path.abspath(os.path.join(webwareDir, 'WebKit'))
	for p in [workDir, webwareDir] + libraryDirs + sysPath:
		if not p:
			continue # do not include the empty ("current") directory
		p = os.path.abspath(p)
		if p == webKitDir or p in path or not os.path.exists(p):
			continue # do not include WebKit and duplicates
		path.append(p)
	sys.path = path # set the new search path
	# Prepare the arguments for launchWebKit:
	args = (appServer, workDir, args)
	# Handle special case where app server shall be stopped:
	if 'stop' in args[2]:
		print 'Stopping WebKit.%s...' % appServer
		errorlevel = launchWebKit(*args)
		if not errorlevel:
			if pidFile and os.path.exists(pidFile):
				try:
					os.remove(pidFile)
				except Exception:
					print 'The pid file could not be removed.'
					print
		sys.exit(errorlevel)
	# Handle the pid file:
	if pidFile:
		pidFile = os.path.expanduser(pidFile)
		# Read the old pid file:
		try:
			pid = int(open(pidFile).read())
		except Exception:
			pid = None
		if pid is not None:
			print 'According to the pid file, the server is still running.'
			# Try to kill an already running server:
			killed = 0
			try:
				from signal import SIGTERM, SIGKILL
				print 'Trying to terminate the server with pid %d...' % pid
				os.kill(pid, SIGTERM)
			except OSError, error:
				from errno import ESRCH
				if error.errno == ESRCH: # no such process
					print 'The pid file was stale, continuing with startup...'
					killed = 1
				else:
					print 'Cannot terminate server with pid %d.' % pid
					print error.strerror
					sys.exit(1)
			except (ImportError, AttributeError):
				print 'Cannot check or terminate server with pid %d.' % pid
				sys.exit(1)
			if not killed:
				from time import sleep
				try:
					for i in range(100):
						sleep(0.1)
						os.kill(pid, SIGTERM)
				except OSError, error:
					from errno import ESRCH
					if error.errno == ESRCH:
						print 'Server with pid %d has been terminated.' % pid
						killed = 1
			if not killed:
				try:
					for i in range(100):
						sleep(0.1)
						os.kill(pid, SIGKILL)
				except OSError, error:
					from errno import ESRCH
					if error.errno == ESRCH:
						print 'Server with pid %d has been killed by force.' % pid
						killed = 1
			if not killed:
				print 'Server with pid %d cannot be terminated.' % pid
				sys.exit(1)
		# Write a new pid file:
		try:
			open(pidFile, 'w').write(str(os.getpid()))
		except Exception:
			print 'The pid file %r could not be written.' % pidFile
			sys.exit(1)
	olduid = oldgid = stdout = stderr = log = None
	errorlevel = 1
	try:
		# Change server process group:
		if gid is not None:
			try:
				oldgid = os.getgid()
				if gid != oldgid:
					os.setgid(gid)
					if group:
						print 'Changed server process group to %r.' % group
				else:
					oldgid = None
			except Exception:
				if group:
					print 'Could not set server process group to %r.' % group
					oldgid = None
					sys.exit(1)
		# Change server process user:
		if uid is not None:
			try:
				olduid = os.getuid()
				if uid != olduid:
					os.setuid(uid)
					print 'Changed server process user to %r.' % user
				else:
					olduid = None
			except Exception:
				print 'Could not change server process user to %r.' % user
				olduid = None
				sys.exit(1)
		msg = 'WebKit.' + appServer
		if args[2]:
			msg = '%s %s' % (msg, ' '.join(args[2]))
		else:
			msg = 'Starting %s...' % msg
		print msg
		# Handle the log file:
		if logFile:
			logFile = os.path.expanduser(logFile)
			try:
				log = open(logFile, 'a', 1) # append, line buffered mode
				print 'Output has been redirected to %r...' % logFile
				stdout, stderr = sys.stdout, sys.stderr
				sys.stdout = sys.stderr = log
			except IOError, error:
				print 'Cannot redirect output to %r.' % logFile
				print error.strerror
				log = None
				sys.exit(1)
		else:
			print
		# Set up a reference to our profiler so apps can import and use it:
		from WebKit import Profiler
		if Profiler.startTime is None:
			from time import time
			Profiler.startTime = time()
		# Now start the app server:
		if runProfile:
			print 'Profiling is on.', \
				'See docstring in Profiler.py for more info.'
			print
			from profile import Profile
			profiler = Profile()
			Profiler.profiler = profiler
			errorlevel = Profiler.runCall(launchWebKit, *args)
			print
			print 'Writing profile stats to %s...' % Profiler.statsFilename
			Profiler.dumpStats()
			print 'WARNING: Applications run much slower when profiled,'
			print 'so turn off profiling in Launch.py when you are finished.'
		else:
			errorlevel = launchWebKit(*args)
	finally:
		print
		# Close the log file properly:
		if log:
			sys.stdout, sys.stderr = stdout, stderr
			log.close()
		# Restore server process group and user.
		# Note that because we changed the real group and
		# user id of the process (most secure thing), we
		# cannot change them back now, but we try anyway:
		if oldgid is not None:
			try:
				os.setgid(oldgid)
			except Exception:
				pass
			else:
				oldgid = None
		if olduid is not None:
			try:
				os.setuid(olduid)
			except Exception:
				pass
			else:
				olduid = None
		# Remove the pid file again.
		# Note that this may fail when the group or user id
		# has been changed, but we try anyway:
		if pidFile and os.path.exists(pidFile):
			try:
				os.remove(pidFile)
			except Exception:
				if oldgid is None and olduid is None:
					print 'The pid file could not be removed.'
					print
	sys.exit(errorlevel)

if __name__ == '__main__':
	main()
