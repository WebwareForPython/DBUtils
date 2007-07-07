def test(store):
	from Foo import Foo

	f = Foo()

	# legal sets:
	f.setRi(1)
	f.setNi(2)
	f.setRs('a')
	f.setNs('b')
	f.setNi(None)
	f.setNs(None)

	# illegal sets:
	errMsg = 'Set None for required attribute, but no exception was raised.'
	try:
		f.setRi(None)
	except:
		pass
	else:
		raise Exception, errMsg

	try:
		f.setRs(None)
	except:
		pass
	else:
		raise Exception, errMsg

	store.addObject(f)
	store.saveChanges()
	store.clear()

	results = store.fetchObjectsOfClass(Foo)
	assert len(results) == 1
	f = results[0]
	assert f.ri() == 1
	assert f.ni() is None
	assert f.rs() == 'a'
	assert f.ns() is None

	return

	from MiscUtils.DataTable import DataTable

	dataSource = '''
b:int,i:int,l:long,f:float,s:string
0,0,0,0,0
0,0,0,0.0,0.0
1,1,1,1,a
0,-1,8589934592,-3.14,'x'
'''

	data = DataTable()
	data.readString(dataSource)

	for values in data:
		print values

		t = Thing()
		t.setB(values['b'])
		t.setI(values['i'])
		t.setL(values['l'])
		t.setF(values['f'])
		t.setS(values['s'])

		store.addObject(t)
		store.saveChanges()

		# Try an immediate fetch
		results = store.fetchObjectsOfClass(Thing)
		assert len(results) == 1
		# This tests the uniquing feature of MiddleKit:
		assert id(results[0]) == id(t)

		# Clear the store's in memory objects and try a fetch again
		store.clear()
		results = store.fetchObjectsOfClass(Thing)
		assert len(results) == 1
		assert results[0].allAttrs() == t.allAttrs()

		# Make sure what we got from the store is what we put in
		assert t.b() == values['b']
		assert t.i() == values['i']
		assert t.l() == values['l']
		assert t.f() == values['f']
		assert t.s() == values['s']

		# Reset
		store.clear()
		store.executeSQL('delete from Thing;')
		del t
