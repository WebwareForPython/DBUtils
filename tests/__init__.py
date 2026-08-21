"""The DBUtils tests package."""

import sys

from . import mock_pg

# make the mock pg module importable as "pg"
sys.modules['pg'] = mock_pg
