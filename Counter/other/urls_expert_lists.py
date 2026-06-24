from django.urls import path
from ..views import expert_list_views as views

urlpatterns = [
    path("", views.expert_list_view, name="expert_lists"),
    path("create/", views.create_list, name="create_expert_list"),
    path("<int:list_id>/json/", views.get_list_json, name="get_list_json"),
    path("<int:list_id>/update/", views.update_list, name="update_expert_list"),
    path("<int:list_id>/delete/", views.delete_list, name="delete_expert_list"),
    path("expert/create/", views.create_expert, name="create_expert"),
]


