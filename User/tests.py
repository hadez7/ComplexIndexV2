from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

class LogoutRedirectTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client = Client()

    def test_logout_redirects_to_index(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('index'))
