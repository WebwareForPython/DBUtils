<?xml version='1.0' encoding='utf-8'?>

<?python # this is needed to embed the page as a KidExample:
from KidKit.Examples.KidExamplePage import KidExamplePage
hook = KidExamplePage.writeContent ?>

<body py:strip="" xmlns:py="http://purl.org/kid/ns#">

<h1 style="text-align:center;color:navy">Hello from <tt style="padding:4pt">Kid</tt>!</h1>

<p style="text-align:center"><img src="kidlogo.png" /><!-- This image is served by WebKit --></p>

<p>This is the <strong>KidKit</strong> plug-in that allows you
to automatically compile and run <strong>Kid</strong> templates
through the WebKit application server. You can browse through the
<a href="${servlet.request().uriWebKitRoot() + 'KidKit/Docs/UsersGuide.html'}">KidKit
docs</a> here.</p>

<p>You are currently using Kid version
<strong py:content="kid.__version__">(version)</strong>.
See the <a href="http://kid.lesscode.org">Kid homepage</a>
for more information about Kid templates.</p>

<h4 style="text-align:center">Here are some examples.</h4>

<?python from KidKit.Properties import WebKitConfig
files = WebKitConfig['examplePages'] ?>

<table cellspacing="2" cellpadding="2" style="margin-left:auto;margin-right:auto">
<tr py:for="i, file in enumerate(files)" style="background-color:#f${i%2 and 'd' or 'e'}9">
<td><a href="$file" py:content="file">the file name will be inserted here</a>
<span py:if="file=='Welcome'">(this page)</span></td>
<td><a style="font-size:smaller" href="View?filename=${file}.kid">(source)</a></td>
</tr>
</table>

</body>
