def test(store):
	from Foo import Foo
	from Bar import Bar
	from BarReq import BarReq

	# Create a Foo and a Bar that refers to it
	f = Foo()
	f.setX(3)

	store.addObject(f)
	store.saveChanges()

	b = Bar()
	b.setFoo(f)
	store.addObject(b)
	store.saveChanges()

	# Test fetching
	store.clear()
	results = store.fetchObjectsOfClass(Bar)
	assert len(results)
	b = results[0]
	f1 = b.foo()
	f2 = b.foo()
	assert f1 is not None, 'got None instead of a Foo'
	assert f1 is f2  # test uniqueness
	assert b.foo().x()==3

	# Fetch in reverse order
	store.clear()
	f = store.fetchObjectsOfClass(Foo)[0]
	b = store.fetchObjectsOfClass(Bar)[0]
	assert b.foo() is f

	# Test None, set, save and retrieve
	b.setFoo(None)
	store.saveChanges()
	store.clear()
	b = store.fetchObjectsOfClass(Bar)[0]
	assert b.foo() is None

	# Test the assertions in setFoo()
	b = BarReq()
	try:		b.setFoo(None)
	except:		pass
	else:		NoException('b.setFoo(None) # None not allowed')

	try:		b.setFoo('x')
	except:		pass
	else:		NoException('b.setFoo("x") # wrong type not allowed')

	try:		b.setFoo(Bar())
	except:		pass
	else:		NoException('b.setFoo(Bar()) # wrong class not allowed')


def NoException(codeString):
	raise Exception, 'Failed to raise exception for: ' + codeString
