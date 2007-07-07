from types import ListType

from ExamplePage import ExamplePage

debug = 0


class ListBox(ExamplePage):
	"""List box example.

	This page provides a list box interface with controls
	for changing its size and adding and removing items.

	The source is a good example of how to use awake() and actions.

	It also shows how to avoid repeated exectution on refresh/reload.

	"""

	def awake(self, transaction):
		ExamplePage.awake(self, transaction)
		sess = self.session()
		if sess.hasValue('vars'):
			self._vars = sess.value('vars')
		else:
			self._vars = {
				'list':      [],
				'height':    10,
				'width':    250,
				'newCount':   1,
				'formCount':  1,
			}
			sess.setValue('vars', self._vars)
		self._error = None

	def writeContent(self):
		enc, wr = self.htmlEncode, self.writeln
		wr('<div style="text-align:center">')
		if debug:
			wr('<p>fields = %s</p>' % enc(str(self.request().fields())))
			wr('<p>vars = %s</p>' % enc(str(self._vars)))
		# Intro text is provided by our class' doc string:
		intro = self.__class__.__doc__.split('\n\n')
		wr('<h2>%s</h2>' % intro.pop(0))
		for s in intro:
			wr('<p>%s</p>' % s.replace('\n', '<br>'))
		wr('<p style="color:red">%s</p>' % (self._error or '&nbsp;'))
		wr('''
<form method="post">
<input name="formCount" type="hidden" value="%(formCount)d">
<select multiple="yes" name="list" size="%(height)d"
style="width:%(width)dpt;text-align:center">
''' % self._vars)
		index = 0
		for item in self._vars['list']:
			wr('<option value="%d">%s</option>' % (index, enc(item['name'])))
			index += 1
		wr('''
</select>
<p>
<input name="_action_new" type="submit" value="New">
<input name="_action_delete" type="submit" value="Delete">
&nbsp; &nbsp; &nbsp;
<input name="_action_taller" type="submit" value="Taller">
<input name="_action_shorter" type="submit" value="Shorter">
&nbsp; &nbsp; &nbsp;
<input name="_action_wider" type="submit" value="Wider">
<input name="_action_narrower" type="submit" value="Narrower">
</p>
</form>
</div>
''')

	def heightChange(self):
		return 1

	def widthChange(self):
		return 30


	## Commands ##

	def new(self):
		"""Add a new item to the list box."""
		req = self.request()
		self._vars['list'].append(
			{'name': 'New item %d' % self._vars['newCount']})
		self._vars['newCount'] += 1
		self.writeBody()

	def delete(self):
		"""Delete the selected items in the list box."""
		req = self.request()
		if req.hasField('list'):
			indices = req.field('list')
			if type(indices) is not ListType:
				indices = [indices]
			indices = map(int, indices) # convert strings to ints
			indices.sort() # sort...
			indices.reverse() # in reverse order
			# remove the objects:
			for index in indices:
				del self._vars['list'][index]
		else:
			self._error = 'You must select a row to delete.'
		self.writeBody()

	def taller(self):
		self._vars['height'] += self.heightChange()
		self.writeBody()

	def shorter(self):
		if self._vars['height'] > 2:
			self._vars['height'] -= self.heightChange()
		self.writeBody()

	def wider(self):
		self._vars['width'] += self.widthChange()
		self.writeBody()

	def narrower(self):
		if self._vars['width'] >= 60:
			self._vars['width'] -= self.widthChange()
		self.writeBody()


	## Actions ##

	def actions(self):
		acts = ExamplePage.actions(self)
		# check whether form is valid (no repeated execution)
		try:
			formCount = int(self.request().field('formCount'))
		except:
			formCount = 0
		if formCount == self._vars['formCount']:
			acts.extend(['new', 'delete',
				'taller', 'shorter', 'wider', 'narrower'])
			self._vars['formCount'] += 1
		return acts
