from django.urls import path
from ..views import total_count_report_views as views

urlpatterns = [
    path("", views.total_count_report_view, name='report_count'),
]



