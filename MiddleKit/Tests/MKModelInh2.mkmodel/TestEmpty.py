def test(store):
	from Foo import Foo
	from MiscUtils.DataTable import DataTable

	dataSource = '''
b:int,i:int,l:long,f:float,s:string,x:int
0,0,0,0,0,0
0,0,0,0.0,0.0,0
1,1,1,1,a,1
0,-1,8589934592,-3.14,'x',3
'''

	data = DataTable()
	data.readString(dataSource)

	for values in data:
		print values

		t = Foo()
		for attr in list('bilfsx'):
			t._set(attr, values[attr])

		store.addObject(t)
		store.saveChanges()

		# Try an immediate fetch
		results = store.fetchObjectsOfClass(Foo)
		assert len(results) == 1
		# This tests the uniquing feature of MiddleKit:
		assert id(results[0]) == id(t)

		# Clear the store's in memory objects and try a fetch again
		store.clear()
		results = store.fetchObjectsOfClass(Foo)
		assert len(results) == 1
		assert results[0].allAttrs() == t.allAttrs()

		# Make sure what we got from the store is what we put in
		for attr in list('bilsx'):
			assert results[0]._get(attr) == values[attr]

		different = 0.000001 # @@ 2000-11-25 ce: more work needed on floats
		assert abs(results[0]._get('f')-values['f']) < different

		# Insert the fetched attributes
		t2 = Foo()
		for attr in list('bilfsx'):
			t2._set(attr, results[0]._get(attr))
		store.addObject(t2)
		store.saveChanges()
		results = store.fetchObjectsOfClass(Foo)
		assert len(results) == 2, 'len=%r' % len(results)
		assert results[0].allAttrs() == results[1].allAttrs()

		# Reset
		store.clear()
		store.executeSQL('delete from Foo;')
