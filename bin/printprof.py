#!/usr/bin/env python
import sys

cutoff = 15

def heading(s):
	print
	print s
	print '-'*40

def error(s):
	print 'ERROR:', s
	sys.exit(1)

for arg in sys.argv[1:]:
	try:
		cutoff = int(arg)
	except ValueError:
		filename = arg

import pstats
stats = pstats.Stats(filename)

heading('cumulative')
stats.sort_stats('cumulative')
stats.print_stats(cutoff)

heading('calls')
stats.sort_stats('calls')
stats.print_stats(cutoff)

heading('time')
stats.sort_stats('time')
stats.print_stats(cutoff)
