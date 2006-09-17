from BasicTypeAttr import BasicTypeAttr


class IntAttr(BasicTypeAttr):

	def __init__(self, dict):
		BasicTypeAttr.__init__(self, dict)
		if self.get('Max') is not None:
			self['Max'] = int(self['Max'])
		if self.get('Min') is not None:
			self['Min'] = int(self['Min'])
