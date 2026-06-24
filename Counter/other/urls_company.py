from django.urls import path
from ..views import company_views as views

urlpatterns = [
    path("", views.company_view, name="companies"),
    path("create/", views.create_company, name="create_company"),
    path("<int:company_id>/json/", views.see_company_json, name="see_company_json"),
    path("<int:company_id>/delete/", views.delete_company, name="delete_company"),
    path("<int:company_id>/update/", views.update_company, name="update_company"),
]
