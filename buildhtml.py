#!/usr/bin/env python

"""Build HMTL from reST files."""

from docutils.core import publish_file

print "Creating the documentation..."

publish_file(writer_name='html',
    source=open('DBUtils/Docs/UsersGuide.txt', 'r'),
    destination=open('DBUtils/Docs/UsersGuide.html', 'w'),
    settings_overrides = dict(
        stylesheet_path='Doc.css', embed_stylesheet=False,
        toc_backlinks=False))

print "Done."
