from django.urls import path
from ..views import concealment_detection_views as views

urlpatterns = [
    path("", views.concealment_detection_view, name="concealment_detection"),
    path("ajax/report-words/", views.get_report_words, name="get_report_words"),
    path("ajax/reports-by-year/", views.get_reports_by_year, name="get_reports_by_year"),
    path("historial/", views.concealment_history_view, name="concealment_history"),
    path("historial/<int:review_id>/detalle/", views.concealment_history_detail_ajax, name="concealment_history_detail"),
]
