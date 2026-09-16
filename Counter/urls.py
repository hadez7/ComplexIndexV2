from django.urls import path, include
from .views import general_views as views

urlpatterns = [
    # Main views
    path("", views.index_view, name="index"),
    path("panel/", views.panel_view, name="panel"),
    path("upload/", views.upload_view, name="upload"),
    path("comparative_analysis/", views.comparative_analysis_view, name="comparative_analysis"),
    path("users/", views.user_view, name="users"),
    path("users/create/", views.create_user, name="users_create"),
    path("users/update/", views.update_user, name="users_update"),
    path("users/<int:user_id>/toggle-active/", views.toggle_user_active, name="users_toggle_active"),
    path("users/<int:user_id>/expert/", views.assign_expert, name="users_assign_expert"),
    path("reports-by-year/", views.reports_by_year, name="reports_by_year"),
    
    # Included URLConfs
    path("totalcount/", include("Counter.other.urls_total_count")),
    path("companies/", include("Counter.other.urls_company")),
    path("reports/", include("Counter.other.urls_report")),
    path("expert_lists/", include("Counter.other.urls_expert_lists")),
    path("concealment_detection/", include("Counter.other.urls_concealment_detection")),
]

