"""
HTTPStatusCodes.py


TO DO

	@@ document
	@@ 2000-04-17 ce: Is there an RFC for this?


DONE

	* 2000-05-08 ce: Incorporated Matt Schinkel's (matt@null.net) re.sub()
	  for stripping HTML tags in the ASCII version of the HTTP msg.

"""


import re


HTTPStatusCodeList = [
	(100, 'CONTINUE',                        'The client can continue.'),
	(101, 'SWITCHING_PROTOCOLS',             'The server is switching protocols according to Upgrade header.'),
	(200, 'OK',                              'The request succeeded normally.'),
	(201, 'CREATED',                         'The request succeeded and created a new resource on the server.'),
	(202, 'ACCEPTED',                        'The request was accepted for processing, but was not completed.'),
	(203, 'NON_AUTHORITATIVE_INFORMATION',   'The meta information presented by the client did not originate from the server.'),
	(204, 'NO_CONTENT',                      'The request succeeded but that there was no new information to return.'),
	(205, 'RESET_CONTENT',                   'The agent <em>SHOULD</em> reset the document view which caused the request to be sent.'),
	(206, 'PARTIAL_CONTENT',                 'The server has fulfilled the partial GET request for the resource.'),
	(300, 'MULTIPLE_CHOICES',                'The requested resource corresponds to any one of a set of representations, each with its own specific location.'),
	(301, 'MOVED_PERMANENTLY',               'The resource has permanently moved to a new location, and that future references should use a new URI with their requests.'),
	(302, 'MOVED_TEMPORARILY',               'The resource has temporarily moved to another location, but that future references should still use the original URI to access the resource.'),
	(303, 'SEE_OTHER',                       'The response to the request can be found under a different URI.'),
	(304, 'NOT_MODIFIED',                    'A conditional GET operation found that the resource was available and not modified.'),
	(305, 'USE_PROXY',                       'The requested resource <em>MUST</em> be accessed through the proxy given by the <code><em>Location</em></code> field.'),
	(400, 'BAD_REQUEST',                     'The request sent by the client was syntactically incorrect.'),
	(401, 'UNAUTHORIZED',                    'The request requires HTTP authentication.'),
	(402, 'PAYMENT_REQUIRED',                'Reserved for future use.'),
	(403, 'FORBIDDEN',                       'The server understood the request but refused to fulfill it.'),
	(404, 'NOT_FOUND',                       'The requested resource is not available.'),
	(405, 'METHOD_NOT_ALLOWED',              'The method specified in the <code><em>Request-Line</em></code> is not allowed for the resource identified by the <code><em>Request-URI</em></code>.'),
	(406, 'NOT_ACCEPTABLE',                  'The resource identified by the request is only capable of generating response entities which have content characteristics not acceptable according to the accept headers sent in the request.'),
	(407, 'PROXY_AUTHENTICATION_REQUIRED',   'The client <em>MUST</em> first authenticate itself with the proxy.'),
	(408, 'REQUEST_TIMEOUT',                 'The client did not produce a request within the time that the server was prepared to wait.'),
	(409, 'CONFLICT',                        'The request could not be completed due to a conflict with the current state of the resource.'),
	(410, 'GONE',                            'The resource is no longer available at the server and no forwarding address is known.'),
	(411, 'LENGTH_REQUIRED',                 'The request cannot be handled without a defined <code><em>Content-Length</em></code>.'),
	(412, 'PRECONDITION_FAILED',             'The precondition given in one or more of the request-header fields evaluated to false when it was tested on the server.'),
	(413, 'REQUEST_ENTITY_TOO_LARGE',        'The server is refusing to process the request because the request entity is larger than the server is willing or able to process.'),
	(414, 'REQUEST_URI_TOO_LONG',            'The server is refusing to service the request because the <code><em>Request-URI</em></code> is longer than the server is willing to interpret.'),
	(415, 'UNSUPPORTED_MEDIA_TYPE',          'The server is refusing to service the request because the entity of the request is in a format not supported by the requested resource for the requested method.'),
	(416, 'REQUESTED_RANGE_NOT_SATISFIABLE', 'The server cannot serve the requested byte range.'),
	(417, 'EXPECTATION_FAILED',              'The server could not meet the expectation given in the Expect request header.'),
	(500, 'INTERNAL_SERVER_ERROR',           'An error inside the HTTP server which prevented it from fulfilling the request.'),
	(501, 'NOT_IMPLEMENTED',                 'The HTTP server does not support the functionality needed to fulfill the request.'),
	(502, 'BAD_GATEWAY',                     'The HTTP server received an invalid response from a server it consulted when acting as a proxy or gateway.'),
	(503, 'SERVICE_UNAVAILABLE',             'The HTTP server is temporarily overloaded, and unable to handle the request.'),
	(504, 'GATEWAY_TIMEOUT',                 'The server did not receive a timely response from the upstream server while acting as a gateway or proxy.'),
	(505, 'HTTP_VERSION_NOT_SUPPORTED',      'The server does not support or refuses to support the HTTP protocol version that was used in the request message.')
]

HTTPStatusCodeListColumnNames = ('Code', 'Identifier', 'Description')


HTTPStatusCodes = {}
# HTTPStatusCodes can be indexed by either their status code number
# of textual identifier. The result is a dictionary with keys code,
# identifier, asciiMessage and htmlMessage.


# Construct HTTPStatusCodes dictionary
for record in HTTPStatusCodeList:
	code, identifier, htmlMsg = record
	dict = {
		'code':       code,
		'identifier': identifier,
		'htmlMsg':    htmlMsg
	}
	dict['asciiMsg'] = re.sub('<.*?>', '', htmlMsg)

	HTTPStatusCodes[code] = dict
	HTTPStatusCodes[identifier] = dict


def HTMLTableOfHTTPStatusCodes(codes=HTTPStatusCodeList, tableArgs='align=center border=2', rowArgs='valign=top', colArgs='', headingTag='th', headingArgs=''):
	""" Returns an HTML string containing all the status code information as provided by this module. It's highly recommended that if pass arguments to this function, that you do so by keyword. FUTURE: Allow font specs. """
	res = ['<table %s>\n' % tableArgs]
	th = '<%s %s>' % (headingTag, headingArgs)
	res.append('<tr> %s Code </th>  %s Identifier </th>  %s Description </th> </tr>\n' % (th, th, th))
	for code, identifier, htmlMsg in HTTPStatusCodeList:
		td = '<td %s>' % colArgs
		res.append('<tr %s> %s %s </td>  %s %s </td>  %s %s </td> </tr>\n' % (rowArgs, td, code, td, identifier, td, htmlMsg))
	res.append('</table>\n')
	return ''.join(res)


if __name__ == '__main__':
	print '''<html>
<head>
	<title>HTTP Status Codes</title>
</head>
<body>'''
	print HTMLTableOfHTTPStatusCodes()
	print '''</body>
</html>'''
