from django.urls import path, include
from ..views import report_views as views

urlpatterns = [
    path("", views.report_view, name="reports"),
    path("<int:report_id>/json/", views.see_report_json, name="see_report_json"),
    path("<int:report_id>/delete/", views.delete_report, name="delete_report"),
    path("<int:report_id>/update/", views.update_report, name="update_report"),
    path('<int:report_id>/report_count/', include('Counter.other.urls_total_count_report'), name='report_count'),
    path("total_count/", include("Counter.other.urls_total_count")),
]
