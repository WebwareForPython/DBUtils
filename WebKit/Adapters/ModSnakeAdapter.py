"""
WebWare adapter for mod_snake.
-  Gifted to the WebWare project by Jon Travis (jtravis@covalent.net)

Usage:

Add the following lines to your httpd.conf file:
-- Snip here --
SnakeModuleDir   /path/to/Webware
SnakeModuleDir   /path/to/Webware/WebKit
SnakeModule      ModSnakeAdapter.ModSnakeAdapter
WebwareAddress   /path/to/Webware/WebKit/adapter.address
AddHandler       webware .psp

<Location /wpy>
SetHandler webware
</Location>
-- Snip here --

Using the above configuration will tag all .psp files for processing
by the webware handler.  All files in the /wpy location will also be
given the same handler.

To change the chunk size that the mod_snake adaptor uses for reading
and writing data, simply add the directive:

WebwareChunkSize  69

(or whatever your new chunksize is)
"""

import mod_snake
import time
import os
from marshal import dumps, loads
from socket  import *
try:
	from cStringIO import StringIO
except:
	from StringIO import StringIO

# Keys into the server-config dictionary
PER_SVR_SERVER    = 0      # server_rec
PER_SVR_PORT      = 1      # Port from webware address file
PER_SVR_ADDRESS   = 2      # Address from webware address file
PER_SVR_CHUNKSIZE = 3      # Size of chunks to read and write

DEFAULT_CHUNKSIZE = 32 * 1024

from WebKit.Adapters.Adapter import Adapter

class ModSnakeAdapter(Adapter):
	def __init__(self, module):
		hooks = {
			'create_svr_config' : self.create_svr_config,
			'content_handler': self.content_handler,
			}

		for hook in hooks.keys():
			module.add_hook(hook, hooks[hook])

		directives = {
			'WebwareAddress' : (mod_snake.RSRC_CONF,mod_snake.TAKE1,
				self.cmd_WebwareAddress),
			'WebwareChunkSize': (mod_snake.RSRC_CONF,mod_snake.TAKE1,
				self.cmd_WebwareChunkSize)
			}

		module.add_directives(directives)

		Adapter.__init__(self, '')

	def create_svr_config(self, server):
		return {
			PER_SVR_SERVER: server,
			PER_SVR_PORT: '8086',
			PER_SVR_ADDRESS: 'localhost',
			PER_SVR_CHUNKSIZE: DEFAULT_CHUNKSIZE,
			}

	def cmd_WebwareChunkSize(self, per_dir, per_svr, chunksize):
		chunksize = int(chunksize)
		if chunksize <= 0:
			return "chunksize must be > 0"

		per_svr[PER_SVR_CHUNKSIZE] = int(chunksize)

	def cmd_WebwareAddress(self, per_dir, per_svr, file):
		(host, port) = open(file).read().split(':')
		per_svr[PER_SVR_PORT]    = int(port)
		per_svr[PER_SVR_ADDRESS] = host
		self._webKitDir = os.path.dirname(file)

	def content_handler(self, per_dir, per_svr, request):
		if request.handler != 'webware':
			return mod_snake.DECLINED

		res = request.setup_client_block(mod_snake.REQUEST_CHUNKED_ERROR)
		if res:
			raise "Failed to setup client blocking method"

		request.should_client_block()
		strdata = StringIO()

		while 1:
			data, err = request.get_client_block(per_svr[PER_SVR_CHUNKSIZE])
			if err <= 0:
				break

			strdata.write(data)


		# Setup the subprocess environment, because os.environ suxx0r3z
		request.add_common_vars()
		request.add_cgi_vars()

		env = {}
		for key, val in request.subprocess_env.items():
			env[key] = val

		env["GATEWAY_INTERFACE"] = mod_snake.get_version()

		response = self.transactWithAppServer(env, strdata.getvalue(), \
			per_svr[PER_SVR_ADDRESS], per_svr[PER_SVR_PORT])

		self.respond( request, response)

		return mod_snake.OK

	def respond(self, req, respdict):
		headerend = respdict.find("\n\n")
		headers = respdict[:headerend]
		for header in headers.split("\n"):
			header = header.split(":")
			req.headers_out[header[0]] = ":".join(header[1:])
			if header[0].lower() == 'content-type':
				req.content_type = header[1]
			if header[0].lower() == 'status':
				req.status = int(header[1].lstrip().split(' ', 1)[0])
		req.send_http_header()
		req.rwrite(respdict[headerend+2:])
