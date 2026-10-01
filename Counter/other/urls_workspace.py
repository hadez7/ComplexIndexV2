from django.urls import path
from ..views import workspace_views

urlpatterns = [
    path("", workspace_views.workspace_list_view, name="workspaces_list"),
    path("create/", workspace_views.workspace_create_view, name="workspace_create"),
    path("<int:workspace_id>/select/", workspace_views.workspace_select_view, name="workspace_select"),
    path("<int:workspace_id>/update/", workspace_views.workspace_update_view, name="workspace_update"),
    path("<int:workspace_id>/delete/", workspace_views.workspace_delete_view, name="workspace_delete"),
]
