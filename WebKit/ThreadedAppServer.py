#!/usr/bin/env python
"""Threaded Application Server

The AppServer is the main process of WebKit. It handles requests for
servlets from webservers.

ThreadedAppServer uses a threaded model for handling multiple requests.

At one time there were other experimental execution models for AppServer,
but none of these were successful and have been removed.
The ThreadedAppServer/AppServer distinction is thus largely historical.

ThreadedAppServer takes the following command line arguments:

start: start the AppServer (default argument)
stop: stop the currently running Apperver
daemon: run as a daemon
ClassName.SettingName=value: change configuration settings

When started, AppServer records its pid in appserverpid.txt.

"""

from Common import *
import AppServer as AppServerModule
from AutoReloadingAppServer import AutoReloadingAppServer as AppServer
from MiscUtils.Funcs import timestamp
from WebUtils import Funcs

from marshal import dumps, loads
import os, sys, threading, Queue, select, socket, time, errno, traceback


debug = 0

DefaultConfig = {
	'Host':                 '127.0.0.1',
	'EnableAdapter':        True,
	'AdapterPort':          8086,
	'EnableMonitor':        False,
	'MonitorPort':          8085,
	'EnableHTTP':           False,
	'HTTPPort':             8080,
	'MaxServerThreads':     20,
	'MinServerThreads':     5,
	'StartServerThreads':   10,

	# @@ 2000-04-27 ce: None of the following settings are implemented
	# 'RequestQueueSize': 16,
	# 'RequestBufferSize': 64*1024,
	# 'SocketType': 'inet', # inet, unix
}

# Need to know this value for communications
# (note that this limits the size of the dictionary we receive
# from the AppServer to 2,147,483,647 bytes):
intLength = len(dumps(int(1)))

server = None


class NotEnoughDataError(Exception):
	pass

class ProtocolError(Exception):
	pass


