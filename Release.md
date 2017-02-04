Create a new DBUtils release:
=============================

* Check the documentation. If possible, update all translations.
  (Chinese translation was too old and has been removed for the time being.)

* Run all tests in DBUtils/Tests with Python version from 2.3 to 2.7.

* Check the examples in DBUtils/Examples with the current Webware version.

* Update and check the Release Notes and copyright information.

* Set version number and release date with `setversion.py`.

* Revert to old version number for translations that have not been updated.

* Build html pages using `buildhtml.py`.

* Create a tag in the Git repository.

* Create a source tarball with:

        python setup.py sdist

  You will find the tarball in the "dist" folder.

  Under Windows, this will be a .zip file, otherwise a .tar.gz file.
  You can force .tar.gz under Windows with `--formats=gztar`,
  but you need to use WSL, Cygwin or have a tar binary installed.
  Generally, it is better to create the release under Unix to avoid
  problems with DOS line feeds and wrong file permission.

* Upload to the Python Package Index:

    Create a .pypirc file in your home directory as follows:

        echo "[pypi]
        repository=https://pypi.python.org/pypi
        username:myusername
        password:mypassword
        
        [pypitest]
        repository=https://testpypi.python.org/pypi
        username:myusername
        password:mypassword       
        " > ~.pypirc

* Register the project on the test PyPI with:

        python setup.py register -r pypitest

* Upload the source package to the test PyPI with:

        python setup.py sdist upload -r pypitest

  You have to install setuptools to make this work.
  
* Register and upload the project to the real PyPI with:

        python setup.py register -r pypi
        python setup.py sdist upload -r pypi

    See also: http://peterdowns.com/posts/first-time-with-pypi.html

* Don't forget to update the home page:

    * https://cito.github.io/DBUtils/
    * https://cito.github.io/w4py/

