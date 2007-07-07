<?xml version='1.0' encoding='utf-8'?>
<?python
from KidKit.Examples.KidExamplePage import KidExamplePage
hook = KidExamplePage.writeContent
import time
?>
<div style="text-align:center"
    xmlns:py="http://purl.org/kid/ns#">
<h2>Time Example 1</h2>
<p><i>This page is embedded as a KidExamplePage.</i></p>
<p>The current time is
<span py:content="time.strftime('%C %c')" style="color:#339">
Locale Specific Date/Time
</span>.</p>
</div>
