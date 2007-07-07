def test(store):
	# We're testing to see if the defaults made it
	# into the database. We have a row with i == 42
	# and all other fields blank and s == '42' and
	# all other fields blank.
	# Our defaults for b, i, l, f, s are
	# 1, 2, 3, 4.0, '5'.

	foos = store.fetchObjectsOfClass('Foo')
	foo = [foo for foo in foos if foo._get('i') == 42][0]
	assert foo._get('b') == 1
	assert foo._get('l') == 3
	assert foo._get('f') == 4.0
	assert foo._get('s') == '5'

	foo = [foo for foo in foos if foo._get('s') == '42'][0]
	assert foo._get('i') == 2

	# Next we test if we were able to specify 'none'
	# for attributes that have defaults.
	# We marked these objects with 43.
	foo = [foo for foo in foos if foo._get('i') == 43][0]
	assert foo._get('b') is None
	assert foo._get('l') is None
	assert foo._get('f') is None
	assert foo._get('s') is None

	foo = [foo for foo in foos if foo._get('s') == '43'][0]
	assert foo._get('i') is None
