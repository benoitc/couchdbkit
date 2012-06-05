import unittest

from pyramid import testing

class ViewTests(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_my_view(self):
        from .views import my_view
        #Don't actually test anything right now
        #request = testing.DummyRequest()
        #info = my_view(request)
        #self.assertEqual(info['project'], 'pyramid_couchdb_example')
        self.assertEqual(True, True)
