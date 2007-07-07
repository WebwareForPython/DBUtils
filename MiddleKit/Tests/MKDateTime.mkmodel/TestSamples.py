def test(store):
	from Foo import Foo

	f = store.fetchObjectsOfClass(Foo)[0]

	from MiddleKit.Design.PythonGenerator import nativeDateTime, mxDateTime

	value = f.d()
	match = None
	if nativeDateTime:
		match = value == nativeDateTime.date(2000, 1, 1)
	if not match and mxDateTime:
		match = value == mxDateTime.DateTime(2000, 1, 1)
	assert match, value

	value = f.t()
	match = None
	if nativeDateTime:
		match = value == store.filterDateTimeDelta(nativeDateTime.time(13, 01))
		if not match:
			match = value == nativeDateTime.timedelta(hours=13, minutes=01)
	if not match and mxDateTime:
		match = value == mxDateTime.DateTimeDeltaFrom('13:01')
	assert match, '%s, %s' % (value, type(value))

	value = f.dt()
	match = None
	if nativeDateTime:
		match = value == nativeDateTime.datetime(2000, 1, 1, 13, 1)
	if not match and mxDateTime:
		match = value == mxDateTime.DateTime(2000, 1, 1, 13, 1)
	assert match, value
