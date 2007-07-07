#!/usr/bin/env python

"""Fault tolerance system for WebKit.

Contributed to Webware for Python by Jay Love.

This module is intended to provide additional assurance that the
AppServer continues running at all times. This module will be
reponsible for starting the AppServer, and monitoring its health. It
does that by periodically sending a status check message to the
AppServer to ensure that it is responding. If it finds that the
AppServer does not respond within a specified time, it will start a
new copy of the AppServer, after killing the previous process.

Use::

    $ python Monitor.py start
    $ python Monitor.py stop

The default AppServer specified below will be used, or you can list
the AppServer you would like after ``start``.

You can have the whole process run as a daemon by specifying ``daemon``
after ``start`` on the command line.

To stop the processes, run ``Monitor.py stop``.

"""

# Future:
# Add ability to limit number of requests served. When some count is reached,
# send a message to the server to save it's sessions, then exit. Then start
# a new AppServer that will pick up those sessions.

# It should be possible on both Unix and Windows to monitor the AppServer
# process in 2 ways:
# 1) The method used here, ie can it service requests?
# 2) is the process still running?

# Combining these with a timer lends itself to load balancing of some kind.

defaultServer = "ThreadedAppServer"
monitorInterval = 10 # add to config if this implementation is adopted
maxStartTime = 120

"""Module global:

`defaultServer`:
    default ``"ThreadedAppServer"``. The type of AppServer to start up
    (as listed in ``Launch.py``)
`monitorInterval`:
    default 10. Seconds between checks.
`maxStartTime`:
    default 120. Seconds to wait for AppServer to start before killing
    it and trying again.

"""

import os, sys, time, socket, signal
from marshal import dumps

# Initialize some more global variables

serverName = defaultServer
srvpid = 0
addr = None
running = 0

debug = 1

statstr = dumps({'format': 'STATUS'})
statstr = dumps(len(statstr)) + statstr
quitstr = dumps({'format': 'QUIT'})
quitstr = dumps(len(quitstr)) + quitstr


## Start ##

def createServer(setupPath=0):
	"""Unix only, executed after forking for daemonization."""
	print "Starting Server..."

	import WebKit
	code = 'from WebKit.%s import main' % serverName
	exec code
	main(['start'])

def startupCheck():
	"""Make sure the AppServer starts up correctly."""
	count = 0
	print "Waiting for start..."
	time.sleep(monitorInterval/2) # give the server a chance to start
	while 1:
		if checkServer(0):
			break
		count += monitorInterval
		if count > maxStartTime:
			print "Couldn't start AppServer."
			print "Killing AppServer..."
			os.kill(srvpid, signal.SIGKILL)
			sys.exit(1)
		print "Waiting for start..."
		time.sleep(monitorInterval)

def startServer(killcurrent=1):
	"""Start the AppServer.

	If `killcurrent` is true or not provided, kill the current AppServer.

	"""
	global srvpid
	if os.name == 'posix':
		if killcurrent:
			try:
				os.kill(srvpid, signal.SIGTERM)
			except Exception:
				pass
			try:
				os.waitpid(srvpid, 0)
			except Exception:
				pass
		srvpid = os.fork()
		if srvpid == 0:
			createServer(not killcurrent)
			sys.exit()

def checkServer(restart=1):
	"""Send a check request to the AppServer.

	If restart is 1, then attempt to restart the server
	if we can't connect to it.

	This function could also be used to see how busy an AppServer
	is by measuring the delay in getting a response when using the
	standard port.

	"""
	try:
		sts = time.time()
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect(addr)
		s.send(statstr)
		s.shutdown(1)
		resp = s.recv(9) # up to 1 billion requests!
		monwait = time.time() - sts
		if debug:
			print "Processed %s Requests." % resp
			print "Delay %s." % monwait
		return 1
	except Exception:
		print "No Response from AppServer."
		if running and restart:
			startServer()
			startupCheck()
		else:
			return 0

