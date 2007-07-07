"""Profiler.py

Stores some values related to performance.
These are usually set by Launch.py or AppServer.py.

To get profiling going, locate the "runProfile = 0" line towards the top
of WebKit/Launch.py and change the "0" to a "1", or start the Launch.py
script with the --run-profile option. When the app server shuts down it
will write a profiling report "profile.pstats" in the directory containing
the Launch.py script which can be quickly examined from the command line:

	$ cd Webware
	$ bin/printprof.py WebKit/profile.pstats

You might also wish to dump the profiling stats on demand (as in, by
clicking or reloading a URL for that purpose). Read further for details.

The variables in this module are:

profiler
	An instance of Python's profile.Profiler, but only if Launch.py is
	started with profiling enabled. Otherwise, this is None.
	You could access this from a servlet in order to dump stats:

		from WebKit.Profiler import dumpStats
		dumpStats()

	With some work, you could dump them directly to the page in a
	readable format.

startTime
	The earliest recordable time() when the app server program was
	launched.

readyTime
readyDuration
	The time() and duration from startTime for when the app server
	was ready to start accepting requests. A smaller readyDuration
	makes application reloading faster which is useful when
	developing with AutoReload on.
	
"""

profiler = startTime = readyTime = readyDuration = None

# Convenience

statsFilename = 'profile.pstats'

def runCall(func, *args, **kwargs):
	return profiler.runcall(func, *args, **kwargs)

def dumpStats(file=statsFilename):
	profiler.dump_stats(file)

def reset():
	"""
	Invoked by DebugAppServer in support of AutoReload.
	"""
	global startTime
	import time
	startTime = time.time()
