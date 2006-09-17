#!/usr/bin/env python
"""
stress.py
By Chuck Esterbrook
Mods by Jay Love

Purpose: Hit the WebKit AppServer with lots of a requests in order to:
	* Test for memory leaks
	* Test concurrency
	* Investigate performance

This stress test skips the web server and the WebKit adaptor, so it's not
useful for measuring absolute performance. However, after making a
modification to WebKit or your web-based application, it can be useful to
see the relative difference in performance (although still somewhat
unrealistic).

To Run:
	> stress.py  -OR-
	> python stress.py

This will give you the usage (and examples) which is:
	stress.py numRequests [minParallelRequests [maxParallelRequests [delay]]]

Programmatically, you could could also import this file and use the
stress() function.

To capture additional '.rr' files, which contain raw request
dictionaries, make use of the CGIAdaptor and uncomment the lines therein
that save the raw requests.

Caveat: HTTP cookies are blown away from the raw requests. Mostly due to
the fact that they will contain stale session ids.
"""


import sys, os, time
from glob import glob
from socket import *
from marshal import dumps
from thread import start_new_thread
from random import randint
from time import asctime, localtime, time, sleep
from threading import Thread


def usage():
	""" Prints usage of this program and exits. """
	sys.stdout = sys.stderr
	name = sys.argv[0]
	print '%s usage:' % name
	print '  %s numRequests [minParallelRequests [maxParallelRequests [delay]]]' % name
	print 'Examples:'
	print '  %s 100            # run 100 sequential requests' % name
	print '  %s 100 5          # run 100 requests, 5 at a time' % name
	print '  %s 100 5 10       # run 100 requests, 5-10 at a time' % name
	print '  %s 100 10 10 0.01 # run 100 requests, 10 at a time, with a delay between each set' % name
	print
	sys.exit(1)


def request(names, dicts, host, port, count, delay=0, slowconn=0):
	"""
	Performs a single AppServer request including sending the request and receiving the response.
	slowconn simulates a slowed connection from the client.
	"""
	complete = 0
	filecount = len(names)
	totalbytes = 0
	while complete < count:
		i = randint(0, filecount-1)
		# Taken from CGIAdaptor:
		s = socket(AF_INET, SOCK_STREAM)
		s.connect((host, port))
		data = dumps(dicts[i])
		s.send(dumps(len(data)))
		s.send(data)
		if delay and slowconn:
			sleep(delay)
		s.shutdown(1)
		data = ''
		while 1:
			newdata = s.recv(8192)
			if not newdata:
				break
			else:
				data = data+newdata
			#sys.stdout.write(data)
		# END
		if data.count('Session Expired'):
			raise Exception, 'Session expired.'
		if delay:
			sleep(delay)
		complete = complete +1
		totalbytes = totalbytes+len(data)

def stress(maxRequests, minParallelRequests=1, maxParallelRequests=1, delay=0.0, slowconn=0):
	""" Executes a stress test on the AppServer according to the arguments. """

	# Taken from CGIAdaptor:
	(host, port) = open('../address.text').read().split(':')
	if os.name == 'nt' and host == '': # MS Windows doesn't like a blank host name
		host = 'localhost'
	port = int(port)
	bufsize = 32*1024
	# END

	# Get the requests from .rr files which are expected to contain raw request dictionaries
	requestFilenames = glob('*.rr')
	requestDicts = map(lambda filename: eval(open(filename).read()), requestFilenames)
	# Kill the HTTP cookies, which typically have an invalid session id
	# from when the raw requests were captured.
	for dict in requestDicts:
		environ = dict['environ']
		if environ.has_key('HTTP_COOKIE'):
			del environ['HTTP_COOKIE']
	requestCount = len(requestFilenames)
	count = 0

	if maxParallelRequests<minParallelRequests:
		maxParallelRequests = minParallelRequests
	sequential = minParallelRequests==1 and maxParallelRequests==1

	startTime = time()
	count = 0
	print 'STRESS TEST for Webware.WebKit.AppServer'
	print
	print 'time                =', asctime(localtime(time()))
	print 'requestFilenames    =', requestFilenames
	print 'maxRequests         =', maxRequests
	print 'minParallelRequests =', minParallelRequests
	print 'maxParallelRequests =', maxParallelRequests
	print 'delay               = %0.02f' % delay
	print 'sequential          =', sequential
	print 'Running...'


	threads = []
	for i in range(maxParallelRequests):
		num = randint(minParallelRequests, maxParallelRequests)
		num = maxRequests/num
		thread = Thread(target=request, args=(requestFilenames, requestDicts, host, port, num, delay, slowconn))
		thread.start()
		threads.append(thread)
		count = count + num
	# Wait till all threads are finished
	for thread in threads:
		thread.join()
	threads = None
	duration = time()-startTime
	print 'count                = %d' % count
	print 'duration             = %0.2f' % duration
	print 'secs/page            = %0.2f' % (duration/count)
	print 'pages/sec            = %0.2f' % (count/duration)
	print 'Done.'
	print


if __name__=='__main__':
	if len(sys.argv)==1:
		usage()
	else:
		args = map(lambda arg: eval(arg), sys.argv[1:])
		apply(stress, args)
