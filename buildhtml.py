#!/usr/bin/env python

"""Build HMTL from reSt files."""

from docutils.core import publish_file

print "Creating the documentation..."

publish_file(writer_name='html',
    source=file('DBUtils/Docs/UsersGuide.txt', 'r'),
    destination=file('DBUtils/Docs/UsersGuide.html', 'w'),
    settings_overrides = dict(
        stylesheet_path='Doc.css',
        embed_stylesheet=False))

print "Done."
