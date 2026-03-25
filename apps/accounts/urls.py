"""
URL patterns for accounts app.
"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # Profile
    path('profile/', views.profile_view, name='profile'),

    # Role-specific dashboards
    path('dashboard/patient/', views.patient_dashboard, name='patient_dashboard'),
    path('dashboard/doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('dashboard/receptionist/', views.receptionist_dashboard, name='receptionist_dashboard'),
    path('dashboard/pharmacist/', views.pharmacist_dashboard, name='pharmacist_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),

    # Admin user management
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.user_create_view, name='user_create'),
    path('users/<int:pk>/edit/', views.user_update_view, name='user_edit'),

    # Department management
    path('departments/', views.DepartmentListView.as_view(), name='department_list'),
    path('departments/<int:dept_id>/', views.manage_department, name='manage_department'),
    path('departments/<int:dept_id>/assign-doctor/', views.assign_doctor_to_department, name='assign_doctor'),

    # Audit logs
    path('audit-logs/', views.AuditLogListView.as_view(), name='audit_logs'),
]
