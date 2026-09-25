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


from User.models import UserProfile, UserAuditLog
import json

class UserAuditAndSoftDeleteTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='adminuser',
            email='admin@example.com',
            password='AdminPassword123!'
        )
        self.regular_user = User.objects.create_user(
            username='regularuser',
            email='regular@example.com',
            password='RegularPassword123!'
        )

    def test_user_profile_created_automatically(self):
        self.assertTrue(hasattr(self.regular_user, 'profile'))
        self.assertFalse(self.regular_user.profile.is_deleted)
        self.assertIsNone(self.regular_user.profile.deleted_at)

    def test_soft_delete_preserves_user_and_marks_deleted(self):
        self.client.login(username='adminuser', password='AdminPassword123!')
        url = reverse('users_delete', kwargs={'user_id': self.regular_user.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertTrue(data.get('soft_deleted'))

        # Check DB state
        self.regular_user.refresh_from_db()
        self.assertFalse(self.regular_user.is_active)
        self.assertTrue(self.regular_user.profile.is_deleted)
        self.assertIsNotNone(self.regular_user.profile.deleted_at)

        # Check Audit Log
        log = UserAuditLog.objects.filter(target_user=self.regular_user, action='SOFT_DELETE').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.admin_user)
        self.assertEqual(log.target_username, 'regularuser')

    def test_cannot_soft_delete_self(self):
        self.client.login(username='adminuser', password='AdminPassword123!')
        url = reverse('users_delete', kwargs={'user_id': self.admin_user.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json().get('success'))

    def test_cannot_soft_delete_superuser(self):
        other_super = User.objects.create_superuser(
            username='othersuper',
            email='super2@example.com',
            password='SuperPassword123!'
        )
        self.client.login(username='adminuser', password='AdminPassword123!')
        url = reverse('users_delete', kwargs={'user_id': other_super.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json().get('success'))

    def test_restore_soft_deleted_user(self):
        # Soft delete first
        self.client.login(username='adminuser', password='AdminPassword123!')
        self.client.post(reverse('users_delete', kwargs={'user_id': self.regular_user.id}))
        
        self.regular_user.refresh_from_db()
        self.assertTrue(self.regular_user.profile.is_deleted)
        self.assertFalse(self.regular_user.is_active)

        # Reactivate via toggle
        toggle_url = reverse('users_toggle_active', kwargs={'user_id': self.regular_user.id})
        toggle_res = self.client.post(toggle_url)
        self.assertEqual(toggle_res.status_code, 200)

        self.regular_user.refresh_from_db()
        self.assertTrue(self.regular_user.is_active)
        self.assertFalse(self.regular_user.profile.is_deleted)
        self.assertIsNone(self.regular_user.profile.deleted_at)

        # Check restore audit log
        restore_log = UserAuditLog.objects.filter(target_user=self.regular_user, action='RESTORE').first()
        self.assertIsNotNone(restore_log)

    def test_update_user_audit_log(self):
        self.client.login(username='adminuser', password='AdminPassword123!')
        update_url = reverse('users_update')
        payload = {
            'user_id': self.regular_user.id,
            'email': 'juan.perez@example.com',
            'is_staff': True
        }
        res = self.client.post(update_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)

        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.email, 'juan.perez@example.com')
        self.assertTrue(self.regular_user.is_staff)

        # Role change log should exist
        log = UserAuditLog.objects.filter(target_user=self.regular_user, action='ROLE_CHANGE').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.admin_user)

    def test_login_creates_audit_log(self):
        # Initial login
        self.client.login(username='regularuser', password='RegularPassword123!')
        login_log = UserAuditLog.objects.filter(target_username='regularuser', action='LOGIN').first()
        self.assertIsNotNone(login_log)
        self.assertEqual(login_log.actor, self.regular_user)

    def test_audit_logs_endpoint_access(self):
        # Admin should access logs
        self.client.login(username='adminuser', password='AdminPassword123!')
        url = reverse('users_audit_logs')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get('success'))
        self.assertIsInstance(data.get('logs'), list)

        # Regular user should not have access
        self.client.login(username='regularuser', password='RegularPassword123!')
        res_regular = self.client.get(url)
        self.assertIn(res_regular.status_code, [302, 403])
