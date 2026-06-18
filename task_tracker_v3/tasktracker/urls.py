from django.urls import path
from . import views
from . import api_views

urlpatterns = [
    # ── Web Views ──
    path('', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('punch-in/', views.punch_in, name='punch_in'),
    path('punch-out/', views.punch_out, name='punch_out'),
    path('tasks/create/', views.create_task, name='create_task'),
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('tasks/<int:task_id>/submit/', views.submit_task, name='submit_task'),
    path('tasks/<int:task_id>/status/', views.update_task_status, name='update_task_status'),
    path('grammar-check/', views.grammar_check, name='grammar_check'),
    path('attendance/', views.attendance_report, name='attendance_report'),
    path('projects/', views.projects_view, name='projects'),
    path('projects/create/', views.create_project, name='create_project'),
    path('projects/<int:project_id>/', views.project_detail_view, name='project_detail'),

    # ── REST APIs ──
    path('api/signup/', api_views.api_signup, name='api_signup'),
    path('api/login/', api_views.api_login, name='api_login'),
    path('api/me/', api_views.api_me, name='api_me'),
    path('api/dashboard/', api_views.api_dashboard, name='api_dashboard'),
    path('api/projects/', api_views.api_projects, name='api_projects'),
    path('api/projects/<int:pk>/', api_views.api_project_detail, name='api_project_detail'),
    path('api/tasks/', api_views.api_tasks, name='api_tasks'),
    path('api/tasks/<int:pk>/', api_views.api_task_detail, name='api_task_detail'),
    path('api/attendance/', api_views.api_attendance, name='api_attendance'),
    path('api/punch-in/', api_views.api_punch_in, name='api_punch_in'),
    path('api/punch-out/', api_views.api_punch_out, name='api_punch_out'),
]