class ThreadedAppServer(AppServer):
	"""Threaded Application Server.

	`ThreadedAppServer` accepts incoming socket requests, spawns a
	new thread or reuses an existing one, then dispatches the request
	to the appropriate handler (e.g., an Adapter handler, HTTP handler,
	etc., one for each protocol).

	The transaction is connected directly to the socket, so that the
	response is sent directly (if streaming is used, like if you call
	``response.flush()``). Thus the ThreadedAppServer packages the
	socket/response, rather than value being returned up the call chain.

	"""


	## Init ##

	def __init__(self, path=None):
		"""
		Setup the AppServer, create an initial thread pool
		(threads created with `spawnThread`), record the PID
		in a file, and add any enabled handlers (Adapter, HTTP, Monitor).
		"""

		self._defaultConfig = None
		try:
			AppServer.__init__(self, path)
			threadCount = self.setting('StartServerThreads')
			self._maxServerThreads = self.setting('MaxServerThreads')
			self._minServerThreads = self.setting('MinServerThreads')
			self._threadPool = []
			self._threadCount = 0
			self._threadUseCounter = []
			# twice the number of threads we have:
			self._requestQueue = Queue.Queue(self._maxServerThreads * 2)
			self._addr = {}
			self._requestID = 0

			out = sys.stdout

			out.write('Creating %d threads' % threadCount)
			for i in range(threadCount):
				self.spawnThread()
				out.write(".")
				out.flush()
			out.write("\n")

			self._socketHandlers = {}
			self._handlerCache = {}
			self._sockets = {}

			if self.setting('EnableAdapter'):
				self.addSocketHandler(AdapterHandler)

			if self.setting('EnableMonitor'):
				self.addSocketHandler(MonitorHandler)

			if self.setting('EnableHTTP'):
				from WebKit.HTTPServer import HTTPAppServerHandler
				self.addSocketHandler(HTTPAppServerHandler)

			self.readyForRequests()
		except:
			if self.running:
				self.initiateShutdown()
				self._closeThread.join()
			raise

	def addSocketHandler(self, handlerClass, serverAddress=None):
		"""Add socket handler.

		Adds a socket handler for `serverAddress` -- `serverAddress`
		is a tuple (*host*, *port*), where *host* is the interface
		to connect to (for instance, the IP address on a machine with
		multiple IP numbers), and *port* is the port (e.g. HTTP is on
		80 by default, and Webware adapters use 8086 by default).

		The `handlerClass` is a subclass of `Handler`, and is used to
		handle the actual request -- usually returning control back
		to ThreadedAppServer in some fashion. See `Handler` for more.

		"""

		if serverAddress is None:
			serverAddress = self.address(handlerClass.settingPrefix)
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		try:
			sock.bind(serverAddress)
			sock.listen(1024)
		except:
			print "Error: Can not listen for %s on %s" % (
				handlerClass.settingPrefix, str(serverAddress))
			sys.stdout.flush()
			raise
		serverAddress = sock.getsockname() # resolve/normalize
		self._socketHandlers[serverAddress] = handlerClass
		self._handlerCache[serverAddress] = []
		self._sockets[serverAddress] = sock
		adr_str = ':'.join(map(str, serverAddress))
		print "Listening for %s on %s" % (handlerClass.settingPrefix, adr_str)
		# write text file with server address
		adr_file = self.addressFileName(handlerClass)
		if os.path.exists(adr_file):
			print "Warning: %s already exists" % adr_file
			try:
				os.unlink(adr_file)
			except OSError: # we cannot remove the file
				if open(adr_file).read() == adr_str:
					return # same content, so never mind
				else:
					print "Error: Could not remove", adr_file
					sys.stdout.flush()
					raise
		try:
			f = open(adr_file, 'w')
			f.write(adr_str)
			f.close()
		except IOError:
			print "Error: Could not write", adr_file
			sys.stdout.flush()
			raise

	def isPersistent(self):
		return True

	def defaultConfig(self):
		if self._defaultConfig is None:
			self._defaultConfig = AppServer.defaultConfig(self).copy()
			self._defaultConfig.update(DefaultConfig)
		return self._defaultConfig

	def mainloop(self, timeout=1):
		"""Main thread loop.

		This is the main thread loop that accepts and dispatches
		socket requests.

		It goes through a loop as long as ``self.running > 2``.
		Setting ``self.running = 2`` asks the the main loop to end.
		When the main loop is finished, it sets ``self.running = 1``.
		When the AppServer is completely down, it sets ``self.running = 0``.

		The loop waits for connections, then based on the connecting
		port it initiates the proper Handler (e.g.,
		AdapterHandler, HTTPHandler). Handlers are reused when possible.

		The initiated handlers are put into a queue, and
		worker threads poll that queue to look for requests that
		need to be handled (worker threads use `threadloop`).

		Every so often (every 5 loops) it updates thread usage
		information (`updateThreadUsage`), and every
		``MaxServerThreads`` * 2 loops it it will manage
		threads (killing or spawning new ones, in `manageThreadCount`).

		"""

		threadCheckInterval = self._maxServerThreads*2
		threadUpdateDivisor = 5 # grab stat interval
		threadCheck = 0

		self.running = 3 # server is in the main loop now

		try:
			while self.running > 2:

				# block for timeout seconds waiting for connections
				try:
					input, output, exc = select.select(
						self._sockets.values(), [], [], timeout)
				except select.error, e:
					if e[0] == errno.EINTR:
						continue
					else:
						raise

				for sock in input:
					self._requestID += 1
					client, addr = sock.accept()
					serverAddress = sock.getsockname()
					try:
						handler = self._handlerCache[serverAddress].pop()
					except IndexError:
						handler = self._socketHandlers[serverAddress](self,
							serverAddress)
					handler.activate(client, self._requestID)
					self._requestQueue.put(handler)

				if threadCheck % threadUpdateDivisor == 0:
					self.updateThreadUsage()

				if threadCheck > threadCheckInterval:
					threadCheck = 0
					self.manageThreadCount()
				else:
					threadCheck += 1

				self.restartIfNecessary()

		finally:
			self.running = 1


	## Thread Management ##

	# These methods handle the thread pool. The AppServer pre-allocates
	# threads, and reuses threads for requests. So as more threads
	# are needed with varying load, new threads are spawned, and if there
	# are excess threads, then threads are removed.

	def updateThreadUsage(self):
		"""Update the threadUseCounter list.

		Called periodically	from `mainloop`.

		"""
		count = self.activeThreadCount()
		if len(self._threadUseCounter) > self._maxServerThreads:
			self._threadUseCounter.pop(0)
		self._threadUseCounter.append(count)

	def activeThreadCount(self):
		"""Get a snapshot of the number of threads currently in use.

		Called from `updateThreadUsage`.

		"""
		count = 0
		for i in self._threadPool:
			if i._processing:
				count += 1
		return count

	def manageThreadCount(self):
		"""Adjust the number of threads in use.

		From information gleened from `updateThreadUsage`, we see about how
		many threads are being used, to see if we have too many threads or
		too few. Based on this we create or absorb threads.

		"""

		# @@: This algorithm needs work. The edges (i.e. at
		# the minserverthreads) are tricky. When working
		# with this, remember thread creation is *cheap*.

		average = max = 0

		if debug:
			print "ThreadUse Samples:", self._threadUseCounter
		for i in self._threadUseCounter:
			average += i
			if i > max:
				max = i
		average = average / len(self._threadUseCounter)
		if debug:
			print "Average Thread Use: ", avg
			print "Max Thread Use: ", max
			print "ThreadCount: ", self.threadCount

		if len(self._threadUseCounter) < self._maxServerThreads:
			return # not enough samples

		margin = self._threadCount / 2 # smoothing factor
		if debug:
			print "Margin:", margin

		if average > self._threadCount - margin and \
			self._threadCount < self._maxServerThreads:
			# Running low: double thread count
			n = min(self._threadCount,
				self._maxServerThreads - self._threadCount)
			if debug:
				print "Adding %s threads" % n
			for i in range(n):
				self.spawnThread()
		elif average < self._threadCount - margin and \
			self._threadCount > self._minServerThreads:
			n = min(self._threadCount - self._minServerThreads,
				self._threadCount - max)
			self.absorbThread(n)
		else:
			# cleanup any stale threads that we killed but haven't joined
			self.absorbThread(0)

	def spawnThread(self):
		"""Create a new worker thread.

		Worker threads poll with the `threadloop` method.

		"""
		if debug:
			print "Spawning new thread"
		t = threading.Thread(target=self.threadloop)
		t._processing = False
		t.start()
		self._threadPool.append(t)
		self._threadCount += 1
		if debug:
			print "New thread spawned, threadCount =", self._threadCount

	def absorbThread(self, count=1):
		"""Absorb a thread.

		We do this by putting a None on the Queue.
		When a thread gets it, that tells it to exit.

		We also keep track of the threads, so after killing
		threads we go through all the threads and find the
		thread(s) that have exited, so that we can take them
		out of the thread pool.

		"""
		for i in range(count):
			self._requestQueue.put(None)
			# _threadCount is an estimate, just because we
			# put None in the queue, the threads don't immediately
			# disapear, but they will eventually.
			self._threadCount -= 1
		for i in self._threadPool:
			# There may still be a None in the queue, and some
			# of the threads we want gone may not yet be gone.
			# But we'll pick them up later -- they'll wait,.
			if not i.isAlive():
				rv = i.join() # Don't need a timeout, it isn't alive
				self._threadPool.remove(i)
				if debug:
					print "Thread absorbed, real threadCount =", len(self.threadPool)


	## Worker Threads ##

	def threadloop(self):
		"""The main loop for worker threads.

		Worker threads poll the ``_requestQueue`` to find a request handler
		waiting to run. If they find a None in the queue, this thread has
		been selected to die, which is the way the loop ends.

		The handler object does all the work when its `handleRequest` method
		is called.

		`initThread` and `delThread` methods are called at the beginning and
		end of the thread loop, but they aren't being used for anything
		(future use as a hook).

		"""

		self.initThread()

		t = threading.currentThread()
		t._processing = False

		try:
			while 1:
				try:
					handler = self._requestQueue.get()
					if handler is None: # None means time to quit
						if debug:
							print "Thread retrieved None, quitting."
						break
					t._processing = True
					try:
						handler.handleRequest()
					except:
						traceback.print_exc(file=sys.stderr)
					t._processing = False
					handler.close()
				except Queue.Empty:
					pass
		finally:
			self.delThread()
		if debug:
				print threading.currentThread(), "Quitting."

	def initThread(self):
		"""Initialize thread.

		Invoked immediately by threadloop() as a hook for subclasses.
		This implementation does nothing and subclasses need not invoke super.

		"""
		pass

	def delThread(self):
		"""Delete thread.

		Invoked immediately by threadloop() as a hook for subclasses.
		This implementation does nothing and subclasses need not invoke super.

		"""
		pass


	## Shutting Down ##

	def shutDown(self):
		"""Called on shutdown.

		Also calls `AppServer.shutDown`, but first closes all sockets
		and tells all the threads to die.

		"""
		if self.running > 2:
			self.running = 2 # ask main loop to finish
		print "ThreadedAppServer is shutting down..."
		sys.stdout.flush()
		self.awakeSelect() # unblock select call in mainloop()
		for i in range(30): # wait at most 3 seconds for shutdown
			if self.running < 2:
				break
			time.sleep(0.1)
		# Close all sockets now:
		for sock in self._sockets.values():
			sock.close()
		# Remove the text files with the server addresses:
		for handler in self._socketHandlers.values():
			adr_file = self.addressFileName(handler)
			if os.path.exists(adr_file):
				try:
					os.unlink(adr_file)
				except OSError:
					print "Warning: Could not remove", adr_file
		# Tell all threads to end:
		for i in range(self._threadCount):
			self._requestQueue.put(None)
		for i in self._threadPool:
			try:
				i.join()
			except:
				pass
		# Call super's shutdown:
		AppServer.shutDown(self)
		sys.stdout.flush()
		sys.stderr.flush()
		self.running = 0

	def awakeSelect(self):
		"""Awake the select() call.

		The ``select()`` in `mainloop()` is blocking, so when
		we shut down we have to make a connect to unblock it.
		Here's where we do that, called `shutDown`.

		"""
		for host, port in self._sockets.keys():
			if host == '0.0.0.0':
				# Can't connect to 0.0.0.0; use 127.0.0.1 instead
				host = '127.0.0.1'
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			try:
				sock.connect((host, port))
				sock.close()
			except:
				pass


	## Misc ##

	def address(self, settingPrefix):
		"""Get host address.

		The address for the Adapter (Host/interface, and port),
		as taken from ``Configs/AppServer.config``,
		settings ``Host`` and ``AdapterPort``.

		"""
		try:
			return self._addr[settingPrefix]
		except KeyError:
			host = self.setting(settingPrefix + 'Host', self.setting('Host'))
			if settingPrefix == 'Adapter':
				# jdh 2004-12-01:
				# 'Port' has been renamed to 'AdapterPort'. However, we don't
				# want the the default AdapterPort in DefaultConfig above to
				# be used if a user still has 'Port' in their config file.
				# So for now, we prefer the 'Port' setting if it exists.
				# After a few releases we can remove this special case.
				port = self.setting('Port', None)
				if port is None:
					port = self.setting(settingPrefix + 'Port')
				else:
					print "WARNING:", \
						"The 'Port' setting has been renamed to 'AdapterPort'."
					print "Please update your AppServer.config file."
			else:
				port = self.setting(settingPrefix + 'Port')
			self._addr[settingPrefix] = (host, port)
			return self._addr[settingPrefix]

	def addressFileName(self, handlerClass):
		"""Get the name of the text file with the server address."""
		return ('%s.text' % handlerClass.protocolName)


