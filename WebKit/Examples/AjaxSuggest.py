#
# Ajax "Suggest" Example
#
# Written by Robert Forkel based on wiki.w4py.org/ajax_in_webware.html
# and www.dynamicajax.com/fr/AJAX_Suggest_Tutorial-271_290_312.html,
# with minor changes made by Christoph Zwerschke.
#

from random import randint

from AjaxPage import AjaxPage

maxSuggestions = 10
maxWords = 5000
maxLetters = 5

# Create some random "words":
suggestions = []
for i in range(maxWords):
	word = []
	for j in range(maxLetters):
		word.append(chr(randint(97, 122)))
	suggestions.append(''.join(word))


class AjaxSuggest(AjaxPage):

	_clientPolling = None # we have no long-running queries

	def writeJavaScript(self):
		AjaxPage.writeJavaScript(self)
		self.writeln('<script type="text/javascript" src="ajaxsuggest.js"></script>')

	def writeStyleSheet(self):
		AjaxPage.writeStyleSheet(self)
		self.writeln('<link rel="stylesheet" href="ajaxsuggest.css" type="text/css">')

	def htBodyArgs(self):
		return AjaxPage.htBodyArgs(self) + ' onload="initPage();"'

	def writeContent(self):
		self.writeln('<h2>Ajax "Suggest" Example</h2>')
		if self.request().hasField('query'):
			self.writeln('''
<p>You have just entered the word <b class="in_red">"%s"</b>.</p>
<p>If you like, you can try again:</p>'''
				% self.htmlEncode(self.request().field('query')))
		else:
			self.writeln('''
<p>This example uses Ajax techniques to make suggestions
based on your input as you type.</p>
<p>Of course, you need a modern web browser with
JavaScript enabled in order for this to work.</p>
<p>Start typing in some lowercase letters,
and get random words starting with these characters suggested:</p>''')
		self.writeln('''<form><div>
<input type="text" name="query" id="query" onkeyup="getSuggestions();" autocomplete="off">
<input type="submit" value="Submit"></div><div class="hide" id="suggestions"></div></form>''')

	def exposedMethods(self):
		"""Register the suggest method for use with Ajax."""
		return ['suggest']

	def suggest(self, prefix):
		"""We return a JavaScript function call as string.

		The JavaScript function we want called is `handleSuggestions`
		and we pass an array of strings starting with prefix.

		Note: to pass more general Python objects to the client side, use JSON,
		e.g. using json-py's (sourceforge.net/projects/json-py/) JsonWriter.

		"""
		s = filter(lambda w, prefix=prefix:
			w.startswith(prefix), suggestions) or ['none']
		return "handleSuggestions([%s]);" % ",".join(
			map(lambda w: "'%s'" % w, s[:maxSuggestions]))
