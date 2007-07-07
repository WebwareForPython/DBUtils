from Common import *
from WebUtils import Funcs
from HTTPContent import HTTPContent, HTTPContentError
from Application import EndResponse


class Page(HTTPContent):
	"""The standard web page template.

	Page is a type of HTTPContent that is more convenient for servlets
	which represent HTML pages generated in response to GET and POST requests.
	In fact, this is the most common type of Servlet.

	Subclasses typically override `writeHeader`, `writeBody` and `writeFooter`.

	They might also choose to override `writeHTML` entirely.

	When developing a full-blown website, it's common to create a subclass of
	`Page` called `SitePage` which defines the common look and feel of the
	website and provides site-specific convenience methods. Then all other
	pages in your application then inherit from `SitePage`.

	"""


	## Transactions ##

	def defaultAction(self):
		"""The default action in a Page is to writeHTML()."""
		self.writeHTML()


	## Generating results ##

	def title(self):
		"""The page title.

		Subclasses often override this method to provide a custom title.
		This title should be absent of HTML tags. This implementation
		returns the name of the class, which is sometimes appropriate
		and at least informative.

		"""
		return self.__class__.__name__

	def htTitle(self):
		"""The page title as HTML.

		Return self.title(). Subclasses sometimes override this to provide
		an HTML enhanced version of the title. This is the method that should
		be used when including the page title in the actual page contents.

		"""
		return self.title()

	def htBodyArgs(self):
		"""The atrributes for the <body> element.

		Returns the arguments used for the HTML <body> tag.
		Invoked by writeBody().

		With the prevalence of stylesheets (CSS), you can probably skip
		this particular HTML feature, but for historical reasons this sets
		the page to black text on white.

		"""
		return 'text="black" bgcolor="white"'

	def writeHTML(self):
		"""Write all the HTML for the page.

		Subclasses may override this method (which is invoked by `_respond`)
		or more commonly its constituent methods, `writeDocType`, `writeHead`
		and `writeBody`.

		You will want to override this method if:
		* you want to format the entire HTML page yourself
		* if you want to send an HTML page that has already
		  been generated
		* if you want to use a template that generates the entire
		  page
		* if you want to send non-HTML content (be sure to
		  call ``self.response().setHeader('Content-type',
		  'mime/type')`` in this case).

		"""
		self.writeDocType()
		self.writeln('<html>')
		self.writeHead()
		self.writeBody()
		self.writeln('</html>')

	def writeDocType(self):
		"""Write the DOCTYPE tag.

		Invoked by `writeHTML` to write the ``<!DOCTYPE ...>`` tag.

		By default this gives the HTML 4.01 Transitional DOCTYPE,
		which is a good guess for what most people send.  Be
		warned, though, that some browsers render HTML differently
		based on the DOCTYPE (particular newer browsers, like
		Mozilla, do this).

		Subclasses may override to specify something else.

		You can find out more about doc types by searching for
		DOCTYPE on the web, or visiting:
		http://www.htmlhelp.com/tools/validator/doctype.html

		"""
		# @@ sgd-2003-01-29 - restored the 4.01 transitional as
		# per discussions on the mailing list for the 0.8 release.
		self.writeln('<!DOCTYPE HTML PUBLIC'
			' "-//W3C//DTD HTML 4.01 Transitional//EN"'
			' "http://www.w3.org/TR/html4/loose.dtd">')

	def writeHead(self):
		"""Write the <head> element of the page.

		Writes the ``<head>`` portion of the page by writing the
		``<head>...</head>`` tags and invoking `writeHeadParts` in between.

		"""
		wr = self.writeln
		wr('<head>')
		self.writeHeadParts()
		wr('</head>')

	def writeHeadParts(self):
		"""Write the parts included in the <head> element.

		Writes the parts inside the ``<head>...</head>`` tags.
		Invokes `writeTitle` and then `writeMetaData`, `writeStyleSheet`
		and `writeJavaScript`. Subclasses should override the `title`
		method and the three latter methods only.

		"""
		self.writeTitle()
		self.writeMetaData()
		self.writeStyleSheet()
		self.writeJavaScript()

	def writeTitle(self):
		"""Write the <title> element of the page.

		Writes the ``<title>`` portion of the page.
		Uses `title`, which is where you should override.

		"""
		self.writeln('\t<title>%s</title>' % self.title())

	def writeMetaData(self):
		"""Write the meta data for the page.

		This default implementation does nothing.
		Subclasses should override if necessary.

		A typical implementation is:

		    self.writeln('\t<meta http-equiv="content-type" content="text/html; charset=ISO-8859-1">')

		"""
		pass

	def writeStyleSheet(self):
		"""Write the CSS for the page.

		This default implementation does nothing.
		Subclasses should override if necessary.

		A typical implementation is:

		    self.writeln('\t<link rel="stylesheet" href="StyleSheet.css" type="text/css">')

		"""
		pass

	def writeJavaScript(self):
		"""Write the JavaScript for the page.

		This default implementation does nothing.
		Subclasses should override if necessary.

		A typical implementation is:

		    self.writeln('\t<script type="text/javascript" src="ajax.js"></script>')

		"""
		pass

	def writeBody(self):
		"""Write the <body> element of the page.

		Writes the ``<body>`` portion of the page by writing the
		``<body>...</body>`` (making use of `htBodyArgs`) and
		invoking `writeBodyParts` in between.

		"""
		wr = self.writeln
		bodyArgs = self.htBodyArgs()
		if bodyArgs:
			wr('<body %s>' % bodyArgs)
		else:
			wr('<body>')
		self.writeBodyParts()
		wr('</body>')

	def writeBodyParts(self):
		"""Write the parts included in the <body> element.

		Invokes `writeContent`. Subclasses should only override this method
		to provide additional page parts such as a header, sidebar and footer,
		that a subclass doesn't normally have to worry about writing.

		For writing page-specific content, subclasses should override
		`writeContent`() instead. This method is intended to be overridden
		by your SitePage.

		See `SidebarPage` for an example override of this method.

		Invoked by `writeBody`.

		"""
		self.writeContent()

	def writeContent(self):
		"""Write the unique, central content for the page.

		Subclasses should override this method (not invoking super) to write
		their unique page content.

		Invoked by `writeBodyParts`.

		"""
		self.writeln('<p> This page has not yet customized its content. </p>')

	def preAction(self, actionName):
		"""Things to do before actions.

		For a page, we first writeDocType(), <html>, and then writeHead().

		"""
		self.writeDocType()
		self.writeln('<html>')
		self.writeHead()

	def postAction(self, actionName):
		"""Things to do after actions.

		Simply close the html tag (</html>).

		"""
		self.writeln('</html>')


	## Convenience Methods ##

	def htmlEncode(self, s):
		"""HTML encode special characters.
		Alias for `WebUtils.Funcs.htmlEncode`, quotes the special characters
		&, <, >, and \"

		"""
		return Funcs.htmlEncode(s)

	def htmlDecode(self, s):
		"""HTML decode special characters.

		Alias for `WebUtils.Funcs.htmlDecode`. Decodes HTML entities.

		"""
		return Funcs.htmlDecode(s)


	## Validate HTML output (developer debugging) ##

	def validateHTML(self, closingTags='</body></html>'):
		"""Validate the response.

		Validate the current response data using Web Design Group's
		HTML validator available at
		http://www.htmlhelp.com/tools/validator/

		Make sure you install the offline validator (called
		``validate``) which can be called from the command-line.
		The ``validate`` script must be in your path.

		Add this method to your SitePage (the servlet from
		which all your servlets inherit), override
		Page.writeBodyParts() in your SitePage like so::

		    def writeBodyParts(self):
		        Page.writeBodyParts()
		        self.validateHTML()

		The ``closingtags`` param is a string which is appended
		to the page before validation.  Typically, it would be
		the string ``</body></html>``.  At the point this method
		is called (e.g. from `writeBodyParts`) the page is not
		yet 100% complete, so we have to fake it.

		"""
		# don't bother validating if the servlet has redirected
		status = self.response().header('status', None)
		if status and status.find('Redirect') != -1:
			return
		response = self.response().rawResponse()
		contents = response['contents'] + closingTags
		from WebUtils import WDGValidator
		errorText = WDGValidator.validateHTML(contents)
		if not errorText:
			return
		self.write(errorText)
