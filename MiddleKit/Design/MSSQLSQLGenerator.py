import os, sys
from time import asctime, localtime, time
from SQLGenerator import SQLGenerator

try: # for Python < 2.3
	True, False
except NameError:
	True, False = 1, 0


def cleanConstraintName(name):
	assert name
	name = name.replace('[', '')
	name = name.replace(']', '')
	assert '[' not in name, name
	assert ',' not in name, name
	if len(name) > 128:
		raise Exception("name is %i chars long, but MS SQL Server only"
			" supports 128. this case is no currently handled. name=%r"
			% (len(name), name))
	return name


class MSSQLSQLGenerator(SQLGenerator):

	def sqlSupportsDefaultValues(self):
		return True # I think it does but I do not know how it is implemented


class Model:

	def writeSQL(self, generator, dirname):
		if not os.path.exists(dirname):
			os.mkdir(dirname)
		assert os.path.isdir(dirname)
		self._klasses.setSQLGenerator(generator)
		self._klasses.writeSQL(generator, os.path.join(dirname, 'Create.sql'))

	def writePostKlassSamplesSQL(self, generator, file):
		file.write('go\n')


class Klasses:

	def dropDatabaseSQL(self, dbName):
		'''
		Rather than drop the database, I prefer to drop just the tables.
		The reason is that the database in MSSQL can contain users and diagrams that would then need to be re-added or re-created
		Its better to drop the tables than delete them because if you delete the data, the identities need to be reset.
		What is even worse is that identity resets behave differently depending on whether data has existed in them at any given point.
		Its safer to drop the table.  dr 4-11-2001
		'''
		strList = []
#		strList.append('use %s\ngo\n' % dbName)
		strList.append('use Master\ngo\n')
		strList.append("if exists("
			"select * from master.dbo.sysdatabases where name = N'%s'"
			") drop database %s;\ngo \n" % (dbName, dbName))

		if 0:
			self._klasses.reverse()
			for klass in self._klasses:
			# If table exists drop.
				strList.append("print 'Dropping table %s'\n" % klass.name())
				strList.append("if exists (select * from dbo.sysobjects"
					" where id = object_id(N'[dbo].[%s]')"
					" and OBJECTPROPERTY(id, N'IsUserTable') = 1)\n"
					% klass.name())
				strList.append('drop table [dbo].%s\n' % klass.sqlTableName())
				strList.append('go\n\n')
			self._klasses.reverse()

		return ''.join(strList)

	def dropTablesSQL(self):
		strList = []
		self._klasses.reverse()
		for klass in self._klasses:
		# If table exists drop.
			strList.append("print 'Dropping table %s'\n" % klass.name())
			strList.append("if exists (select * from dbo.sysobjects"
				" where id = object_id(N'[dbo].[%s]')"
				" and OBJECTPROPERTY(id, N'IsUserTable') = 1)\n"
				% klass.name())
			strList.append('drop table [dbo].%s\n' % klass.sqlTableName())
			strList.append('go\n\n')
		self._klasses.reverse()
		return ''.join(strList)


	def createDatabaseSQL(self, dbName):
		'''
		Creates the database only if it does not already exist
		'''
		return ('Use Master\n' + 'go\n\n' + "if not exists("
			"select * from master.dbo.sysdatabases where name = N'%s'"
			") create database %s;\ngo \n" % (dbName, dbName))

	def useDatabaseSQL(self, dbName):
		return 'USE %s;\n\n' % dbName

	def sqlGenerator(self):
		return generator

	def setSQLGenerator(self, generator):
		self._sqlGenerator = generator

	def writeClassIdsSQL(self, generator, out):
		wr = out.write
		wr('''\

if exists (select * from dbo.sysobjects where id = object_id(N'[dbo].[_MKClassIds]') and OBJECTPROPERTY(id, N'IsUserTable') = 1)
drop table [dbo].[_MKClassIds]
go

create table _MKClassIds (
	id int not null primary key,
	name varchar(100)
)\ngo
''')
		wr('delete from _MKClassIds\n\n')
		for klass in self._klasses:
			wr('insert into _MKClassIds (id, name) values ')
			wr("(%s, '%s');\n" % (klass.id(), klass.name()))
		wr('\ngo\n\n')


	def writeKeyValue(self, out, key, value):
		''' Used by willWriteSQL(). '''
		key = key.ljust(12)
		out.write('# %s = %s\n' % (key, value))

	def willWriteSQL(self, generator, out):
		wr = out.write
		kv = self.writeKeyValue
		wr('/*\nStart of generated SQL.\n\n')
		kv(out, 'Date', asctime(localtime(time())))
		kv(out, 'Python ver', sys.version)
		kv(out, 'Op Sys', os.name)
		kv(out, 'Platform', sys.platform)
		kv(out, 'Cur dir', os.getcwd())
		kv(out, 'Num classes', len(self._klasses))
		wr('\nClasses:\n')
		for klass in self._klasses:
			wr('\t%s\n' % klass.name())
		wr('*/\n\n')

		sql = generator.setting('PreSQL', None)
		if sql:
			wr('/* PreSQL start */\n' + sql + '\n/* PreSQL end */\n\n')

		# If database doesn't exist create it.
		dbName = generator.dbName()
		# wr('Use %s\ngo\n\n' % dbName)\

		rList = self._klasses[:]
		rList.reverse()
		# print str(type(rList))
		# for klass in rList:
		#     # If table exists, then drop it.
		#     wr("if exists (select * from dbo.sysobjects"
		#         " where id = object_id(N'[dbo].[%s]')"
		#         " and OBJECTPROPERTY(id, N'IsUserTable') = 1)\n"
		#         % klass.name())
		# wr('drop table [dbo].[%s]\n' % klass.name())
		# wr('go\n\n')


