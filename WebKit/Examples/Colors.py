import os
from ExamplePage import ExamplePage


# Helper functions

gamma = 2.2 # an approximation for today's CRTs

def brightness(r, g, b):
	"""Calculate brightness of RGB color."""
	r, g, b = map(lambda x: x/255.0, (r, g, b))
	return (0.3*r**gamma + 0.6*g**gamma + 0.1*b**gamma)**(1/gamma)

def textcolor(r, g, b):
	"""Determine a good text font color for high contrast."""
	return brightness(r, g, b) < 0.5 and 'white' or 'black'

def RGBToHTMLColor(r, g, b):
	"""Convert r, g, b to #RRGGBB."""
	return '#%02X%02X%02X' % (r, g, b)

def HTMLColorToRGB(h):
	"""Convert #RRGGBB to r, g, b."""
	h = h.strip()
	if h.startswith('#'):
		h = h[1:]
	h = h[:2], h[2:4], h[4:]
	return map(lambda x: int(x, 16), h)

# Prepare HTML for color table

numSteps = 6 # this gives the "web-safe" color palette
steps = map(lambda x: 255.0*x/(numSteps-1), range(numSteps))

colorTable = [
	'<p>Click on one of the colors below to set the background color.</p>',
	'<table cellpadding="4" cellspacing="4"'
		' style="margin-left:auto;margin-right:auto">']
for r in steps:
	for g in steps:
		colorTable.append('<tr>\n')
		for b in steps:
			color = RGBToHTMLColor(r, g, b)
			colorTable.append('<td style="background-color:%s;color:%s"'
				' onclick="document.forms[0].elements[0].value=\'%s\';'
				'document.forms[0].submit()">%s</td>\n'
				% (color, textcolor(r, g, b), color, color))
		colorTable.append('</tr>\n')
colorTable.append('</table>')
colorTable = ''.join(colorTable)


class Colors(ExamplePage):
	"""Colors demo.

	This class is a good example of caching. The color table that
	this servlet creates never changes, so the servlet caches this
	in the global colorTable variable. The original version of this
	example did no caching and was 12 times slower.

	"""

	def htBodyArgs(self):
		"""Write the attributes of the body element.

		Overridden in order to throw in the custom background color
		that the user can specify in our form.

		"""
		self._bgcolor = self.request().field('bgcolor', '#FFFFFF')
		try:
			r, g, b = HTMLColorToRGB(self._bgcolor)
			self._color = textcolor(r, g, b)
		except:
			self._color = 'black'
		return 'text="black" bgcolor="%s" style="background-color:%s"' \
			% ((self._bgcolor,)*2)

	def writeContent(self):
		"""Write the actual content of the page."""
		self.write('''
			<div style="text-align:center;color:%s">
			<h3>Color Table Demo</h3>
			<form>
				Background color: <input type="text" name="bgcolor" value="%s">
				<input type="submit" value="Go">
			</form>
			%s
			</div>
			''' % (self._color, self._bgcolor, colorTable))
