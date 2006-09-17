def test(store):
	from Line import Line
	from Rectangle import Rectangle
	
	# Note: Two inherits One

	# Simple creation and insertion	
	line = Line()
	line.setX1(1)
	line.setY1(2)
	line.setX2(3)
	line.setY2(4)
	store.addObject(line)
	
	store.saveChanges()
	store.clear()
