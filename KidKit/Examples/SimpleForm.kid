<?xml version='1.0' encoding='utf-8'?>
<?python
from KidKit.Examples.KidExamplePage import KidExamplePage
hook = KidExamplePage.writeContent
?>
<div style="text-align:center"
    xmlns:py="http://purl.org/kid/ns#">
<?python
# Note that the above div element is the root element of this page,
# because it is embedded in the body of the KidExamplePage template.
# For a stand-alone page, the html element will be the root element.
# Also, note that this Python block is just inside the root element.
# That makes it "local-level", where the 'servlet' variable is available.
# Outside the root element, the servlet is not yet instantiated.
fields = servlet.request().fields()
name = fields.get('name') or 'stranger'
?>
<h1>Kid Form Demo</h1>
<p>Hello <strong py:content="name" />, how are you?</p>
<form action="" method="get">
<p>Enter your name here:</p>
<p><input type="text" name="name" /></p>
<p><input type="submit" name="Submit" value="Submit" /></p>
</form>
</div>