class Handler:
	"""A very general socket handler.

	Handler is an abstract superclass -- specific protocol implementations
	will subclass this. A Handler takes a socket to interact with, and
	creates a raw request.

	Handlers will be reused. When a socket is received `activate` will be
	called -- but the handler should not do anything, as it is still running
	in the main thread. The handler is put into a queue, and a worker thread
	picks it up and runs `handleRequest`, which subclasses should override.

	Several methods are provided which are typically used by subclasses.

	"""

	def __init__(self, server, serverAddress):
		"""Create a new socket handler.

		Each handler is attached to a specific host and port,
		and of course to the AppServer.

		"""
		self._server = server
		self._serverAddress = serverAddress

	def activate(self, sock, requestID):
		"""Activate the handler for processing the request.

		`sock` is the incoming socket that this handler will work with,
		and `requestID` is a serial number unique for each request.

		This isn't where work gets done -- the handler is queued after this,
		and work is done when `handleRequest` is called.

		"""
		self._requestID = requestID
		self._sock = sock

	def close(self):
		"""Close the socket.

		Called when the handler is finished. Closes the socket and
		returns the handler to the pool of inactive handlers.

		"""
		self._sock = None
		self._server._handlerCache[self._serverAddress].append(self)

	def handleRequest(self):
		"""
		Subclasses should override this -- this is where
		work gets done.
		"""
		pass

	def receiveDict(self):
		"""Receive a dictionary from the socket.

		Utility function to receive a marshalled dictionary from
		the socket. Returns None if the request was empty.

		"""
		chunk = ''
		missing = intLength
		while missing > 0:
			block = self._sock.recv(missing)
			if not block:
				self._sock.close()
				if len(chunk) == 0:
					# We probably awakened due to awakeSelect being called.
					return None
				else:
					# We got a partial request -- something went wrong.
					raise NotEnoughDataError, 'received only %d of %d bytes' \
						' when receiving dictLength' % (len(chunk), intLength)
			chunk += block
			missing = intLength - len(chunk)
		try:
			dictLength = loads(chunk)
		except ValueError, msg:
			# Common error: client is speaking HTTP.
			if chunk[:3] == 'GET':
				self._sock.sendall('''\
HTTP/1.0 505 HTTP Version Not Supported\r
Content-type: text/plain\r
\r
Error: Invalid AppServer protocol: %s.\r
Sorry, I don't speak HTTP.  You must connect via an adapter.\r
See the Troubleshooting section of the WebKit Install Guide.\r
''' % msg)
				self._sock.close()
				return None
			print "ERROR:", msg
			print "ERROR: you can only connect to", self._serverAddress[1], \
				"via an adapter,"
			print "       like mod_webkit or wkcgi, not with a browser."
			raise
		if type(dictLength) != type(1):
			self._sock.close()
			raise ProtocolError, "Invalid AppServer protocol"
		chunk = ''
		missing = dictLength
		while missing > 0:
			block = self._sock.recv(missing)
			if not block:
				self._sock.close()
				raise NotEnoughDataError, 'received only %d of %d bytes' \
					' when receiving dict' % (len(chunk), dictLength)
			chunk += block
			missing = dictLength - len(chunk)
		return loads(chunk)


