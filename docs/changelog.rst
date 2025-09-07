Changelog for DBUtils
+++++++++++++++++++++

3.1.2
=====

DBUtils 3.1.2 was released on September 7, 2025.

Changes:

* Support Python version 3.14.

3.1.1
=====

DBUtils 3.1.1 was released on June 4, 2025.

Changes:

* Support Python version 3.13.

3.1.0
=====

DBUtils 3.1.0 was released on March 17, 2024.

Changes:

* Support Python version 3.12, cease support for Python 3.6.
* Various small internal improvements and modernizations.

3.0.3
=====

DBUtils 3.0.3 was released on April 27, 2023.

Changes:

* Support Python version 3.11.
* Improve determination of DB API module if creator is specified.
* Minor fixes and section an advanced usage in docs.

3.0.2
=====

DBUtils 3.0.2 was released on January 14, 2022.

The optional iterator protocol on cursors is now supported.

3.0.1
=====

DBUtils 3.0.1 was released on December 22, 2021.

It includes ``InterfaceError`` to the default list of exceptions
for which the connection failover mechanism is applied.
You can override this with the ``failures`` parameter.

3.0.0
=====

DBUtils 3.0.0 was released on November 26, 2021.

It is intended to be used with Python versions 3.6 to 3.10.

Changes:

* Cease support for Python 2 and 3.5, minor optimizations.

2.0.3
=====

DBUtils 2.0.3 was released on November 26, 2021.

Changes:

* Support Python version 3.10.

2.0.2
=====

DBUtils 2.0.2 was released on June 8, 2021.

Changes:

* Allow using context managers for pooled connections.

2.0.1
=====

DBUtils 2.0.1 was released on April 8, 2021.

Changes:

* Avoid "name Exception is not defined" when exiting.

2.0
===

DBUtils 2.0 was released on September 26, 2020.

It is intended to be used with Python versions 2.7 and 3.5 to 3.9.

Changes:

* DBUtils does not act as a Webware plugin anymore, it is now just an ordinary
  Python package (of course it could be used as such also before).
* The Webware ``Examples`` folder has been removed.
* Folders, packages and modules have been renamed to lower-case.
  Particularly, you need to import ``dbutils`` instead of ``DBUtils`` now.
* The internal naming conventions have also been changed to comply with PEP8.
* The documentation has been adapted to reflect the changes in this version.
* This changelog has been compiled from the former release notes.

1.4
===

DBUtils 1.4 was released on September 26, 2020.

It is intended to be used with Python versions 2.7 and 3.5 to 3.9.

Improvements:

* The ``SteadyDB`` and ``SteadyPg`` classes only reconnect after the
  ``maxusage`` limit has been reached when the connection is not currently
  inside a transaction.

1.3
===

DBUtils 1.3 was released on March 3, 2018.

It is intended to be used with Python versions 2.6, 2.7 and 3.4 to 3.7.

Improvements:

* This version now supports context handlers for connections and cursors.

1.2
===

DBUtils 1.2 was released on February 5, 2017.

It is intended to be used with Python versions 2.6, 2.7 and 3.0 to 3.6.

1.1.1
=====

DBUtils 1.1.1 was released on February 4, 2017.

It is intended to be used with Python versions 2.3 to 2.7.

Improvements:

* Reopen ``SteadyDB`` connections when commit or rollback fails
  (suggested by Ben Hoyt).

Bugfixes:

* Fixed a problem when running under Jython (reported by Vitaly Kruglikov).

1.1
===

DBUtils 1.1 was released on August 14, 2011.

Improvements:

* The transparent reopening of connections is actually an undesired behavior
  if it happens during database transactions. In these cases, the transaction
  should fail and the error be reported back to the application instead of the
  rest of the transaction being executed in a new connection and therefore in
  a new transaction. Therefore DBUtils now allows suspending the transparent
  reopening during transactions. All you need to do is indicate the beginning
  of a transaction by calling the ``begin()`` method of the connection.
  DBUtils makes sure that this method always exists, even if the database
  driver does not support it.