def main(args):
	"""The main loop.

	Starts the server with `startServer(0)`,
	checks it's started up (`startupCheck`), and does a
	loop checking the server (`checkServer`).

	"""
	global running
	running = 1

	file = open("monitor.pid", "w")
	if os.name == 'posix':
		file.write(str(os.getpid()))
	file.flush()
	file.close()
	startServer(0)
	try:
		startupCheck()

	except Exception, e:
		if debug:
			print "Startup check exception:", e
			print "Exiting monitor..."
		try:
			os.kill(srvpid, signal.SIGTERM)
		except Exception:
			pass
		sys.exit()

	while running:
		try:
			if debug:
				print "Checking server..."
			checkServer()
			time.sleep(monitorInterval)
		except Exception, e:
			if debug:
				print "Exception:", e
			if not running:
				return
			print "Exiting Monitor..."
			try:
				os.kill(srvpid, signal.SIGTERM)
			except Exception:
				sys.exit(0)
			try:
				os.waitpid(srvpid, 0) # prevent zombies
			except Exception:
				sys.exit(0)


def shutDown(signum, frame):
	"""Shutdown handler.

	For when Ctrl-C has been hit, or this process is being cleanly killed.

	"""
	global running
	print "Monitor Shutdown Called."
	sys.stdout.flush()
	running = 0
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect(addr)
		s.send(quitstr)
		s.shutdown(1)
		resp = s.recv(10)
		s.close()
		print "AppServer response to shutdown request:", resp
	except Exception, e:
		print e
		print "No Response to shutdown request, performing hard kill."
		os.kill(srvpid, signal.SIGINT)
		os.waitpid(srvpid, 0)
	sys.stdout.flush()
	sys.stderr.flush()
	return 0

import signal
signal.signal(signal.SIGINT, shutDown)
signal.signal(signal.SIGTERM, shutDown)


## Stop ##

def stop():
	"""Stop the monitor.

	This kills the other monitor process that has been opened
	(from the PID file ``monitor.pid``).

	"""
	pid = int(open("monitor.pid", "r").read())
	# this goes to the other running instance of this module
	os.kill(pid, signal.SIGINT)


## Command line interface ##

def usage():
	print """
This module serves as a watcher for the AppServer process.
The required command line argument is one of:

start: Starts the monitor and default appserver

stop:  Stops the currently running Monitor process and the AppServer
       if is running. This is the only way to stop the process other
       than hunting down the individual process ID's and killing them.

Optional arguments:

"AppServer": The AppServer class to use (currently only ThreadedAppServer)
daemon:      If "daemon" is specified, the Monitor will run
             as a background process.

"""

arguments = ["start", "stop"]
servernames = ["ThreadedAppServer"]
optionalargs = ["daemon"]

if __name__ == '__main__':

	if os.name != 'posix':
		print "This service can only be run on Posix machines (UNIX)."
		sys.exit()

	if len(sys.argv) == 1:
		usage()
		sys.exit()

	args = sys.argv[1:]
	if args[0] not in arguments:
		usage()
		sys.exit()

	if 1: # setup path:
		if '' not in sys.path:
			sys.path = [''] + sys.path
		try:
			import WebwarePathLocation
			wwdir = os.path.abspath(os.path.join(os.path.dirname(
				WebwarePathLocation.__file__), '..'))
		except Exception, e:
			print e
			usage()
		if not wwdir in sys.path:
			sys.path.insert(0, wwdir)
		sys.path.remove('')
		try:
			sys.path.remove('.')
		except Exception:
			pass

	cfgfile = open(os.path.join(wwdir, "WebKit",
		"Configs/AppServer.config")).read()
	cfg = {'True': 1 == 1, 'False': 1 == 0, 'WebwarePath': wwdir}
	if cfgfile.lstrip().startswith('{'):
		cfg = eval(cfgfile, cfg)
	else:
		exec cfgfile in cfg
	if not cfg.has_key('EnableMonitor') or not cfg['EnableMonitor']:
		print "Monitoring has not been enabled in AppServer.config!"
		sys.exit()
	if cfg.has_key('Host'):
		host = cfg['Host']
	else:
		host = '127.0.0.1'
	if cfg.has_key('MonitorPort'):
		port = cfg['MonitorPort']
	else:
		port = 8085
	addr = (host, port)

	if 'stop' in args:
		stop()
		sys.exit()

	for i in servernames:
		if i in args:
			serverName = i

	if 'daemon' in args: # fork and become a daemon
		daemon = os.fork()
		if daemon:
			sys.exit()

	main(args)
