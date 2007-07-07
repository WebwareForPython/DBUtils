from Foo import Foo


def test(store):
	try:
		import datetime
		testNativeDateTime(store)
	except ImportError:
		pass

	try:
		from mx import DateTime
		testMXDateTime(store)
	except ImportError:
		pass

	testNone(store)


def testStrings(store):
	print 'Testing with strings.'

	f = Foo()
	f.setD('2001-06-07')
	f.setT('12:42')
	f.setDt('2001-06-07 12:42')

	storeFoo(store, f)

	f.setD('2002-11-11')
	f.setT('16:04')
	f.setDt('2002-11-11 16:04')

	store.saveChanges()


def testNativeDateTime(store):
	import datetime
	print 'Testing with the native datetime module.'

	d = datetime.date(2001, 6, 7)
	t = datetime.time(12, 42)
	dt = datetime.datetime(2001, 6, 7, 12, 42)

	f = Foo()
	f.setD(d)
	f.setT(t)
	f.setDt(dt)

	storeFoo(store, f)

	d = datetime.date(2002, 11, 11)
	t = datetime.time(16, 04)
	dt = datetime.datetime(2002, 11, 11, 16, 0)

	f.setD(d)
	f.setT(t)
	f.setDt(dt)

	store.saveChanges()


def testMXDateTime(store):
	import mx
	from mx.DateTime import DateTimeFrom, TimeFrom
	print 'Testing with mx.DateTime module.'

	d  = DateTimeFrom('2001-06-07')
	t  = TimeFrom('12:42')
	dt = DateTimeFrom('2001-06-07 12:42')

	f = Foo()
	f.setD(d)
	f.setT(t)
	f.setDt(dt)

	storeFoo(store, f)

	d  = DateTimeFrom('2002-11-11')
	t  = TimeFrom('16:04')
	dt = DateTimeFrom('2002-11-11 16:04')

	f.setD(d)
	f.setT(t)
	f.setDt(dt)

	store.saveChanges()

	# test parsing of strings, a convenience feature when using mx.DateTime:
	f.setD('2002-11-11')
	f.setT('16:04')
	f.setDt('2002-11-11 16:04')

	store.saveChanges()


def storeFoo(store, f):
	store.addObject(f)
	store.saveChanges()

	store.clear()

	results = store.fetchObjectsOfClass(Foo)
	assert len(results) == 1
#	results[0].dumpAttrs()

	store.executeSQL('delete from Foo;')


def testNone(store):
	print 'Testing None.'

	store.executeSQL('delete from Foo;')

	f = Foo()
	f.setD(None)
	f.setT(None)
	f.setDt(None)

	store.addObject(f)
	store.saveChanges()
	store.clear()

	results = store.fetchObjectsOfClass(Foo)
	assert len(results) == 1
	f = results[0]
	assert f.d() is None
	assert f.t() is None
	assert f.dt() is None
