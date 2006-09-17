#
# AjaxPage.py
#
# Written by John Dickinson based on ideas from
# Apple Developer Connection and DivMod Nevow.
# Some changes by Robert Forkel and Christoph Zwerschke.
#

import StringIO, traceback, time, random

from ExamplePage import ExamplePage as BaseClass

try:
	bool
except NameError: # Fallback for Python < 2.3
	bool = lambda x: x and 1 or 0

try:
	object
except NameError: # Fallback for Python < 2.2
	class object: pass
	std_isinstance = isinstance
	def isinstance(obj, cinf):
		if type(cinf) == type(()):
			for ci in cinf:
				if type(obj) == type(object):
					if std_isinstance(obj, ci):
						return 1
				else:
					if type(obj) == type(ci):
						return 1
			return 0
		else:
			return std_isinstance(obj, cinf)


def quoteJs(what):
	"""Return quoted JavaScript string corresponding to the Python object."""
	if isinstance(what, bool):
		ret = str(what).lower()
	elif isinstance(what, (int, long, float, PyJs)):
		ret = str(what)
	else:
		ret = "'%s'" % str(what).replace('\\', '\\\\').replace('\'', '\\\'').replace('\n', '\\n')
	return ret


class PyJs(object):
	"""This class simply tanslates a Python expression into a JavaScript string."""

	def __init__(self, name):
		self.__name = name

	def __getattr__(self, aname):
		return self.__class__('%s.%s' % (self, aname))

	def __str__(self):
		return self.__name

	def __call__(self, *a, **kw):
		args = ','.join([quoteJs(i) for i in a])
		kw_args = ','.join(['%s=%s' % (k, quoteJs(v)) for k, v in kw.items()])
		if args and kw_args:
			all_args = '%s,%s' % (args, kw_args)
		elif not kw_args:
			all_args = args
		elif not args:
			all_args = kw_args
		return self.__class__('%s(%s)' % (self, all_args))

	def __getitem__(self, index):
		return self.__class__('%s[%s]' % (self, quoteJs(index)))

	def __repr__(self):
		return self.__str__()


class AjaxPage(BaseClass):
	"""A superclass for Webware servlets using Ajax techniques.

	AjaxPage can be used to make coding XMLHttpRequest() applications easier.

	Subclasses should override the method ajax_methods() which returns a list
	of method names. These method names refer to Webware Servlet methods that
	are able to be called by an Ajax-enabled web page. This is very similar
	in functionality to Webware's actions.

	A polling mechanism can be used for long running requests (e.g. generating
	reports) or if you want to send commands to the client without the client
	first triggering an event (e.g. for a chat application). In the first case,
	you should also specify a timeout after which polling shall be used.

	"""

	# Class level variables that can be overridden by servlet instances:
	debug = 0 # set to True if you want to see debugging output
	clientPolling = 1 # set to True if you want to use the polling mechanism
	responseTimeout = 90 # timeout of client waiting for a response in seconds

	# Class level variables to help make client code simpler:
	window, document, alert, this = map(PyJs,
		'window document alert this'.split())
	setTag, setClass, setID, setValue, setReadonly = map(PyJs,
		'setTag setClass setID setValue setReadonly'.split())
	call, call_form = map(PyJs, ('ajax_call', 'ajax_call_form'))

	# Response Queue for timed out queries:
	_responseQueue = {}

	def writeJavaScript(self):
		BaseClass.writeJavaScript(self)
		s = '<script type="text/javascript" src="ajax%s.js"></script>'
		self.writeln(s % 'call')
		if self.clientPolling:
			self.writeln(s % 'poll')

	def actions(self):
		a = BaseClass.actions(self)
		a.append('ajax_call')
		if self.clientPolling:
			a.append('ajax_poll')
		return a

	def ajax_methods(self):
		return []

	def ajax_clientPollingInterval(self):
		"""Set the interval for the client polling.

		You should always make it a little random to avoid synchronization.

		"""
		return random.choice(range(3, 8))

	def ajax_call(self):
		"""Execute method with arguments on the server side.

		The method name is passed in the field _call_,
		the unique request number in the field _req_
		and the arguments in the field _ (single underscore).

		Returns Javascript function to be executed by the client immediately.

		"""
		req = self.request()
		if req.hasField('_call_'):
			call = req.field('_call_')
			args = req.field('_', [])
			if type(args) != type([]):
				args = [args]
			if self.clientPolling and self.responseTimeout:
				start_time = time.time()
			if call in self.ajax_methods():
				try:
					method = getattr(self, call)
				except AttributeError:
					cmd = self.alert('%s, although an approved method,'
						' was not found' % call)
				else:
					try:
						if self.debug:
							self.log("Ajax call %s(%s)" % (call, args))
						cmd = str(method(*args))
					except Exception:
						err = StringIO.StringIO()
						traceback.print_exc(file=err)
						e = err.getvalue()
						cmd = self.alert('%s was called,'
							' but encountered an error: %s' % (call, e))
						err.close()
			else:
				cmd = self.alert('%s is not an approved method' % call)
		else:
			cmd = self.alert('Ajax call missing call parameter.')
		if self.clientPolling and self.responseTimeout:
			in_time = time.time() - start_time < self.responseTimeout
		else:
			in_time = 1
		if in_time:
			# If the computation of the method did not last very long,
			# deliver it immediately back to the client with this response:
			if self.debug:
				self.log("Ajax returns immediately: " + str(cmd))
			self.write(cmd)
		else:
			# If the client request might have already timed out,
			# put the result in the queue and let client poll it:
			if self.debug:
				self.log("Ajax puts in queue: " + str(cmd))
			sid = self.session().identifier()
			self._responseQueue.setdefault(sid, []).append(cmd)

	def ajax_poll(self):
		"""Return queued Javascript functions to be executed on the client side.

		This is polled by the client in random intervals in order to get
		results from long-running queries or push content to the client.

		"""
		if self.clientPolling:
			sid = self.session().identifier()
			# Set the timeout until the next time this method is called
			# by the client, using the Javascript wait variable:
			cmd = ['wait=%s' % self.ajax_clientPollingInterval()]
			if self._responseQueue.has_key(sid): # add in other commands
				cmd.extend(map(str, self._responseQueue[sid]))
				self._responseQueue[sid] = []
			cmd = ';'.join(cmd) + ';'
			if self.debug:
				self.log("Ajax returns from queue: " + cmd)
		else:
			if self.debug:
				self.log("Ajax tells the client to stop polling.")
			cmd = 'dying = true;'
		self.write(cmd) # write out at least the wait variable

	def ajax_push(self, cmd):
		"""Push Javascript commands to be executed on the client side.

		Client polling must be activitated if you want to use this.

		"""
		if self.clientPolling:
			if self.debug:
				self.log("Ajax pushes in queue: " + cmd)
			sid = self.session().identifier()
			self._responseQueue.setdefault(sid, []).append(cmd)

	def preAction(self, action_name):
		if action_name.startswith('ajax_'):
			pass
		else:
			BaseClass.preAction(self, action_name)

	def postAction(self, action_name):
		if action_name.startswith('ajax_'):
			pass
		else:
			BaseClass.postAction(self,action_name)
