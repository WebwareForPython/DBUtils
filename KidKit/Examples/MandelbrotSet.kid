<?xml version='1.0' encoding='utf-8'?>
<?python
title = "The Mandelbrot Set"
def color(x,y):
    z = c = complex(x, -y)/100.0
    for n in range(16):
        z = z*z + c
        if abs(z) > 2:
            break
    return "#%x82040" % n
?>
<html xmlns="http://www.w3.org/1999/xhtml"
  xmlns:py="http://purl.org/kid/ns#">
<head>
    <title py:content="title" />
</head>
<body bgcolor="black" text="white">
<table width="100%" height="100%">
    <tr>
        <td align="center" valign="center">
            <h1 py:content="title" />
            <table cellspacing="1" cellpadding="2">
                <tr py:for="y  in range(-150, 150, 5)">
                    <td py:for="x in range(-250, 100, 5)" bgcolor="${color(x,y)}" />
                </tr>
            </table>
        </td>
    </tr>
</table>
</body>
</html>
