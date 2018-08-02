Create a new DBUtils release:
=============================

* Check the documentation. If possible, update all translations.
  (Chinese translation was too old and has been removed for the time being.)

* Use tox to run all tests in DBUtils/Tests with all supported Python versions
  and to run flake8 in order to check the code style and quality.

* Check the examples in DBUtils/Examples with the current Webware version.

* Update and check the Release Notes and copyright information.

* Set version number and release date with `setversion.py`.

* Revert to old version number for translations that have not been updated.

* Build html pages using `buildhtml.py`.

* Create a tag in the Git repository.

* Create a source tarball with:

        python setup.py sdist

  You will find the tarball in the "dist" folder.

  Generally, it is better to create the release under Unix to avoid
  problems with DOS line feeds and wrong file permission.

* Upload to the Python Package Index:

    Create a .pypirc file in your home directory as follows:

        echo "[pypi]
        repository: https://upload.pypi.org/legacy/
        username: your username
        password: your password
        
        [pypitest]
        repository: https://test.pypi.org/legacy/
        username: your username
        password: your password     
        " > ~.pypirc


* Upload the source package to the test PyPI with:

        twine upload -r pypitest dist/*.tar.gz
 
* Register and upload the project to the real PyPI with:

        twine upload -r pypi dist/*.tar.gz

* Don't forget to update the home page:

    * https://cito.github.io/DBUtils/
    * https://cito.github.io/w4py/
