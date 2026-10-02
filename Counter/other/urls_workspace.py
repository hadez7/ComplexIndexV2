from django.urls import path
from ..views import workspace_views

urlpatterns = [
    path("", workspace_views.workspace_list_view, name="workspaces_list"),
    path("create/", workspace_views.workspace_create_view, name="workspace_create"),
    path("<int:workspace_id>/select/", workspace_views.workspace_select_view, name="workspace_select"),
    path("<int:workspace_id>/update/", workspace_views.workspace_update_view, name="workspace_update"),
    path("<int:workspace_id>/archive/", workspace_views.workspace_archive_view, name="workspace_archive"),
    path("<int:workspace_id>/delete/", workspace_views.workspace_delete_view, name="workspace_delete"),
    # Miembros: quién tiene (o deja de tener) acceso a los datos del espacio.
    path("<int:workspace_id>/members/", workspace_views.workspace_members_view, name="workspace_members"),
    path("<int:workspace_id>/members/add/", workspace_views.workspace_members_add_view, name="workspace_members_add"),
    path("<int:workspace_id>/members/remove/", workspace_views.workspace_members_remove_view, name="workspace_members_remove"),
    path("<int:workspace_id>/members/role/", workspace_views.workspace_members_role_view, name="workspace_members_role"),
]
