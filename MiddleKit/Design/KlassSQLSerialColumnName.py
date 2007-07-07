class KlassMixIn:

	def sqlSerialColumnName(self):
		name = getattr(self, '_sqlIdColumnName', None)
		if name is None:
			_ClassName = self.name()
			ClassName = _ClassName[0].upper() + _ClassName[1:]
			className = _ClassName[0].lower() + _ClassName[1:]
			names = locals()
			name = self.klasses().model().setting('SQLSerialColumnName', 'serialNum') % names
			self._sqlIdColumnName = name
		return name


from MiscUtils.MixIn import MixIn
from MiddleKit.Core.Klass import Klass
MixIn(Klass, KlassMixIn)
