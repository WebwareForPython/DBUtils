#!/usr/bin/env python
"""stress.py

By Chuck Esterbrook
Mods by Jay Love

Purpose: Hit the WebKit AppServer with lots of a requests in order to:
	* Test for memory leaks
	* Test concurrency
	* Investigate performance

This stress test skips the web server and the WebKit adapter, so it's not
useful for measuring absolute performance. However, after making a
modification to WebKit or your web-based application, it can be useful to
see the relative difference in performance (although still somewhat
unrealistic).

To run:
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


import sys, os, time, socket
from glob import glob
from marshal import dumps
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
	"""Perform a single AppServer request.

	This includes sending the request and receiving the response.
	slowconn simulates a slowed connection from the client.

	"""
	complete = 0
	filecount = len(names)
	totalbytes = 0
	while complete < count:
		i = randint(0, filecount-1)
		# taken from CGIAdapter:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((host, port))
		data = dumps(dicts[i])
		s.send(dumps(len(data)))
		s.send(data)
		if delay and slowconn:
			sleep(delay)
		s.shutdown(1)
		data = []
		while 1:
			newdata = s.recv(8192)
			if not newdata:
				break
			else:
				data.append(newdata)
		data = ''.join(data)
		# process response
		# sys.stdout.write(data)
		try:
			if not data.startswith('Status: '):
				raise ValueError
			else:
				status = data.split('\n', 1)[0]
				code = int(status.split()[1])
		except:
			status = 'no status'
			code = 0
		if code not in (200,): # accepted status codes
			status = dicts[i]['environ']['PATH_INFO'] + ' ' + status
			raise Exception, status
		if delay:
			sleep(delay)
		complete += 1
		totalbytes += len(data)


def stress(maxRequests,
	minParallelRequests=1, maxParallelRequests=1, delay=0.0, slowconn=0):
	"""Execute stress test on the AppServer according to the arguments."""
	# taken from CGIAdapter:
	try:
		host, port = open('../adapter.address').read().split(':')
	except:
		print "Please start the application server first."
		return
	if os.name == 'nt' and host == '':
		# MS Windows doesn't like a blank host name
		host = 'localhost'
	port = int(port)
	bufsize = 32*1024
	# get the requests from .rr files
	# which are expected to contain raw request dictionaries
	requestFilenames = glob('*.rr')
	requestDicts = map(lambda filename:
		eval(open(filename).read()), requestFilenames)
	# kill the HTTP cookies (which typically have an invalid session id)
	# from when the raw requests were captured
	for dict in requestDicts:
		environ = dict['environ']
		if environ.has_key('HTTP_COOKIE'):
			del environ['HTTP_COOKIE']
	requestCount = len(requestFilenames)
	if maxParallelRequests < minParallelRequests:
		maxParallelRequests = minParallelRequests
	sequential = minParallelRequests == 1 and maxParallelRequests == 1
	startTime = time()
	count = 0
	print 'STRESS TEST for Webware.WebKit.AppServer'
	print
	print 'time                =', asctime(localtime(startTime))
	print 'requestFilenames    =', requestFilenames
	print 'maxRequests         =', maxRequests
	print 'minParallelRequests =', minParallelRequests
	print 'maxParallelRequests =', maxParallelRequests
	print 'delay               = %g' % delay
	print 'sequential          =', sequential
	print 'Running...'
	threads = []
	for i in range(maxParallelRequests):
		num = randint(minParallelRequests, maxParallelRequests)
		num = maxRequests/num
		thread = Thread(target=request, args=(
			requestFilenames, requestDicts, host, port, num, delay, slowconn))
		thread.start()
		threads.append(thread)
		count += num
	# wait till all threads are finished
	for thread in threads:
		thread.join()
	threads = None
	duration = time() - startTime
	print 'count                = %d' % count
	print 'duration             = %g' % duration
	print 'secs/page            = %g' % (duration/count)
	if duration:
		print 'pages/sec            = %g' % (count/duration)
	print 'Done.'
	print


if __name__ == '__main__':
	if len(sys.argv) == 1:
		usage()
	else:
		args = map(eval, sys.argv[1:])
		stress(*args)
