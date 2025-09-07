#!/usr/bin/env python3.12

"""Build HTML from reST files."""

from pathlib import Path

from docutils.core import publish_file

print("Creating the documentation...")

for rst_file in Path().glob('*.rst'):
    rst_path = Path(rst_file)
    name = Path(rst_file).stem
    lang = Path(name).suffix
    if lang.startswith('.'):
        lang = lang[1:]
        if lang == 'zh':
            lang = 'zh_cn'
    else:
        lang = 'en'
    html_path = Path(name + '.html')
    print(name, lang)

    with rst_path.open(encoding='utf-8') as source, \
            html_path.open('w', encoding='utf-8') as destination:
        output = publish_file(
            writer_name='html5', source=source, destination=destination,
            enable_exit_status=True,
            settings_overrides={
                "stylesheet_path": 'doc.css',
                "embed_stylesheet": False,
                "toc_backlinks": False,
                "language_code": lang,
                "exit_status_level": 2})

print("Done.")
