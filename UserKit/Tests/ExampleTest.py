"""
Tests various functions of Users and Roles

To run these tests:
	cd Webware
	python AllTests.py UserKit.Tests.ExampleTest
"""

import os, sys, glob
import shutil
import logging
import unittest

import UserKit

_log = logging.getLogger(__name__)

TEST_CODE_DIR = os.path.dirname(__file__) # e.g. ".../Webware/UserKit/Tests"


class SimpleExampleTest(unittest.TestCase):
	"""A simple example to illustrate how to use UserKit."""

	def setUpDataDir(self, userManager):
		"""Make a folder for UserManager data."""

		self.userDataDir = os.path.join(TEST_CODE_DIR, 'Users')

		if os.path.exists(self.userDataDir):
			shutil.rmtree(self.userDataDir, ignore_errors=1)
		os.mkdir(self.userDataDir)

		userManager.setUserDir(self.userDataDir)

	def tearDown(self):

		# Remove our test folder for UserManager data
		if os.path.exists(self.userDataDir):
			shutil.rmtree(self.userDataDir, ignore_errors=1)
		self.mgr = None


	def testUsersNoRoles(self):
		from UserKit.UserManagerToFile import UserManagerToFile
		from UserKit.HierRole import HierRole

		self.mgr = UserManagerToFile()
		self.setUpDataDir(self.mgr)

		# Create a user, add to 'staff' role
		fooUser = self.mgr.createUser('foo', 'bar')

		# bad login
		theUser = self.mgr.loginName('foo', 'badpass')
		assert theUser is None, 'loginName() returns null if login failed.'
		assert not fooUser.isActive(), \
			'User should NOT be logged in since password was incorrect.'

		# good login
		theUser = self.mgr.loginName('foo', 'bar')
		assert theUser.isActive(), 'User should be logged in now'
		assert theUser == fooUser, \
			'Should be the same user object, since it is the same user "foo"'

		# logout
		theUser.logout()
		assert not theUser.isActive(), 'User should no longer be active.'
		assert self.mgr.numActiveUsers() == 0


	def testUsersAndRoles(self):
		from UserKit.RoleUserManagerToFile import RoleUserManagerToFile
		from UserKit.HierRole import HierRole
		from sha import sha

		self.mgr = RoleUserManagerToFile()
		self.setUpDataDir(self.mgr)

		# Setup our roles
		customersRole = HierRole('customers', 'Customers of ACME Industries')
		staffRole = HierRole('staff', 'All staff.'
			' Staff role includes all permissions of Customers role.',
			[customersRole])

		# Create a user, add to 'staff' role
		# Note that I encrypt my passwords here so they don't appear
		# in plaintext in the storage file.
		johnUser = self.mgr.createUser('john', sha('doe').hexdigest())
		johnUser.setRoles([customersRole])

		fooUser = self.mgr.createUser('foo', sha('bar').hexdigest())
		fooUser.setRoles([staffRole])

		# Check FOO user
		theUser = self.mgr.loginName('foo', sha('bar').hexdigest())
		assert theUser.isActive(), 'User should be logged in now'
		assert theUser == fooUser, \
			'Should be the same user object, since it is the same user "foo"'
		assert theUser.playsRole(staffRole), \
			'User "foo" should be a member of the staff role.'
		assert theUser.playsRole(customersRole), 'User "foo" should' \
			' also be in customer role, since staff includes customers.'

		# Check JOHN user
		theUser = self.mgr.loginName('john', sha('doe').hexdigest())
		assert theUser.isActive(), 'User should be logged in now.'
		assert theUser == johnUser, \
			'Should be the same user object, since it is the same user "John".'
		assert not theUser.playsRole(staffRole), \
			'John should not be a member of the staff.'
		assert theUser.playsRole(customersRole), \
			'John should in customer role.'