class Klass:

	def primaryKeySQLDef(self, generator):
		'''
		Returns a one liner that becomes part of the CREATE statement for creating the primary key of the table. SQL generators often override this mix-in method to customize the creation of the primary key for their SQL variant. This method should use self.sqlIdName() and often ljust()s it by self.maxNameWidth().
		'''
		constraintName = cleanConstraintName('PK__%s__%s'
			% (self.sqlTableName(), self.sqlSerialColumnName()))
		return '	%s int constraint [%s] primary key not null identity(1, 1),\n' % (
			self.sqlSerialColumnName().ljust(self.maxNameWidth()), constraintName)

	def sqlTableName(self):
		"""
		Returns "[name]" so that table names do not conflict with SQL
		reserved words.
		"""
		return '[%s]' % self.name()

	def writeIndexSQLDefsAfterTable(self, wr):
		for attr in self.allAttrs():
			if attr.boolForKey('isIndexed') and attr.hasSQLColumn():
				unique = self.boolForKey('isUnique') and ' unique' or ''
				indexName = cleanConstraintName('IX__%s__%s' % (self.name(), attr.name()))
				wr('create%s index [%s] on %s(%s);\n' % (
					unique, indexName, self.sqlTableName(), attr.sqlColumnName()))
			elif attr.boolForKey('isBackRefAttr') and not attr.boolForKey('isDerived'):
				# this index will speed up the fetching of lists
				if self.setting('UseBigIntObjRefColumns', False):
					# not bothering supporting the old obj ref approach
					pass
				else:
					attrName = attr.name()
					classIdName, objIdName = attr.sqlName().split(',')
					tableName = self.sqlTableName()
					indexName = 'IX__%(tableName)s__BackRef__%(attrName)s' % locals()
					indexName = cleanConstraintName(indexName)
					wr('create index [%(indexName)s] on '
						'%(tableName)s(%(classIdName)s, %(objIdName)s);\n' % locals())
		wr('\n')


class Attr:

	def sqlNullSpec(self):
		return ' null'

	def maxNameWidth(self):
		return 30  # @@ 2000-09-14 ce: should compute that from names rather than hard code

	def sqlType(self):
		return self['Type']
		# @@ 2000-10-18 ce: reenable this when other types are implemented
		raise AbstractError, self.__class__

	def sqlName(self):
		return '[' + self.name() + ']'

	def sqlColumnName(self):
		""" Returns the SQL column name corresponding to this attribute, consisting of self.name() + self.sqlTypeSuffix(). """
		if not hasattr(self, '_sqlColumnName'):
			self._sqlColumnName = self.name() # + self.sqlTypeSuffix()
		return '[' + self._sqlColumnName + ']'

	def uniqueSQL(self):
		"""
		Returns the SQL to use within a column definition to make it unique.
		"""
		if not self.boolForKey('isUnique'):
			return ''
		return ' constraint [UQ__%s__%s] unique' % (
			self.klass().name(), self.name())


class DateTimeAttr:

	def sqlType(self):
		return 'DateTime'


