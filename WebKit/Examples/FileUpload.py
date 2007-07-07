from ExamplePage import ExamplePage
from WebUtils import Funcs


class FileUpload(ExamplePage):
	"""This servlet shows how to handle uploaded files.

	The process is fairly self explanatory. You use a form like the one below in the
	writeContent method. When the form is uploaded, the request field with the name you
	gave to the file selector form item will be an instance of the FieldStorage class from
	the standard Python module "cgi". The key attributes of this class are shown in the
	example below. The most important things are filename, which gives the name of the
	file that was uploaded, and file, which is an open file handle to the uploaded file.
	The uploaded file is temporarily stored in a temp file created by the standard module.
	You'll need to do something with the data in this file. The temp file will be
	automatically deleted. If you want to save the data in the uploaded file read it out
	and write it to a new file, database, whatever.

	"""

	def title(self):
		return "File Upload Example"

	def writeContent(self):
		self.writeln("<h1>Upload Test</h1>")
		try:
			f = self.request().field('filename')
			contents = f.file.read()
		except:
			output = '''<p>%s</p>
<form method="post" enctype="multipart/form-data">
<input type="file" name="filename">
<input type="submit" value="Upload File">
</form>''' % Funcs.htmlEncode(self.__doc__)
		else:
			output = '''<h4>Here's the file you submitted:</h4>
	<table border cellspacing="0" cellpadding="6">
	<tr><th>name</th><td><strong>%s</strong></td></tr>
	<tr><th>type</th><td>%s</td></tr>
	<tr><th>type_options</th><td>%s</td></tr>
	<tr><th>disposition</th><td>%s</td></tr>
	<tr><th>disposition_options</th><td>%s</td></tr>
	<tr><th>headers</th><td>%s</td></tr>
	<tr><th>size</th><td>%s bytes</td></tr>
	<tr><th valign="top">contents</th>
	<td><pre style="font-size:small;margin:0pt">%s</pre></td></tr>
	</table>''' % (
				f.filename, f.type, f.type_options,
				f.disposition, f.disposition_options,
				f.headers, len(contents),
				Funcs.htmlEncode(contents.strip()))
		self.writeln(output)