class MonitorHandler(Handler):
	"""Monitor server status.

	Monitor is a minimal service that accepts a simple protocol,
	and returns a value indicating the status of the server.

	The protocol passes a marshalled dict, much like the Adapter
	interface, which looks like ``{'format': 'XXX'}``, where XXX
	is a command (``STATUS`` or ``QUIT``). Responds with a simple
	string, either the number of requests we've received (for
	``STATUS``) or ``OK`` for ``QUIT`` (which also stops the server).

	"""
	# @@ 2003-03 ib: we should have a RESTART command, and
	# perhaps better status indicators (# of threads, etc).

	protocolName = 'monitor'
	settingPrefix = 'Monitor'

	def handleRequest(self):
		verbose = self._server._verbose
		startTime = time.time()
		if verbose:
			print "BEGIN REQUEST"
			print time.asctime(time.localtime(startTime))
		conn = self._sock
		if verbose:
			print "receiving request from", conn
		BUFSIZE = 8*1024
		requestDict = self.receiveDict()
		if requestDict['format'] == "STATUS":
			conn.send(str(self._server._requestID))
		elif requestDict['format'] == 'QUIT':
			conn.send("OK")
			conn.close()
			self._server.shutDown()


from WebKit.ASStreamOut import ASStreamOut
class TASASStreamOut(ASStreamOut):
	"""Response stream for ThreadedAppServer.

	The `TASASStreamOut` class streams to a given socket, so that when `flush`
	is called and the buffer is ready to be written, it sends the data from the
	buffer out on the socket. This is the response stream used for requests
	generated by ThreadedAppServer.

	TAS stands for ThreadedAppServer (AS for AppServer... a little redundant).

	"""

	def __init__(self, sock):
		"""Create stream.

		We get an extra `sock` argument, which is the socket which we'll
		stream output to (if we're streaming).

		"""
		ASStreamOut.__init__(self)
		self._socket = sock

	def flush(self):
		"""Flush stream.

		Calls `ASStreamOut.ASStreamOut.flush`, and if that returns True
		(indicating the buffer is full enough) then we send data from
		the buffer out on the socket.

		"""
		result = ASStreamOut.flush(self)
		if result: # a True return value means we can send
			reslen = len(self._buffer)
			sent = 0
			while sent < reslen:
				try:
					sent += self._socket.send(
						self._buffer[sent:sent+8192])
				except socket.error, e:
					if e[0] == errno.EPIPE: # broken pipe
						pass
					elif hasattr(errno, 'ECONNRESET') \
							and e[0] == errno.ECONNRESET:
						pass
					else:
						print "StreamOut Error: ", e
					break
			self.pop(sent)


