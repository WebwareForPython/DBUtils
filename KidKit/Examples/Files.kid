<?xml version='1.0' encoding='utf-8'?>
<?python from KidKit.Examples.KidExamplePage import KidExamplePage
hook = KidExamplePage.writeContent ?>
<body py:strip="" xmlns:py="http://purl.org/kid/ns#">
<?python import os
curdir = os.path.dirname(servlet.request().serverSidePath()) ?>
<h3>Index of <span py:replace="curdir" /></h3>
<ul style="list-style-type:none">
<li py:for="f in os.listdir(curdir)"><a href="$f" py:content="f" /></li>
</ul>
</body>