* If the database driver supports a ``ping()`` method, then DBUtils can use it
  to check whether connections are alive instead of just trying to use the
  connection and reestablishing it in case it was dead. Since these checks are
  done at the expense of some performance, you have exact control when these
  are executed via the new ``ping`` parameter.
* ``PooledDB`` has got another new parameter ``reset`` for controlling how
  connections are reset before being put back into the pool.

Bugfixes:

* Fixed propagation of error messages when the connection was lost.
* Fixed an issue with the ``setoutputsize()``  cursor method.
* Fixed some minor issues with the ``DBUtilsExample`` for Webware.


1.0
===

DBUtils 1.0 was released on November 29, 2008.

It is intended to be used with Python versions 2.2 to 2.6.

Changes:

* Added a ``failures`` parameter for configuring the exception classes for
  which the failover mechanisms is applied (as suggested by Matthew Harriger).
* Added a ``closeable`` parameter for configuring whether connections can be
  closed (otherwise closing connections will be silently ignored).
* It is now possible to override defaults via the ``creator.dbapi`` and
  ``creator.threadsafety`` attributes.
* Added an alias method ``dedicated_connection`` as a shorthand for
  ``connection(shareable=False)``.
* Added a version attribute to all exported classes.
* Where the value ``0`` has the meaning "unlimited", parameters can now be also
  set to the value ``None`` instead.
* It turned out that ``threading.local`` does not work properly with
  ``mod_wsgi``, so we use the Python implementation for thread-local data
  even when a faster ``threading.local`` implementation is available.
  A new parameter ``threadlocal`` allows you to pass an arbitrary class
  such as ``threading.local`` if you know it works in your environment.

Bugfixes and improvements:

* In some cases, when instance initialization failed or referenced objects
  were already destroyed, finalizers could throw exceptions or create infinite
  recursion (problem reported by Gregory Pinero and Jehiah Czebotar).
* DBUtils now tries harder to find the underlying DB-API 2 module if only a
  connection creator function is specified. This had not worked before with
  the MySQLdb module (problem reported by Gregory Pinero).

0.9.4
=====

DBUtils 0.9.4 was released on July 7, 2007.

This release fixes a problem in the destructor code and has been supplemented
with a German User's Guide.

Again, please note that the ``dbapi`` parameter has been renamed to ``creator``
in the last release, since you can now pass custom creator functions
for database connections instead of DB-API 2 modules.

0.9.3
=====

DBUtils 0.9.3 was released on May 21, 2007.

Changes:

* Support custom creator functions for database connections.
  These can now be used as the first parameter instead of an DB-API module
  (suggested by Ezio Vernacotola).
* Added destructor for steady connections.
* Use setuptools_ if available.
* Some code cleanup.
* Some fixes in the documentation.
  Added Chinese translation of the User's Guide, kindly contributed by gashero.

.. _setuptools: https://github.com/pypa/setuptools

0.9.2
=====

DBUtils 0.9.2 was released on September 22, 2006.

It is intended to be used with Python versions 2.2 to 2.5.

Changes:

* Renamed ``SolidDB`` to ``SteadyDB`` to avoid confusion with the "solidDB"
  storage engine. Accordingly, renamed ``SolidPg`` to ``SteadyPg``.

0.9.1
=====

DBUtils 0.9.1 was released on May 8, 2006.

It is intended to be used with Python versions 2.2 to 2.4.

Changes:

* Added ``_closeable`` attribute and made persistent connections not closeable
  by default. This allows ``PersistentDB``  to be used in the same way as you
  would use ``PooledDB``.
* Allowed arguments in the DB-API 2 ``cursor()`` method. MySQLdb is using this
  to specify cursor classes. (Suggested by Michael Palmer.)
* Improved the documentation and added a User's Guide.

0.8.1 - 2005-09-13
==================

DBUtils 0.8.1 was released on September 13, 2005.

It is intended to be used with Python versions 2.0 to 2.4.

This is the first public release of DBUtils.