class AdapterHandler(Handler):
	"""Adapter handler.

	Handles the Adapter protocol (as used in mod_webkit, wkcgi,
	WebKit.cgi, HTTPAdapter, etc). This protocol passes a marshalled
	dictionary which contains the keys ``format`` and ``environ``.
	``format`` is currently always the string ``CGI``, and ``environ``
	is a dictionary of string: string, with values like those passed
	in the environment to a CGI request (QUERY_STRING, HTTP_HOST, etc).

	The handler adds one more key, ``input``, which contains a file
	object based off the socket, which contains the body of the
	request (the POST data, for instance). It's left to Application
	to handle that data.

	"""
	protocolName = 'address'
	settingPrefix = 'Adapter'

	def handleRequest(self):
		"""Handle request.

		Creates the request dictionary, and creates a `TASASStreamOut` object
		for the response, then calls `Application.dispatchRawRequest`, which
		does the rest of the work (here we just clean up after).

		"""
		verbose = self._server._verbose
		self._startTime = time.time()

		requestDict = self.receiveDict()
		if not requestDict:
			return

		if verbose:
			requestURI = requestDict.has_key('environ') \
				and Funcs.requestURI(requestDict['environ']) or '-'
			sys.stdout.write('%5i  %s  %s\n' % (self._requestID,
				timestamp()['pretty'], requestURI))

		requestDict['input'] = self.makeInput()
		requestDict['requestID'] = self._requestID
		streamOut = TASASStreamOut(self._sock)
		transaction = self._server._app.dispatchRawRequest(requestDict, streamOut)
		streamOut.close()

		try:
			self._sock.shutdown(1)
			self._sock.close()
		except:
			pass

		if verbose:
			duration = ('%0.2f secs' % (time.time() - self._startTime)).ljust(19)
			sys.stdout.write('%5i  %s  %s\n\n' % (self._requestID,
				duration, requestURI))

		transaction._application = None
		transaction.die()
		del transaction

	def makeInput(self):
		"""Create a file-like object from the socket."""
		return self._sock.makefile("rb", 8012)

