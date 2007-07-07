import os

def test(store):
	samples = open('Dump.csv', 'w')
	store.dumpObjectStore(samples)
	samples.close()

	command = 'diff -u ../MKDump.mkmodel/Samples.csv Dump.csv'
	print command
	retval = os.system(command)
	retval >>= 8  # upper byte is the return code

	assert retval == 0
