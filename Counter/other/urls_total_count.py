from django.urls import path
from ..views import total_count_views as views

urlpatterns = [
    path("", views.total_count_view, name="totalcount"),
    path("export_excel/", views.export_total_count_excel, name="export_excel"),
]