# Determines whether the main look should run in another thread.
# On Win NT/2K/XP, we run the mainloop in a different thread because
# it's not safe for Ctrl-C to be caught while manipulating the queues.
# It's not safe on Linux either, but there, it appears that Ctrl-C will
# trigger an exception in ANY thread, so this fix doesn't help.
def runMainLoopInThread():
	return os.name == 'nt'

# Set to False in DebugAppServer so Python debuggers can trap exceptions:
doesRunHandleExceptions = True

class RestartAppServerError(Exception):
	"""Raised by DebugAppServer when needed."""
	pass

os_chdir = os.chdir

def chdir(path, force=False):
	"""Execute os.chdir() with safety provision."""
	assert force, \
		"You cannot reliably use os.chdir() in a threaded environment.\n" \
		+ 16*" " + "Set force=True if you want to do it anway (using a lock)."
	os_chdir(path)

## Script usage ##

def run(workDir=None):
	"""Start the server (`ThreadedAppServer`).

	`workDir` is the server-side path for the server, which may not be
	the ``Webware/WebKit`` directory (though by default it is).

	After setting up the ThreadedAppServer we call `ThreadedAppServer.mainloop`
	to start the server main loop. It also catches exceptions as a last resort.

	"""
	global server
	server = None
	global exitStatus
	exitStatus = 0
	os.chdir = chdir # inhibit use of os.chdir()
	runAgain = True
	while runAgain: # looping in support of RestartAppServerError
		try:
			try:
				runAgain = False
				server = ThreadedAppServer(workDir)
				if runMainLoopInThread():
					# catch the exception raised by sys.exit so
					# that we can re-call it in the main thread.
					def _windowsmainloop():
						global exitStatus
						try:
							server.mainloop()
						except SystemExit, e:
							exitStatus = e[0]
					# Run the server thread
					t = threading.Thread(
						target=_windowsmainloop)
					t.start()
					try:
						while server.running > 1:
							try:
								time.sleep(1) # wait for interrupt
							except:
								if server.running < 3:
									raise # shutdown
					finally:
						t.join()
				else:
					server.mainloop()
				sys.exit(exitStatus)
			except RestartAppServerError:
				print
				print "Restarting AppServer:"
				sys.stdout.flush()
				sys.stderr.flush()
				runAgain = True
			except SystemExit, e:
				print
				print "Exiting AppServer%s." % (
					e[0] == 3 and ' for reload' or '')
				exitStatus = e[0]
			except KeyboardInterrupt:
				print
				print "Exiting AppServer due to keyboard interrupt."
				exitStatus = 0
			except Exception, e:
				if isinstance(e, IOError) and e[0] == errno.EINTR:
					print
					print "Exiting AppServer due to interrupt signal."
					exitStatus = 0
				else:
					if doesRunHandleExceptions:
						import traceback
						print
						traceback.print_exc(file=sys.stderr)
						print "Exiting AppServer due to above exception."
						exitStatus = 1
					else:
						raise
		finally:
			sys.stdout.flush()
			sys.stderr.flush()
			if server and server.running:
				server.initiateShutdown()
				server._closeThread.join()
			AppServerModule.globalAppServer = None
	sys.stdout.flush()
	sys.stderr.flush()
	os.chdir = os_chdir # allow use of os.chdir() again
	return exitStatus

