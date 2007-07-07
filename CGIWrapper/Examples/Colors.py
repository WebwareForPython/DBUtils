
if fields.has_key('bgcolor'):
	bgcolor = fields['bgcolor'].value
	bgcolorArg = 'bgcolor=' + bgcolor
else:
	bgcolor = ''
	bgcolorArg = ''

print '''
<html>
	<head>
		<title>Colors</title>
	</head>
	<body %s>
		<p align=center><font size=+1><b>Colors</b></font></p>

		<center>
		<form>
			bgcolor: <input type=next name=bgcolor value="%s">
			<input type=submit value=Go>
		</form>
		</center>

		<p><table align=center>
''' % (bgcolorArg, bgcolor)

space = '&nbsp;'*10
gamma = 2.2  # an approximation for today's CRTs, see "brightness =" below

for r in range(11):
	r = r/10.0
	for g in range(11):
		g = g/10.0
		print '<tr>'
		for b in range(11):
			b = b/10.0
			color = '#%02x%02x%02x' % (r*255, g*255, b*255)
			# Compute brightness given RGB
			brightness = (0.3*r**gamma + 0.6*g**gamma + 0.1*b**gamma)**(1/gamma)
			# We then use brightness to determine a good font color for high contrast
			if brightness < 0.5:
				textcolor = 'white'
			else:
				textcolor = 'black'
			print '<td bgcolor=%s> <br> <font color=%s>%s</font> </td>' % (color, textcolor, color)
		print '</tr>'

print '''
		</table>
	</body>
</html>'''
