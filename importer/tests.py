from django.test import TestCase
from selenium import webdriver


class FunctionalTestCase(TestCase):

    def setUp(self):
        self.browser = webdriver.Chrome()

    def test_there_is_homepage(self):
        self.browser.get('http://localhost:8000')
        self.assertIn('contacts', self.browser.page_source)

    def tearDown(self):
        self.browser.quit()


class UnitTestCase(TestCase):

    def test_home_homepage_template(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'importer/home.html')

    def test_home_contacts_template(self):
        response = self.client.get('/contacts/')
        self.assertTemplateUsed(response, 'importer/contacts.html')