# Signal handlers

def shutDown(signum, frame):
	"""Signal handler for shutting down the server."""
	print
	print "App server has been signaled to shutdown."
	if server and server.running > 2:
		print "Shutting down at", time.asctime(time.localtime(time.time()))
		sys.stdout.flush()
		server.running = 2
		if signum == SIGINT:
			raise KeyboardInterrupt
		elif signum == SIGHUP:
			sys.exit(3) # force reload
		else:
			sys.exit(0) # normal exit
	else:
		print "No running app server was found."

try:
	# Use the threadframe module for dumping thread stack frames:
	# http://www.majid.info/mylos/stories/2004/06/10/threadframe.html
	import threadframe

	def threadDump(signum, frame):
		"""Signal handler for dumping thread stack frames to stdout."""
		print
		print "App server has been signaled to attempt a thread dump."
		print
		print "Thread stack frame dump at", time.asctime(time.localtime(time.time()))
		sys.stdout.flush()
		frames = threadframe.dict()
		items = frames.items()
		items.sort()
		print
		print "-" * 79
		print
		for thread_id, frame in items:
			print "Thread ID: %d (reference count = %d)" % (
				thread_id, sys.getrefcount(frame))
			print ''.join(traceback.format_list(traceback.extract_stack(frame)))
		items.sort()
		print "-" * 79
		sys.stdout.flush()

except ImportError:
	# threadframe module not available
	threadDump = None

import signal

# Shutdown signals

try:
	SIGHUP = signal.SIGHUP
	signal.signal(SIGHUP, shutDown)
except AttributeError:
	SIGHUP = None
try:
	SIGTERM = signal.SIGTERM
	signal.signal(SIGTERM, shutDown)
except AttributeError:
	SIGTERM = None
try:
	# this is Ctrl-C on Windows
	SIGINT = signal.SIGINT
	signal.signal(SIGINT, shutDown)
except AttributeError:
	SIGINT = None

if threadDump:

	# Signals for creating a thread dump

	try:
		SIGQUIT = signal.SIGQUIT
		signal.signal(SIGQUIT, threadDump)
	except AttributeError:
		SIGQUIT = None
	try:
		# this is Ctrl-Break on Windows (not Cygwin)
		SIGBREAK = signal.SIGBREAK
		signal.signal(SIGBREAK, threadDump)
	except AttributeError:
		SIGBREAK = None


import re
settingRE = re.compile(r'^(?:--)?([a-zA-Z][a-zA-Z0-9]*\.[a-zA-Z][a-zA-Z0-9]*)=')
from MiscUtils import Configurable

usage = re.search('\n.* arguments:\n\n(.*\n)*?\n', __doc__).group(0)

def main(args):
	"""Command line interface.

	Run by `Launch`, this is the main entrance and command-line interface
	for ThreadedAppServer.

	"""
	function = run
	daemon = False
	workDir = None
	for i in args[:]:
		if settingRE.match(i):
			match = settingRE.match(i)
			name = match.group(1)
			value = i[match.end():]
			Configurable.addCommandLineSetting(name, value)
		elif i == "stop":
			import AppServer
			function = AppServer.stop
		elif i == "daemon":
			daemon = True
		elif i == "start":
			pass
		elif i[:8] == "workdir=":
			workDir = i[8:]
		else:
			print usage
			return
	if daemon:
		if os.name == "posix":
			pid = os.fork()
			if pid:
				sys.exit()
		else:
			print "Daemon mode not available on your OS."
	return function(workDir=workDir)
