from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from Counter.models import Company, Report, TotalCountReport, ConcealmentReview, ConcealmentParagraphReview


class ConcealmentDetectionFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testauditor', password='password123')
        self.client = Client()
        self.client.login(username='testauditor', password='password123')

        self.company1 = Company.objects.create(name='EMPRESA ALFA S.A.', ruc='0990000001001')
        self.company2 = Company.objects.create(name='EMPRESA BETA S.A.', ruc='0990000002001')

        self.report1 = Report.objects.create(
            company=self.company1,
            name='2024',
            year=2024
        )
        self.report2 = Report.objects.create(
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
        company_z = Company.objects.create(name=' ZETA S.A.', ruc='0990000003001')
        report_z = Report.objects.create(company=company_z, name='2024', year=2024)

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
        self.company = Company.objects.create(name='ACME CORP S.A.', ruc='0990000004001')
        self.report = Report.objects.create(
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
        form = ComparativeAnalysisForm(data={'year': '2024'})
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
        self.company1 = Company.objects.create(name='ALPHA LOGISTICS S.A.', ruc='0990000005001')
        self.company2 = Company.objects.create(name='OMEGA HOLDINGS S.A.', ruc='0990000006001')
        self.rep1 = Report.objects.create(company=self.company1, name='Memoria Anual 2024', year=2024)
        self.rep2 = Report.objects.create(company=self.company2, name='Balance 2023', year=2023)

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
        self.company = Company.objects.create(name='BETA CORP S.A.', ruc='0990000007001')

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
            files={"file": fake_txt}
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
            files={"file": fake_pdf}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)

    def test_form_detects_duplicate_company_year_without_overwrite(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from Counter.forms import IndividualReportUploadForm

        # Create existing report
        Report.objects.create(company=self.company, year=2024, name="Existente 2024")

        valid_pdf_content = b"%PDF-1.4\n%trailer\n%%EOF"
        pdf_file = SimpleUploadedFile("nuevo.pdf", valid_pdf_content, content_type="application/pdf")

        form = IndividualReportUploadForm(
            data={"company": self.company.id, "year": 2024, "overwrite": False},
            files={"file": pdf_file}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("Ya existe un reporte registrado", str(form.errors))

    def test_form_allows_duplicate_company_year_with_overwrite(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from Counter.forms import IndividualReportUploadForm

        Report.objects.create(company=self.company, year=2024, name="Existente 2024")

        valid_pdf_content = b"%PDF-1.4\n%trailer\n%%EOF"
        pdf_file = SimpleUploadedFile("nuevo.pdf", valid_pdf_content, content_type="application/pdf")

        form = IndividualReportUploadForm(
            data={"company": self.company.id, "year": 2024, "overwrite": True},
            files={"file": pdf_file}
        )
        self.assertTrue(form.is_valid())

    def test_delete_report_decrements_total_count(self):
        from Counter.models import TotalCount, TotalCountReport

        report = Report.objects.create(company=self.company, year=2024, name="Reporte Prueba")
        TotalCountReport.objects.create(report=report, word="palabraprueba", quantity=15)
        TotalCount.objects.create(word="palabraprueba", quantity=15)

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

