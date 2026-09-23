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


class AuthViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='Password123!'
        )

    def test_login_page_renders_properly(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        content = response.content.decode('utf-8')
        self.assertIn('Iniciar sesión', content)
        self.assertIn('Enterprise Lex Index', content)
        self.assertIn(reverse('register'), content)

    def test_login_with_invalid_credentials_shows_error(self):
        response = self.client.post(reverse('login'), {
            'username': 'wronguser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        content = response.content.decode('utf-8')
        self.assertIn('No pudimos iniciar tu sesión', content)

    def test_register_page_renders_properly(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')
        content = response.content.decode('utf-8')
        self.assertIn('Crear cuenta', content)
        self.assertIn('Nombre(s)', content)
        self.assertIn('Apellidos', content)
        self.assertIn(reverse('login'), content)

    def test_successful_registration_with_names(self):
        response = self.client.post(reverse('register'), {
            'username': 'newauditor',
            'first_name': 'Carlos',
            'last_name': 'Mendoza',
            'email': 'carlos.mendoza@example.com',
            'password1': 'AuditorSecure2025!',
            'password2': 'AuditorSecure2025!',
        })
        self.assertRedirects(response, reverse('index'))
        created_user = User.objects.get(username='newauditor')
        self.assertEqual(created_user.first_name, 'Carlos')
        self.assertEqual(created_user.last_name, 'Mendoza')
        self.assertEqual(created_user.email, 'carlos.mendoza@example.com')

    def test_duplicate_email_registration_fails(self):
        response = self.client.post(reverse('register'), {
            'username': 'anotheruser',
            'email': 'existing@example.com',
            'password1': 'AuditorSecure2025!',
            'password2': 'AuditorSecure2025!',
        })
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Este correo electrónico ya está registrado', content)
