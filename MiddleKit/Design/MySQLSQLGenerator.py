from SQLGenerator import SQLGenerator

try: # for Python < 2.3
	True, False
except NameError:
	True, False = 1, 0


class MySQLSQLGenerator(SQLGenerator):

	def sqlSupportsDefaultValues(self):
		return True


class Klasses:

	def dropDatabaseSQL(self, dbName):
		return 'drop database if exists %s;\n' % dbName

	def dropTablesSQL(self):
		sql = []
		names = self.auxiliaryTableNames()[:]
		names.reverse()
		for tableName in names:
			sql.append('drop table if exists %s;\n' % tableName)
		klasses = self._model._allKlassesInOrder[:]
		klasses.reverse()
		for klass in klasses:
			sql.append('drop table if exists %s;\n' % klass.name())
		sql.append('\n')
		return ''.join(sql)

	def createDatabaseSQL(self, dbName):
		return 'create database %s;\n' % dbName

	def useDatabaseSQL(self, dbName):
		return 'use %s;\n\n' % dbName

	def listTablesSQL(self):
		return 'show tables\n\n'


class Klass:

	def writePostCreateTable(self, generator, out):
		start = self.setting('StartingSerialNum', None)
		if start:
			out.write('alter table %s auto_increment=%s;\n' % (self.sqlTableName(), start))

	def primaryKeySQLDef(self, generator):
		return '    %s int not null primary key auto_increment,\n' % self.sqlSerialColumnName().ljust(self.maxNameWidth())

	def writeIndexSQLDefsInTable(self, wr):
		for attr in self.allAttrs():
			if attr.boolForKey('isIndexed') and attr.hasSQLColumn():
				wr(',\n')
				wr('\tindex (%s)' % attr.sqlName())
		wr('\n')


class EnumAttr:

	def nativeEnumSQLType(self):
		enums = ['"%s"' % enum for enum in self.enums()]
		enums = ', '.join(enums)
		enums = 'enum(%s)' % enums
		return enums


class StringAttr:

	def sqlType(self):
		# @@ 2000-11-11 ce: cache this
		if not self.get('Max', None):
			return 'varchar(100) /* WARNING: NO LENGTH SPECIFIED */'
		max = int(self['Max']) # @@ 2000-11-12 ce: won't need int() after using types
		if max > 65535:
			return 'longtext'
		if max > 255:
			return 'text'
		if self.has_key('Min') and self['Min'] and int(self['Min']) == max:
			return 'char(%s)' % max
		else:
			return 'varchar(%s)' % max


class ObjRefAttr:

	def sqlType(self):
		if self.setting('UseBigIntObjRefColumns', False):
			return 'bigint unsigned /* %s */' % self['Type']
		else:
			return 'int unsigned'