class DateAttr:

	def sqlType(self):
		return 'DateTime'


class TimeAttr:

	def sqlType(self):
		return 'DateTime'


class BoolAttr:

	def sqlType(self):
		# @@
		return 'bit'


class EnumAttr:

	def sqlType(self):
		if self.usesExternalSQLEnums():
			tableName, valueColName, nameColName = self.externalEnumsSQLNames()
			constraintName = cleanConstraintName('FK__%s__%s__%s__%s'
				% (self.containingKlass.sqlTableName(), self.sqlName(),
					tableName, valueColName))
			return 'int constraint [%s] references %s(%s)' % (
				constraintName, tableName, valueColName)
		else:
			return self.nativeEnumSQLType()


class LongAttr:

	def sqlType(self):
		# @@ 2000-10-18 ce: is this ANSI SQL?
		return 'bigint'


class StringAttr:

	def sqlType(self):
		if not self['Max']:
			return 'varchar(100) /* WARNING: NO LENGTH SPECIFIED */'
		elif self['Min'] == self['Max']:
			return 'char(%s)' % self['Max']
		else:
			max = int(self['Max'])
			if int(self['Max']) > 8000:
				return 'text'
			else:
				ref = self.get('Ref', '')
				if not ref:
					ref = '' # for some reason ref was none instead of ''
				else:
					ref = ' ' + ref
				return 'varchar(%s)%s' % (int(self['Max']), ref)

	def sqlForNonNoneSampleInput(self, input):
		value = input
		if value == "''":
			value = ''
		elif value.find('\\') != -1:
			if 1:
				# add spaces before and after, to prevent
				# syntax error if value begins or ends with "
				value = eval('""" ' + str(value) + ' """')
				value = repr(value[1:-1])	# trim off the spaces
				value = value.replace('\\011', '\\t')
				value = value.replace('\\012', '\\n')
				value = value.replace("\\'", "''")
				return value
		value = repr(value)
		value = value.replace("\\'", "''")
		# print '>> value:', value
		return value


class ObjRefAttr:

	refVarCount = 1

	def sqlType(self):
		if self.setting('UseBigIntObjRefColumns', False):
			if self.get('Ref', None):
				return ('bigint constraint %s foreign key'
					' references %(Type)s(%(Type)sId) ' % self)
			else:
				return 'bigint /* relates to %s */ ' % self['Type']
		else:
			return 'int'

	def classIdReferences(self):
		classIdName = self.sqlName().split(',')[0]
		constraintName = cleanConstraintName('FK__%s__%s___MKClassIds__id'
			% (self.containingKlass.sqlTableName(), classIdName))
		return ' constraint [%s] references _MKClassIds' % constraintName

	def objIdReferences(self):
		targetKlass = self.targetKlass()
		objIdName = self.sqlName().split(',')[1]
		constraintName = 'FK__%s__%s__%s__%s' % (
			self.containingKlass.sqlTableName(), objIdName,
			targetKlass.sqlTableName(), targetKlass.sqlSerialColumnName())
		constraintName = cleanConstraintName(constraintName)
		return ' constraint [%s] references %s(%s) ' % (constraintName,
			targetKlass.sqlTableName(), targetKlass.sqlSerialColumnName())

	def sqlForNonNoneSampleInput(self, input):
		sql = ObjRefAttr.mixInSuperSqlForNonNoneSampleInput(self, input)
		if sql.find('(select') != -1:
			# MS SQL 2000 does not allow a subselect where an INSERT value is expected.
			# It will complain:
			# "Subqueries are not allowed in this context. Only scalar expressions are allowed."
			# So we pass back some "pre-statements" to set up the scalar in a temp variable.
			classId, objId = sql.split(',', 1)  # objId is the '(select...' part
			refVarName = str('@ref_%03i_%s'
				% (ObjRefAttr.refVarCount, self.targetKlass().name()))
			ObjRefAttr.refVarCount += 1
			preSql = str('declare %s as int; set %s = %s;\n' % (
				refVarName, refVarName, objId))
			sqlForValue = classId + ',' + refVarName
			return (preSql, sqlForValue)
		else:
			return sql


class ListAttr:

	def sqlType(self):
		raise Exception, 'Lists do not have a SQL type.'


class FloatAttr:

	def sqlType(self):
		return 'float'
		# return 'decimal(16,8)'
		# ^ use the decimal type instead

	def sampleValue(self, value):
		float(value) # raises exception if value is invalid
		return value
