
from MiscUtils.Configurable import Configurable
from WebKit.Examples.ExamplePage import ExamplePage


class DBConfig(Configurable):
    """Database configuration."""

    def defaultConfig(self):
        return {
            'dbapi': 'pg',
            'database': 'demo',
            'user': 'demo',
            'password': 'demo',
            'mincached': 5,
            'maxcached': 25
        }

    def configFilename(self):
        return 'Configs/Database.config'


# the database tables used in this example:
tables = ('''seminars (
    id varchar(4) primary key,
    title varchar(64) unique not null,
    cost money,
    places_left smallint)''',
'''attendees (
    name varchar(64) not null,
    seminar varchar(4),
    paid boolean,
    primary key(name, seminar),
    foreign key (seminar) references seminars(id) on delete cascade)''')


class DBUtilsExample(ExamplePage):
    """Example page for the DBUtils package."""

    # Initialize the database class once when this class is loaded:
    config = DBConfig().config()
    if config.get('maxcached', None) is None:
        dbmod_name = 'Persistent'
    else:
        dbmod_name = 'Pooled'
    dbapi_name = config.pop('dbapi', 'pg')
    if dbapi_name == 'pg': # use the PyGreSQL classic DB API
        dbmod_name += 'Pg'
        if config.has_key('database'):
            config['dbname'] = config['database']
            del config['database']
        if config.has_key('password'):
            config['passwd'] = config['password']
            del config['password']
    else: # use a DB-API 2 compliant module
        dbmod_name += 'DB'
    dbapi = dbmod = dbclass = dbstatus = None
    try:
        dbapi = __import__(dbapi_name)
        try:
            dbmod = getattr(__import__('DBUtils.' + dbmod_name), dbmod_name)
            try:
                if dbapi_name != 'pg':
                    config['creator'] = dbapi
                dbclass = getattr(dbmod, dbmod_name)(**config)
            except dbapi.Error, error:
                dbstatus = str(error)
            except Exception:
                dbstatus = 'Could not connect to the database.'
        except Exception:
            dbstatus = 'Could not import DBUtils.%s.' % dbmod_name
    except Exception:
        dbstatus = 'Could not import %s.' % dbapi_name

    # Initialize the buttons
    _actions = []
    _buttons = []
    for action in ('create tables',
            'list seminars', 'list attendees',
            'add seminar', 'add attendee'):
        value = action.capitalize()
        action = action.split()
        action[1] = action[1].capitalize()
        action = ''.join(action)
        _actions.append(action)
        _buttons.append('<input name="_action_%s" '
            'type="submit" value="%s">' % (action, value))
    _buttons = tuple(_buttons)

    def title(self):
        return "DBUtils Example"

    def actions(self):
        return ExamplePage.actions(self) + self._actions

    def awake(self, transaction):
        ExamplePage.awake(self, transaction)
        self._output = []

    def postAction(self, actionName):
        self.writeBody()
        del self._output
        ExamplePage.postAction(self, actionName)

    def output(self, s):
        self._output.append(s)

    def outputMsg(self, msg, error=False):
        self._output.append('<p style="color:%s">%s</p>'
            % (error and 'red' or 'green', msg))

    def connection(self, shareable=True):
        if self.dbstatus:
            error = self.dbstatus
        else:
            try:
                if self.dbmod_name == 'PooledDB':
                    return self.dbclass.connection(shareable)
                else:
                    return self.dbclass.connection()
            except self.dbapi.Error, error:
                error = str(error)
            except Exception:
                error = 'Cannot connect to the database.'
        self.outputMsg(error, True)

    def dedicated_connection(self):
        return self.connection(False)

    def sqlEncode(self, s):
        if s is None:
            return 'null'
        s = s.replace('\\', '\\\\').replace('\'', '\\\'')
        return "'%s'" % s

    def createTables(self):
        db = self.dedicated_connection()
        if not db:
            return
        for table in tables:
            self._output.append('<p>Creating the following table:</p>'
                '<pre>%s</pre>' % table)
            ddl = 'create table ' + table
            try:
                if self.dbapi_name == 'pg':
                    db.query(ddl)
                else:
                    db.cursor().execute(ddl)
                    db.commit()
            except self.dbapi.Error, error:
                if self.dbapi_name != 'pg':
                    db.rollback()
                self.outputMsg(error, True)
            else:
                self.outputMsg('The table was successfully created.')
        db.close()

    def listSeminars(self):
        id = self.request().field('id', None)
        if id:
            if type(id) != type([]):
                id = [id]
            cmd = ','.join(map(self.sqlEncode, id))
            cmd = 'delete from seminars where id in (%s)' % cmd
            db = self.dedicated_connection()
            if not db:
                return
            try:
                if self.dbapi_name == 'pg':
                    db.query('begin')
                    db.query(cmd)
                    db.query('end')
                else:
                    db.cursor().execute(cmd)
                    db.commit()
            except self.dbapi.Error, error:
                try:
                    if self.dbapi_name == 'pg':
                        db.query('end')
                    else:
                        db.rollback()
                except Exception:
                    pass
                self.outputMsg(error, True)
                return
            else:
                self.outputMsg('Entries deleted: %d' % len(id))
        db = self.connection()
        if not db:
            return
        query = ('select id, title, cost, places_left from seminars '
            'order by title')
        try:
            if self.dbapi_name == 'pg':
                result = db.query(query).getresult()
            else:
                cursor = db.cursor()
                cursor.execute(query)
                result = cursor.fetchall()
                cursor.close()
        except self.dbapi.Error, error:
            self.outputMsg(error, True)
            return
        if not result:
            self.outputMsg('There are no seminars in the database.', True)
            return
        wr = self.output
        button = self._buttons[1].replace('List seminars', 'Delete')
        wr('<h4>List of seminars in the database:</h4>')
        wr('<form action=""><table border="1" cellspacing="0" cellpadding="2">'
            '<tr><th>ID</th><th>Seminar title</th><th>Cost</th>'
            '<th>Places left</th><th>%s</th></tr>' % button)
        for id, title, cost, places in result:
            if places is None:
                places = 'unlimited'
            if not cost:
                cost = 'free'
            wr('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>'
                '<input type="checkbox" name="id" value="%s">'
                '</td></tr>' % (id, title, cost, places, id))
        wr('</table></form>')

    def listAttendees(self):
        id = self.request().field('id', None)
        if id:
            if type(id) != type([]):
                id = [id]
            cmds = ['delete from attendees '
                'where rpad(seminar,4)||name in (%s)'
                % ','.join(map(self.sqlEncode, id))]
            places = {}
            for i in id:
                i = i[:4].rstrip()
                if places.has_key(i):
                    places[i] += 1
                else:
                    places[i] = 1
            for i, n in places.items():
                cmds.append("update seminars set places_left=places_left+%d "
                "where id=%s" % (n, self.sqlEncode(i)))
            db = self.dedicated_connection()
            if not db:
                return
            try:
                if self.dbapi_name == 'pg':
                    db.query('begin')
                    for cmd in cmds:
                        db.query(cmd)
                    db.query('end')
                else:
                    for cmd in cmds:
                        db.cursor().execute(cmd)
                    db.commit()
            except self.dbapi.Error, error:
                if self.dbapi_name == 'pg':
                    db.query('end')
                else:
                    db.rollback()
                self.outputMsg(error, True)
                return
            else:
                self.outputMsg('Entries deleted: %d' % len(id))
        db = self.connection()
        if not db:
            return
        query = ('select a.name, s.id, s.title, a.paid '
            ' from attendees a,seminars s'
            ' where s.id=a.seminar'
            ' order by a.name, s.title')
        try:
            if self.dbapi_name == 'pg':
                result = db.query(query).getresult()
            else:
                cursor = db.cursor()
                cursor.execute(query)
                result = cursor.fetchall()
                cursor.close()
        except self.dbapi.Error, error:
            self.outputMsg(error, True)
            return
        if not result:
            self.outputMsg('There are no attendees in the database.', True)
            return
        wr = self.output
        button = self._buttons[2].replace('List attendees', 'Delete')
        wr('<h4>List of attendees in the database:</h4>')
        wr('<form action=""><table border="1" cellspacing="0" cellpadding="2">'
            '<tr><th>Name</th><th>Seminar</th><th>Paid</th>'
            '<th>%s</th></tr>' % button)
        for name, id, title, paid in result:
            paid = paid and 'Yes' or 'No'
            id = id.ljust(4) + name
            wr('<tr><td>%s</td><td>%s</td><td>%s</td>'
                '<td><input type="checkbox" name="id" value="%s"></td>'
                '</tr>' % (name, title, paid, id))
        wr('</table></form>')

    def addSeminar(self):
        wr = self.output
        wr('<h4>Add a seminar entry to the database:</h4>')
        wr('<form action=""><table>'
            '<tr><th>ID</th><td><input name="id" type="text" '
            'size="4" maxlength="4"></td></tr>'
            '<tr><th>Title</th><td><input name="title" type="text" '
            'size="40" maxlength="64"></td></tr>'
            '<tr><th>Cost</th><td><input name="cost" type="text" '
            'size="20" maxlength="20"></td></tr>'
            '<tr><th>Places</th><td><input name="places" type="text" '
            'size="20" maxlength="20"></td></tr>'
            '<tr><td colspan="2" align="right">%s</td></tr>'
            '</table></form>' % self._buttons[3])
        request = self.request()
        if not request.hasField('id'):
            return
        values = []
        for name in ('id', 'title', 'cost', 'places'):
            values.append(request.field(name, '').strip())
        if not values[0] or not values[1]:
            self.outputMsg('You must enter a seminar ID and a title!')
            return
        if not values[2]:
            values[2] = None
        if not values[3]:
            values[3] = None
        db = self.dedicated_connection()
        if not db:
            return
        cmd = ('insert into seminars values (%s,%s,%s,%s)'
            % tuple(map(self.sqlEncode, values)))
        try:
            if self.dbapi_name == 'pg':
                db.query('begin')
                db.query(cmd)
                db.query('end')
            else:
                db.cursor().execute(cmd)
                db.commit()
        except self.dbapi.Error, error:
            if self.dbapi_name == 'pg':
                db.query('end')
            else:
                db.rollback()
            self.outputMsg(error, True)
        else:
            self.outputMsg('"%s" added to seminars.' % values[1])
        db.close()

    def addAttendee(self):
        db = self.connection()
        if not db:
            return
        query = ('select id, title from seminars '
            'where places_left is null or places_left>0 order by title')
        try:
            if self.dbapi_name == 'pg':
                result = db.query(query).getresult()
            else:
                cursor = db.cursor()
                cursor.execute(query)
                result = cursor.fetchall()
                cursor.close()
        except self.dbapi.Error, error:
            self.outputMsg(error, True)
            return
        if not result:
            self.outputMsg('You have to define seminars first.')
            return
        sem = ['<select name="seminar" size="1">']
        for id, title in result:
            sem.append('<option value="%s">%s</option>' % (id, title))
        sem.append('</select>')
        sem = ''.join(sem)
        wr = self.output
        wr('<h4>Add an attendee entry to the database:</h4>')
        wr('<form action=""><table>'
            '<tr><th>Name</th><td><input name="name" type="text" '
            'size="40" maxlength="64"></td></tr>'
            '<tr><th>Seminar</th><td>%s</td></tr>'
            '<tr><th>Paid</th><td>'
            '<input type="radio" name="paid" value="t">Yes '
            '<input type="radio" name="paid" value="f" checked="checked">No'
            '</td></tr><tr><td colspan="2" align="right">%s</td></tr>'
            '</table></form>' % (sem, self._buttons[4]))
        request = self.request()
        if not request.hasField('name'):
            return
        values = []
        for name in ('name', 'seminar', 'paid'):
            values.append(request.field(name, '').strip())
        if not values[0] or not values[1]:
            self.outputMsg('You must enter a name and a seminar!')
            return
        db = self.dedicated_connection()
        if not db:
            return
        try:
            if self.dbapi_name == 'pg':
                db.query('begin')
                cmd = ("update seminars set places_left=places_left-1 "
                    "where id=%s" % self.sqlEncode(values[1]))
                db.query(cmd)
                cmd = ("select places_left from seminars "
                    "where id=%s" % self.sqlEncode(values[1]))
                if (db.query(cmd).getresult()[0][0] or 0) < 0:
                    raise self.dbapi.Error("No more places left.")
                cmd = ("insert into attendees values (%s,%s,%s)"
                    % tuple(map(self.sqlEncode, values)))
                db.query(cmd)
                db.query('end')
            else:
                cursor = db.cursor()
                cmd = ("update seminars set places_left=places_left-1 "
                    "where id=%s" % self.sqlEncode(values[1]))
                cursor.execute(cmd)
                cmd = ("select places_left from seminars "
                    "where id=%s" % self.sqlEncode(values[1]))
                cursor.execute(cmd)
                if (cursor.fetchone()[0] or 0) < 0:
                    raise self.dbapi.Error("No more places left.")
                cmd = ("insert into attendees values (%s,%s,%s)"
                    % tuple(map(self.sqlEncode, values)))
                db.cursor().execute(cmd)
                cursor.close()
                db.commit()
        except self.dbapi.Error, error:
            if self.dbapi_name == 'pg':
                db.query('end')
            else:
                db.rollback()
            self.outputMsg(error, True)
        else:
            self.outputMsg('%s added to attendees.' % values[0])
        db.close()

    def writeContent(self):
        wr = self.writeln
        if self._output:
            wr('\n'.join(self._output))
            wr('<p><a href="DBUtilsExample">Back</a></p>')
        else:
            wr('<h2>Welcome to the %s!</h2>' % self.title())
            wr('<h4>We are using DBUtils.%s and the %s database module.</h4>'
                % (self.dbmod_name, self.dbapi_name))
            wr('<p>Configuration: %r</p>' % DBConfig().config())
            wr('<p>This example uses a small demo database '
                'designed to track the attendees for a series of seminars '
                '(see <a href="http://www.linuxjournal.com/article/2605">"'
                'The Python DB-API"</a> by Andrew Kuchling).</p>')
            wr('<form action="">'
                '<p>%s (create the needed database tables first)</p>'
                '<p>%s %s (list all database entries)</p>'
                '<p>%s %s (add entries)</p>'
                '</form>' % self._buttons)
