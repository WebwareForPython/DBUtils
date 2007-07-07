<?xml version='1.0' encoding='utf-8'?>
<?python
import time
title = "A Kid Template"
?>
<html xmlns="http://www.w3.org/1999/xhtml"
	xmlns:py="http://purl.org/kid/ns#">
<head>
	<title py:content="title">
		This is replaced with the value of the title variable.
	</title>
	</head>
	<body style="color:black;background-color:white">
		<div style="font-family:sans-serif;text-align:center">
			<h2>
				Time Example 2
			</h2>
			<p>
				<i>
					This page is a stand-alone page.
				</i>
			</p>
			<p>
				The current time is ${time.strftime('%C %c')}.
			</p>
		</div>
	</body>
</html>