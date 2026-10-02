import json

from django.db.models import ProtectedError
from django.test import TestCase, Client, modify_settings
from django.contrib.auth.models import User
from django.urls import reverse
from Counter.models import (
    Company, Report, TotalCount, TotalCountReport,
    ConcealmentReview, ConcealmentParagraphReview,
    Workspace, WorkspaceMembership, ExpertWord,
)
from User.models import Expert


class ConcealmentDetectionFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testauditor', password='password123')
        self.client = Client()
        self.client.login(username='testauditor', password='password123')

        # Todos los datos viven en un espacio de trabajo (campo obligatorio).
        self.ws = Workspace.objects.create(name='Espacio de Auditoría', created_by=self.user)

        self.company1 = Company.objects.create(workspace=self.ws, name='EMPRESA ALFA S.A.', ruc='0990000001001')
        self.company2 = Company.objects.create(workspace=self.ws, name='EMPRESA BETA S.A.', ruc='0990000002001')

        self.report1 = Report.objects.create(
            workspace=self.ws,
            company=self.company1,
            name='2024',
            year=2024
        )
        self.report2 = Report.objects.create(
            workspace=self.ws,
            company=self.company2,
            name='2024',
            year=2024
        )

        TotalCountReport.objects.create(report=self.report1, word='ingresos', quantity=10)
        TotalCountReport.objects.create(report=self.report2, word='gastos', quantity=5)

    def test_filter_labels_present(self):
        response = self.client.get(reverse('concealment_detection'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Año del reporte', content)
        self.assertIn('Selecciona una empresa:', content)

    def test_filter_persistence_on_search(self):
        url = f"{reverse('concealment_detection')}?year=2024&report_id={self.report2.id}&origen_palabras=reporte&palabra=gastos"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context['selected_year'], '2024')
        self.assertEqual(response.context['selected_report'].id, self.report2.id)
        self.assertEqual(response.context['palabra'], 'gastos')

        content = response.content.decode('utf-8')
        self.assertIn('value="2024"', content)
        self.assertIn(f'value="{self.report2.id}" selected', content)
        self.assertIn('EMPRESA BETA S.A.', content)

    def test_get_reports_by_year_ajax(self):
        url = reverse('get_reports_by_year') + '?year=2024'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        names = [item['name'] for item in data]
        self.assertIn('EMPRESA ALFA S.A.', names)
        self.assertIn('EMPRESA BETA S.A.', names)

    def test_company_ordering_ignores_leading_whitespace(self):
        # Create a company with a leading space that starts with 'Z'
        # Without Trim, ASCII space (32) would sort it before 'EMPRESA ALFA S.A.' (65)
        company_z = Company.objects.create(workspace=self.ws, name=' ZETA S.A.', ruc='0990000003001')
        report_z = Report.objects.create(workspace=self.ws, company=company_z, name='2024', year=2024)

        url = reverse('concealment_detection') + '?year=2024'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        reports = list(response.context['reports'])
        # EMPRESA ALFA must come first, not ' ZETA S.A.'
        self.assertEqual(reports[0].clean_company, 'EMPRESA ALFA S.A.')
        self.assertEqual(reports[-1].clean_company, 'ZETA S.A.')

        # Also check AJAX endpoint
        ajax_url = reverse('get_reports_by_year') + '?year=2024'
        ajax_resp = self.client.get(ajax_url)
        self.assertEqual(ajax_resp.status_code, 200)
        ajax_data = ajax_resp.json()
        self.assertEqual(ajax_data[0]['name'], 'EMPRESA ALFA S.A.')
        self.assertEqual(ajax_data[-1]['name'], 'ZETA S.A.')

    def test_concealment_review_records_user_and_history(self):
        # 1. Create a review via POST
        post_data = {
            'report_id': self.report1.id,
            'palabra': 'ingresos',
            'parrafos_validos': ['0'],
        }
        resp = self.client.post(reverse('concealment_detection'), post_data)
        self.assertEqual(resp.status_code, 200)

        # Verify ConcealmentReview saved with request.user
        review = ConcealmentReview.objects.filter(report=self.report1, word='ingresos').latest('reviewed_at')
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.total_valid, 0) # paragraph counts depends on find_paragraph mock/file, but record exists

        # 2. Test GET shows recent_reviews
        get_url = f"{reverse('concealment_detection')}?year=2024&report_id={self.report1.id}&palabra=ingresos"
        get_resp = self.client.get(get_url)
        self.assertEqual(get_resp.status_code, 200)
        self.assertIn('recent_reviews', get_resp.context)
        self.assertGreaterEqual(len(get_resp.context['recent_reviews']), 1)
        self.assertEqual(get_resp.context['recent_reviews'][0].user, self.user)

    def test_concealment_history_view_and_filters(self):
        # Create a sample review
        rev = ConcealmentReview.objects.create(
            report=self.report2,
            user=self.user,
            word='gastos',
            total_found=5,
            total_valid=3,
            total_discarded=2
        )
        ConcealmentParagraphReview.objects.create(
            review=rev,
            paragraph_text='Parrafo sobre gastos operacionales.',
            occurrences=3,
            discarded=False
        )
        ConcealmentParagraphReview.objects.create(
            review=rev,
            paragraph_text='Parrafo no relevante con gastos.',
            occurrences=2,
            discarded=True
        )

        # Test history view status
        history_url = reverse('concealment_history')
        resp = self.client.get(history_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Historial de Auditoría')
        self.assertContains(resp, 'gastos')
        self.assertContains(resp, self.user.username)

        # Test filter by year
        resp_year = self.client.get(history_url + '?year=2024')
        self.assertEqual(resp_year.status_code, 200)
        self.assertEqual(len(resp_year.context['reviews']), 1)
        self.assertIn(self.company2, resp_year.context['companies'])

        # Test filter by year + company ID
        resp_year_company = self.client.get(f'{history_url}?year=2024&company={self.company2.id}')
        self.assertEqual(resp_year_company.status_code, 200)
        self.assertEqual(len(resp_year_company.context['reviews']), 1)

        # Test filter by year + other company with no reviews
        resp_other_company = self.client.get(f'{history_url}?year=2024&company={self.company1.id}')
        self.assertEqual(resp_other_company.status_code, 200)
        self.assertEqual(len(resp_other_company.context['reviews']), 0)

        # Test filter by non-existent year
        resp_wrong_year = self.client.get(history_url + '?year=2020')
        self.assertEqual(resp_wrong_year.status_code, 200)
        self.assertEqual(len(resp_wrong_year.context['reviews']), 0)

        # Test filter by auditor
        resp_auditor = self.client.get(history_url + f'?user={self.user.username}')
        self.assertEqual(resp_auditor.status_code, 200)
        self.assertEqual(len(resp_auditor.context['reviews']), 1)

        # Test filter by word
        resp_word = self.client.get(history_url + '?word=gastos')
        self.assertEqual(resp_word.status_code, 200)
        self.assertEqual(len(resp_word.context['reviews']), 1)

        # Test filter by non-existent word
        resp_none = self.client.get(history_url + '?word=noexiste')
        self.assertEqual(len(resp_none.context['reviews']), 0)

        # Test AJAX detail endpoint
        detail_url = reverse('concealment_history_detail', args=[rev.id])
        detail_resp = self.client.get(detail_url)
        self.assertEqual(detail_resp.status_code, 200)
        json_data = detail_resp.json()
        self.assertEqual(json_data['word'], 'gastos')
        self.assertEqual(json_data['user'], self.user.username)
        self.assertEqual(len(json_data['paragraphs']), 2)
        self.assertEqual(json_data['paragraphs'][0]['discarded'], False)
        self.assertEqual(json_data['paragraphs'][1]['discarded'], True)


class ComparativeAnalysisTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='analyst', password='password')
        self.client.login(username='analyst', password='password')
        self.ws = Workspace.objects.create(name='Espacio Análisis', created_by=self.user)
        self.company = Company.objects.create(workspace=self.ws, name='ACME CORP S.A.', ruc='0990000004001')
        self.report = Report.objects.create(
            workspace=self.ws,
            company=self.company,
            name='2024',
            year=2024
        )

    def test_reports_by_year_returns_company_name(self):
        url = reverse('reports_by_year') + '?year=2024'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], self.report.id)
        # Verify it does not just return '2024'
        self.assertEqual(data[0]['name'], 'ACME CORP S.A.')

    def test_comparative_form_report_label_shows_company(self):
        from Counter.forms import ComparativeAnalysisForm
        form = ComparativeAnalysisForm(data={'year': '2024'}, workspace=self.ws)
        choices = list(form.fields['report'].choices)
        # First choice is the empty label
        self.assertEqual(choices[0][0], '')
        # Second choice should have ACME CORP S.A. as label
        self.assertEqual(choices[1][0], self.report.id)
        self.assertEqual(choices[1][1], 'ACME CORP S.A.')

    def test_comparative_analysis_view_renders(self):
        url = reverse('comparative_analysis')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Análisis comparativo')
        self.assertContains(response, 'Comparar reporte con lista de experto')


class ReportSearchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin_reports', password='password')
        self.client.login(username='admin_reports', password='password')
        self.ws = Workspace.objects.create(name='Espacio Reportes', created_by=self.user)
        self.company1 = Company.objects.create(workspace=self.ws, name='ALPHA LOGISTICS S.A.', ruc='0990000005001')
        self.company2 = Company.objects.create(workspace=self.ws, name='OMEGA HOLDINGS S.A.', ruc='0990000006001')
        self.rep1 = Report.objects.create(workspace=self.ws, company=self.company1, name='Memoria Anual 2024', year=2024)
        self.rep2 = Report.objects.create(workspace=self.ws, company=self.company2, name='Balance 2023', year=2023)

    def test_search_reports_by_name(self):
        url = reverse('reports') + '?q=Memoria'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f'id="reporte-{self.rep1.id}"')
        self.assertNotContains(resp, f'id="reporte-{self.rep2.id}"')

    def test_search_reports_by_company(self):
        url = reverse('reports') + '?q=OMEGA'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f'id="reporte-{self.rep2.id}"')
        self.assertNotContains(resp, f'id="reporte-{self.rep1.id}"')

    def test_search_reports_no_results(self):
        url = reverse('reports') + '?q=Inexistente'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'No se encontraron reportes que coincidan con')
        self.assertNotContains(resp, f'id="reporte-{self.rep1.id}"')
        self.assertNotContains(resp, f'id="reporte-{self.rep2.id}"')


class PanelViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='paneluser', password='password123')
        self.client = Client()

    def test_panel_requires_login(self):
        resp = self.client.get(reverse('panel'))
        self.assertEqual(resp.status_code, 302)

    def test_panel_authenticated_renders(self):
        # Necesita un espacio: sin él, el panel redirige a la pantalla de espacios.
        Workspace.objects.create(name='Espacio Panel', created_by=self.user)
        self.client.login(username='paneluser', password='password123')
        resp = self.client.get(reverse('panel'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Panel de Administración')
        self.assertContains(resp, 'Empresas')
        self.assertContains(resp, 'Reportes')


class UploadModuleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='uploaduser', password='password123')
        self.client.login(username='uploaduser', password='password123')
        self.ws = Workspace.objects.create(name='Espacio Subida', created_by=self.user)
        self.company = Company.objects.create(workspace=self.ws, name='BETA CORP S.A.', ruc='0990000007001')

    def test_upload_view_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse('upload'))
        self.assertEqual(resp.status_code, 302)

    def test_upload_view_renders_correctly(self):
        resp = self.client.get(reverse('upload'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Subida y Procesamiento de Reportes')
        self.assertContains(resp, 'Subir Reporte Individual (PDF)')
        self.assertContains(resp, 'Subir Múltiples Reportes (Lote ZIP)')
        self.assertContains(resp, 'Sobrescribir si ya existe')

    def test_form_rejects_non_pdf_file(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from Counter.forms import IndividualReportUploadForm

        fake_txt = SimpleUploadedFile("documento.txt", b"Texto plano de prueba", content_type="text/plain")
        form = IndividualReportUploadForm(
            data={"company": self.company.id, "year": 2024},
            files={"file": fake_txt},
            workspace=self.ws
        )
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)
        self.assertIn("PDF", form.errors["file"][0])

    def test_form_rejects_invalid_pdf_header(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from Counter.forms import IndividualReportUploadForm

        fake_pdf = SimpleUploadedFile("falso.pdf", b"NO ES UN PDF REAL", content_type="application/pdf")
        form = IndividualReportUploadForm(
            data={"company": self.company.id, "year": 2024},
            files={"file": fake_pdf},
            workspace=self.ws
        )
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)

    def test_form_detects_duplicate_company_year_without_overwrite(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from Counter.forms import IndividualReportUploadForm

        # Create existing report
        Report.objects.create(workspace=self.ws, company=self.company, year=2024, name="Existente 2024")

        valid_pdf_content = b"%PDF-1.4\n%trailer\n%%EOF"
        pdf_file = SimpleUploadedFile("nuevo.pdf", valid_pdf_content, content_type="application/pdf")

        form = IndividualReportUploadForm(
            data={"company": self.company.id, "year": 2024, "overwrite": False},
            files={"file": pdf_file},
            workspace=self.ws
        )
        self.assertFalse(form.is_valid())
        self.assertIn("Ya existe un reporte registrado", str(form.errors))

    def test_form_allows_duplicate_company_year_with_overwrite(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from Counter.forms import IndividualReportUploadForm

        Report.objects.create(workspace=self.ws, company=self.company, year=2024, name="Existente 2024")

        valid_pdf_content = b"%PDF-1.4\n%trailer\n%%EOF"
        pdf_file = SimpleUploadedFile("nuevo.pdf", valid_pdf_content, content_type="application/pdf")

        form = IndividualReportUploadForm(
            data={"company": self.company.id, "year": 2024, "overwrite": True},
            files={"file": pdf_file},
            workspace=self.ws
        )
        self.assertTrue(form.is_valid())

    def test_delete_report_decrements_total_count(self):
        from Counter.models import TotalCount, TotalCountReport

        report = Report.objects.create(workspace=self.ws, company=self.company, year=2024, name="Reporte Prueba")
        TotalCountReport.objects.create(report=report, word="palabraprueba", quantity=15)
        TotalCount.objects.create(workspace=self.ws, word="palabraprueba", quantity=15)

        # Ensure TotalCount starts at 15
        self.assertEqual(TotalCount.objects.get(word="palabraprueba").quantity, 15)

        # Delete the report via endpoint
        del_resp = self.client.delete(reverse('delete_report', args=[report.id]))
        self.assertEqual(del_resp.status_code, 204)

        # TotalCount record should now be deleted since total quantity is 0
        self.assertFalse(TotalCount.objects.filter(word="palabraprueba").exists())


class InternationalizationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='admin_i18n',
            email='admin@example.com',
            password='AdminPassword123!'
        )

    def test_default_language_is_spanish(self):
        self.client.login(username='admin_i18n', password='AdminPassword123!')
        response = self.client.get(reverse('panel'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('Panel de administración', content)
        self.assertIn('Empresas', content)
        self.assertIn('Reportes', content)

    def test_switch_language_to_english_and_render_translated_content(self):
        self.client.login(username='admin_i18n', password='AdminPassword123!')
        # Post to set_language
        setlang_url = reverse('set_language')
        response = self.client.post(setlang_url, {'language': 'en', 'next': reverse('panel')})
        self.assertEqual(response.status_code, 302)

        # Get panel with the cookie set
        panel_resp = self.client.get(reverse('panel'))
        self.assertEqual(panel_resp.status_code, 200)
        content = panel_resp.content.decode('utf-8')
        self.assertIn('Admin Panel', content)
        self.assertIn('Companies', content)
        self.assertIn('Reports', content)

    def test_switch_language_back_to_spanish(self):
        self.client.login(username='admin_i18n', password='AdminPassword123!')
        setlang_url = reverse('set_language')
        # First switch to EN
        self.client.post(setlang_url, {'language': 'en', 'next': reverse('panel')})
        # Then switch back to ES
        self.client.post(setlang_url, {'language': 'es', 'next': reverse('panel')})

        panel_resp = self.client.get(reverse('panel'))
        content = panel_resp.content.decode('utf-8')
        self.assertIn('Panel de administración', content)
        self.assertIn('Empresas', content)

    def test_all_modules_rendered_in_english(self):
        self.client.login(username='admin_i18n', password='AdminPassword123!')
        self.client.post(reverse('set_language'), {'language': 'en', 'next': reverse('panel')})

        # Landing page
        resp = self.client.get(reverse('index'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Comprehensive Audit & Contract Complexity Platform', resp.content.decode('utf-8'))

        # Companies
        resp = self.client.get(reverse('companies'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Company Directory', resp.content.decode('utf-8'))

        # Total count
        resp = self.client.get(reverse('totalcount'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Consolidated Lexical Frequency & Distribution', resp.content.decode('utf-8'))

        # Concealment detection
        resp = self.client.get(reverse('concealment_detection'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Information Concealment Detector', resp.content.decode('utf-8'))

        # Concealment history
        resp = self.client.get(reverse('concealment_history'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Concealment Audit History', resp.content.decode('utf-8'))

        # Expert lists
        resp = self.client.get(reverse('expert_lists'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Vocabularies and Control Lists', resp.content.decode('utf-8'))

        # Comparative analysis
        resp = self.client.get(reverse('comparative_analysis'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Comparative Vocabulary Analysis', resp.content.decode('utf-8'))

        # Profile
        resp = self.client.get(reverse('profile'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('User Profile', resp.content.decode('utf-8'))

        # Upload
        resp = self.client.get(reverse('upload'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Upload Individual Report (PDF)', resp.content.decode('utf-8'))

        # Users
        resp = self.client.get(reverse('users'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('User Management', resp.content.decode('utf-8'))


class WorkspaceIsolationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test_ws_user', password='password123', is_staff=True)
        self.client = Client()
        self.client.login(username='test_ws_user', password='password123')

        from Counter.models import Workspace, WorkspaceMembership
        self.ws1 = Workspace.objects.create(
            name="Espacio Corporativo",
            project_type="Corporativo",
            created_by=self.user
        )
        WorkspaceMembership.objects.create(workspace=self.ws1, user=self.user, role="admin")

        self.ws2 = Workspace.objects.create(
            name="Espacio Legal",
            project_type="Legal",
            created_by=self.user
        )
        WorkspaceMembership.objects.create(workspace=self.ws2, user=self.user, role="admin")

        # Compañías en cada workspace
        self.comp_ws1 = Company.objects.create(name="Empresa Corp 1", ruc="11111111111", workspace=self.ws1)
        self.comp_ws2 = Company.objects.create(name="Firma Legal 2", ruc="22222222222", workspace=self.ws2)

        # Reportes en cada workspace
        self.rep_ws1 = Report.objects.create(name="Reporte Corp", year=2024, company=self.comp_ws1, workspace=self.ws1, total_words=100)
        self.rep_ws2 = Report.objects.create(name="Contrato Legal", year=2024, company=self.comp_ws2, workspace=self.ws2, total_words=200)

        # Palabras de conteo
        from Counter.models import TotalCount
        TotalCount.objects.create(workspace=self.ws1, word="dividendo", quantity=25)
        TotalCount.objects.create(workspace=self.ws2, word="clausula", quantity=40)

    def test_workspaces_list_view(self):
        resp = self.client.get(reverse('workspaces_list'))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('Espacio Corporativo', content)
        self.assertIn('Espacio Legal', content)
        self.assertIn('Corporativo', content)
        self.assertIn('Legal', content)

    def test_workspace_select_and_filtering(self):
        # Seleccionar Workspace 1
        resp = self.client.get(reverse('workspace_select', args=[self.ws1.id]))
        self.assertEqual(resp.status_code, 302)
        session = self.client.session
        self.assertEqual(session.get('active_workspace_id'), self.ws1.id)

        # Ver panel de Workspace 1
        resp_panel = self.client.get(reverse('panel'))
        self.assertEqual(resp_panel.status_code, 200)
        self.assertEqual(resp_panel.context['total_reports'], 1)
        self.assertEqual(resp_panel.context['total_companies'], 1)

        # Ver empresas de Workspace 1
        resp_comp = self.client.get(reverse('companies'))
        self.assertEqual(resp_comp.status_code, 200)
        content_comp = resp_comp.content.decode('utf-8')
        self.assertIn('Empresa Corp 1', content_comp)
        self.assertNotIn('Firma Legal 2', content_comp)

        # Ver reportes de Workspace 1
        resp_rep = self.client.get(reverse('reports'))
        self.assertEqual(resp_rep.status_code, 200)
        content_rep = resp_rep.content.decode('utf-8')
        self.assertIn('Reporte Corp', content_rep)
        self.assertNotIn('Contrato Legal', content_rep)

        # Cambiar a Workspace 2
        resp = self.client.get(reverse('workspace_select', args=[self.ws2.id]))
        self.assertEqual(resp.status_code, 302)

        # Ver empresas de Workspace 2
        resp_comp2 = self.client.get(reverse('companies'))
        self.assertEqual(resp_comp2.status_code, 200)
        content_comp2 = resp_comp2.content.decode('utf-8')
        self.assertIn('Firma Legal 2', content_comp2)
        self.assertNotIn('Empresa Corp 1', content_comp2)

        # Ver reportes de Workspace 2
        resp_rep2 = self.client.get(reverse('reports'))
        self.assertEqual(resp_rep2.status_code, 200)
        content_rep2 = resp_rep2.content.decode('utf-8')
        self.assertIn('Contrato Legal', content_rep2)
        self.assertNotIn('Reporte Corp', content_rep2)

    def test_create_workspace_via_post(self):
        post_data = {
            'name': 'Auditoría Médica 2026',
            'project_type': 'Salud / Médico',
            'description': 'Análisis de historias clínicas',
            'color': 'green',
            'icon': 'medical'
        }
        resp = self.client.post(reverse('workspace_create'), post_data)
        self.assertEqual(resp.status_code, 302)

        from Counter.models import Workspace
        ws_created = Workspace.objects.filter(name='Auditoría Médica 2026').first()
        self.assertIsNotNone(ws_created)
        self.assertEqual(ws_created.project_type, 'Salud / Médico')
        self.assertEqual(ws_created.color, 'green')
        self.assertEqual(ws_created.icon, 'medical')



class ExpertListWorkspaceIsolationTests(TestCase):
    """Las listas de palabras de los expertos deben ser únicas y aisladas por espacio."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='listas_ws', password='password123', is_staff=True
        )
        self.client = Client()
        self.client.login(username='listas_ws', password='password123')

        self.ws1 = Workspace.objects.create(name='Espacio Listas 1', created_by=self.user)
        self.ws2 = Workspace.objects.create(name='Espacio Listas 2', created_by=self.user)

        expert_user = User.objects.create_user(username='expert1', password='x')
        self.expert = Expert.objects.create(user=expert_user, profession='Ingeniero')

    def _seleccionar(self, ws):
        self.client.get(reverse('workspace_select', args=[ws.id]))

    def _post_json(self, url, payload):
        return self.client.post(url, json.dumps(payload), content_type='application/json')

    def _crear(self, nombre, palabras=None):
        return self._post_json(reverse('create_expert_list'), {
            'expert_id': self.expert.id,
            'name': nombre,
            'words': palabras or ['ingresos', 'pasivos'],
        })

    def test_mismo_nombre_permitido_en_espacios_distintos(self):
        self._seleccionar(self.ws1)
        r1 = self._crear('Común')
        self.assertEqual(r1.status_code, 200, r1.content)
        self.assertTrue(r1.json()['success'])

        # Mismo nombre, otro espacio: debe permitirse
        self._seleccionar(self.ws2)
        r2 = self._crear('Común')
        self.assertEqual(r2.status_code, 200, r2.content)
        self.assertTrue(r2.json()['success'])

        self.assertEqual(ExpertWord.objects.filter(name='Común').count(), 2)

    def test_nombre_duplicado_en_el_mismo_espacio_rechazado(self):
        self._seleccionar(self.ws1)
        self.assertEqual(self._crear('Duplicada').status_code, 200)
        repetida = self._crear('Duplicada')
        self.assertEqual(repetida.status_code, 400)
        self.assertEqual(ExpertWord.objects.filter(workspace=self.ws1, name='Duplicada').count(), 1)

    def test_no_puede_leer_editar_borrar_lista_de_otro_espacio(self):
        self._seleccionar(self.ws1)
        lista_id = self._crear('Solo del ws1').json()['id']

        # Cambio al otro espacio: la lista de ws1 no debe ser visible ni manipulable
        self._seleccionar(self.ws2)
        self.assertEqual(
            self.client.get(reverse('get_list_json', args=[lista_id])).status_code, 404
        )
        self.assertEqual(
            self._post_json(reverse('update_expert_list', args=[lista_id]),
                            {'name': 'Robada', 'words': ['x']}).status_code, 404
        )
        self.assertEqual(
            self._post_json(reverse('delete_expert_list', args=[lista_id]), {}).status_code, 404
        )
        self.assertTrue(ExpertWord.objects.filter(id=lista_id, name='Solo del ws1').exists())

        # Vuelvo a ws1: sigue ahí y ahora sí se puede editar
        self._seleccionar(self.ws1)
        ok = self._post_json(reverse('update_expert_list', args=[lista_id]),
                             {'name': 'Renombrada', 'words': ['y']})
        self.assertEqual(ok.status_code, 200, ok.content)

    def test_listado_solo_muestra_listas_del_espacio_activo(self):
        self._seleccionar(self.ws1)
        self._crear('FiltroWs1')
        self._seleccionar(self.ws2)
        self._crear('FiltroWs2')

        self._seleccionar(self.ws1)
        resp = self.client.get(reverse('expert_lists'))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('FiltroWs1', content)
        self.assertNotIn('FiltroWs2', content)


class WorkspaceDeletionSafetyTests(TestCase):
    """Nunca se debe poder borrar un espacio con contenido (reportes, empresas, PDFs)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='seguridad_ws', password='password123', is_staff=True
        )
        self.client = Client()
        self.client.login(username='seguridad_ws', password='password123')

        self.ws_vacio = Workspace.objects.create(name='Espacio Vacío', created_by=self.user)
        self.ws_lleno = Workspace.objects.create(name='Espacio Lleno', created_by=self.user)

        self.company = Company.objects.create(
            workspace=self.ws_lleno, name='PROTEGIDA S.A.', ruc='0999999999001'
        )
        self.report = Report.objects.create(
            workspace=self.ws_lleno, company=self.company, name='2024', year=2024
        )
        TotalCount.objects.create(workspace=self.ws_lleno, word='ingresos', quantity=42)
        TotalCountReport.objects.create(report=self.report, word='ingresos', quantity=42)

    def _snapshot(self):
        return (
            Workspace.objects.count(), Company.objects.count(), Report.objects.count(),
            TotalCount.objects.count(), TotalCountReport.objects.count(),
        )

    def test_no_se_puede_borrar_espacio_con_contenido(self):
        antes = self._snapshot()
        resp = self.client.post(reverse('workspace_delete', args=[self.ws_lleno.id]))
        self.assertEqual(resp.status_code, 400)
        self.assertIn('reportes', resp.json()['error'])
        self.assertEqual(self._snapshot(), antes)
        self.assertTrue(Workspace.objects.filter(id=self.ws_lleno.id).exists())

    def test_el_modelo_protege_el_borrado_a_nivel_base_de_datos(self):
        antes = self._snapshot()
        with self.assertRaises(ProtectedError):
            self.ws_lleno.delete()
        self.assertEqual(self._snapshot(), antes)

    def test_se_puede_borrar_un_espacio_vacio(self):
        resp = self.client.post(reverse('workspace_delete', args=[self.ws_vacio.id]))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(Workspace.objects.filter(id=self.ws_vacio.id).exists())
        self.assertTrue(Workspace.objects.filter(id=self.ws_lleno.id).exists())

    def test_no_se_puede_borrar_el_unico_espacio_activo(self):
        # Dejo solo el ws_lleno: vacío y único → rechazado por ser el único
        self.ws_vacio.delete()
        self.ws_lleno.reports.all().delete()
        self.ws_lleno.companies.all().delete()

        resp = self.client.post(reverse('workspace_delete', args=[self.ws_lleno.id]))
        self.assertEqual(resp.status_code, 400)
        self.assertIn('único', resp.json()['error'])
        self.assertTrue(Workspace.objects.filter(id=self.ws_lleno.id).exists())

    def test_archivar_oculta_sin_borrar_y_es_reversible(self):
        antes = self._snapshot()

        resp = self.client.post(reverse('workspace_archive', args=[self.ws_lleno.id]))
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()['is_archived'])

        # Ningún dato se perdió
        self.assertEqual(self._snapshot(), antes)

        # No aparece en la lista de espacios seleccionables
        from Counter.workspace_utils import get_user_workspaces
        self.assertNotIn(self.ws_lleno, list(get_user_workspaces(self.user)))
        # Pero sí en la pantalla de gestión (para poder restaurarlo)
        self.assertIn(self.ws_lleno, list(get_user_workspaces(self.user, include_archived=True)))

        # La tarjeta se muestra con el distintivo "Archivado"
        resp_list = self.client.get(reverse('workspaces_list'))
        self.assertEqual(resp_list.status_code, 200)
        self.assertIn('Archivado', resp_list.content.decode('utf-8'))

        # Y la sesión no puede seguir apuntando a un espacio archivado
        self.assertNotEqual(
            self.client.session.get('active_workspace_id'), self.ws_lleno.id
        )

        # Restaurar
        resp_back = self.client.post(reverse('workspace_archive', args=[self.ws_lleno.id]))
        self.assertEqual(resp_back.status_code, 200)
        self.assertFalse(resp_back.json()['is_archived'])
        self.assertEqual(self._snapshot(), antes)

    def test_no_se_puede_archivar_el_unico_espacio_activo(self):
        self.ws_lleno.is_archived = True
        self.ws_lleno.save(update_fields=['is_archived'])

        resp = self.client.post(reverse('workspace_archive', args=[self.ws_vacio.id]))
        self.assertEqual(resp.status_code, 400)
        self.assertIn('único', resp.json()['error'])
        self.assertFalse(Workspace.objects.get(id=self.ws_vacio.id).is_archived)


class DenegarPorDefectoTests(TestCase):
    """Un usuario sin espacio de trabajo aprobado no ve nada del trabajo hecho."""

    PANTALLAS = [
        'panel', 'companies', 'reports', 'totalcount', 'upload',
        'concealment_detection', 'concealment_history', 'expert_lists',
        'comparative_analysis',
    ]

    def setUp(self):
        # Un espacio con datos que pertenece a otra persona (el "trabajo hecho").
        self.admin = User.objects.create_superuser(
            username='dueno_datos', password='password123'
        )
        self.ws = Workspace.objects.create(name='Espacio Ajeno', created_by=self.admin)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.admin, role='admin')
        self.company = Company.objects.create(
            workspace=self.ws, name='CONFIDENCIAL S.A.', ruc='0998888889001'
        )
        self.report = Report.objects.create(
            workspace=self.ws, company=self.company, name='2024', year=2024
        )

        # Usuario recién registrado: sin membresías.
        self.nuevo = User.objects.create_user(username='nuevo', password='password123')
        self.client = Client()
        self.client.login(username='nuevo', password='password123')

    def test_redirige_a_la_pantalla_de_espacios(self):
        for name in self.PANTALLAS:
            with self.subTest(vista=name):
                resp = self.client.get(reverse(name))
                self.assertEqual(resp.status_code, 302)
                self.assertIn('/workspaces/', resp['Location'])

    def test_no_aparece_ningun_dato_del_espacio_ajeno(self):
        resp = self.client.get(reverse('workspaces_list'))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertNotIn('CONFIDENCIAL S.A.', content)
        self.assertNotIn('Espacio Ajeno', content)
        self.assertIn('Aún no tienes acceso a ningún espacio de trabajo', content)

    @modify_settings(MIDDLEWARE={'remove': ['Counter.middleware.WorkspaceAccessGuardMiddleware']})
    def test_las_vistas_filtran_incluso_sin_el_middleware(self):
        # Segunda barrera: aunque una vista se saltara el guard, sin espacio
        # activo debe devolver listas vacías y nunca el total global.
        companies = self.client.get(reverse('companies'))
        self.assertEqual(companies.status_code, 200)
        self.assertNotIn('CONFIDENCIAL S.A.', companies.content.decode('utf-8'))

        reports = self.client.get(reverse('reports'))
        self.assertNotIn('CONFIDENCIAL S.A.', reports.content.decode('utf-8'))

        panel = self.client.get(reverse('panel'))
        self.assertEqual(panel.status_code, 200)
        self.assertEqual(panel.context['total_companies'], 0)
        self.assertEqual(panel.context['total_reports'], 0)

        totalcount = self.client.get(reverse('totalcount'))
        self.assertEqual(list(totalcount.context['total_counts']), [])
        self.assertEqual(list(totalcount.context['companies']), [])

    def test_las_peticiones_ajax_reciben_403(self):
        resp = self.client.get(
            reverse('reports_by_year') + '?year=2024',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()['detail'], 'no_active_workspace')

    def test_staff_ve_todo_sin_necesitar_aprobacion(self):
        self.client.logout()
        self.client.login(username='dueno_datos', password='password123')
        # Staff sin ningún espacio propio: sigue viendo los suyos y el ajeno.
        Workspace.objects.filter(created_by=self.admin).update(created_by=None)
        self.admin.workspace_memberships.all().delete()
        resp = self.client.get(reverse('panel'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['total_reports'], 1)

    def test_puede_acceder_a_la_pantalla_de_espacios_y_al_login(self):
        self.assertEqual(self.client.get(reverse('workspaces_list')).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('login')).status_code, 200)
        self.assertEqual(self.client.get(reverse('register')).status_code, 200)


class WorkspaceMemberManagementTests(TestCase):
    """La aprobación de acceso: el admin del espacio añade o quita usuarios."""

    def setUp(self):
        # Admin del espacio (staff): quien aprueba.
        self.admin = User.objects.create_user(
            username='admin_espacio', password='password123', is_staff=True
        )
        self.ws = Workspace.objects.create(name='Espacio Privado', created_by=self.admin)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.admin, role='admin')

        self.company = Company.objects.create(
            workspace=self.ws, name='SECRETA S.A.', ruc='0997777777001'
        )
        Report.objects.create(workspace=self.ws, company=self.company, name='2024', year=2024)

        self.solicitante = User.objects.create_user(
            username='solicitante', password='password123'
        )

        self.admin_client = Client()
        self.admin_client.login(username='admin_espacio', password='password123')
        self.user_client = Client()
        self.user_client.login(username='solicitante', password='password123')

    def _add(self, client, role='viewer', user=None, ws=None):
        return client.post(
            reverse('workspace_members_add', args=[(ws or self.ws).id]),
            json.dumps({'user_id': (user or self.solicitante).id, 'role': role}),
            content_type='application/json',
        )

    def test_antes_de_aprobar_no_ve_los_datos(self):
        resp = self.user_client.get(reverse('panel'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/workspaces/', resp['Location'])

    def test_add_da_acceso_y_remove_lo_quita(self):
        resp = self._add(self.admin_client, role='viewer')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(
            WorkspaceMembership.objects.filter(
                workspace=self.ws, user=self.solicitante, role='viewer'
            ).exists()
        )

        # Con acceso: sí ve el panel y las empresas de ese espacio.
        panel = self.user_client.get(reverse('panel'))
        self.assertEqual(panel.status_code, 200)
        self.assertEqual(panel.context['total_companies'], 1)
        companies = self.user_client.get(reverse('companies'))
        self.assertIn('SECRETA S.A.', companies.content.decode('utf-8'))

        # Al quitarlo, vuelve a no ver nada.
        resp = self.admin_client.post(
            reverse('workspace_members_remove', args=[self.ws.id]),
            json.dumps({'user_id': self.solicitante.id}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertFalse(
            WorkspaceMembership.objects.filter(
                workspace=self.ws, user=self.solicitante
            ).exists()
        )
        self.assertEqual(self.user_client.get(reverse('panel')).status_code, 302)

    def test_alguien_sin_permiso_no_gestionar_miembros(self):
        # 'solicitante' tiene acceso a OTRO espacio: pasa el guard pero no administra este.
        otro_ws = Workspace.objects.create(name='Espacio Público', created_by=self.admin)
        WorkspaceMembership.objects.create(
            workspace=otro_ws, user=self.solicitante, role='admin'
        )
        self.assertEqual(self._add(self.user_client).status_code, 403)

        # Un editor (rol medio) tampoco puede gestionar miembros.
        otro = User.objects.create_user(username='editor_espacio', password='password123')
        WorkspaceMembership.objects.create(
            workspace=self.ws, user=otro, role='editor'
        )
        editor_client = Client()
        editor_client.login(username='editor_espacio', password='password123')
        self.assertEqual(self._add(editor_client, user=self.solicitante).status_code, 403)
        self.assertEqual(
            editor_client.get(
                reverse('workspace_members', args=[self.ws.id])
            ).status_code,
            403,
        )

    def test_listado_de_miembros_y_disponibles(self):
        resp = self.admin_client.get(reverse('workspace_members', args=[self.ws.id]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        usernames = [m['username'] for m in data['members']]
        self.assertIn('admin_espacio', usernames)
        self.assertNotIn('solicitante', usernames)
        self.assertIn('solicitante', [u['username'] for u in data['available_users']])
        # El creador nunca se puede quitar a sí mismo.
        creador = next(m for m in data['members'] if m['username'] == 'admin_espacio')
        self.assertFalse(creador['puede_eliminar'])
        self.assertFalse(creador['puede_cambiar_rol'])

    def test_no_se_puede_anadir_dos_veces_ni_con_rol_invalido(self):
        self.assertEqual(self._add(self.admin_client).status_code, 200)
        self.assertEqual(self._add(self.admin_client).status_code, 400)
        self.assertEqual(self._add(self.admin_client, role='superpoder').status_code, 400)

    def test_no_se_puede_dejar_el_espacio_sin_administradores(self):
        # admin_espacio es el creador: inamovible. Se añade otro admin y se quita.
        segundo = User.objects.create_user(username='segundo_admin', password='password123')
        WorkspaceMembership.objects.create(
            workspace=self.ws, user=segundo, role='admin'
        )
        self.assertEqual(
            self._add(self.admin_client, user=self.solicitante, role='admin').status_code, 200
        )

        # Quitar al segundo admin deja al creador como único admin: permitido.
        resp = self.admin_client.post(
            reverse('workspace_members_remove', args=[self.ws.id]),
            json.dumps({'user_id': segundo.id}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        # Cambiarle el rol al creador está vetado.
        resp = self.admin_client.post(
            reverse('workspace_members_role', args=[self.ws.id]),
            json.dumps({'user_id': self.admin.id, 'role': 'viewer'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(
            WorkspaceMembership.objects.filter(
                workspace=self.ws, user=self.admin, role='admin'
            ).exists()
        )

    def test_no_puede_anadir_a_un_usuario_inactivo(self):
        inactivo = User.objects.create_user(
            username='baja', password='password123', is_active=False
        )
        resp = self._add(self.admin_client, user=inactivo)
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(
            WorkspaceMembership.objects.filter(workspace=self.ws, user=inactivo).exists()
        )

    def test_el_boton_de_miembros_solo_aparece_para_el_admin(self):
        resp = self.admin_client.get(reverse('workspaces_list'))
        content = resp.content.decode('utf-8')
        self.assertIn('onclick="openMembersModal(', content)

        WorkspaceMembership.objects.create(
            workspace=self.ws, user=self.solicitante, role='viewer'
        )
        resp = self.user_client.get(reverse('workspaces_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('onclick="openMembersModal(', resp.content.decode('utf-8'))
