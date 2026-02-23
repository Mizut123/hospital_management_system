"""
URL patterns for patients app.
"""
from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('', views.PatientListView.as_view(), name='list'),
    path('register/', views.register_patient, name='register'),
    path('search/', views.search_patients, name='search'),
    path('<int:pk>/', views.PatientDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.patient_profile, name='edit'),

    # API endpoints
    path('api/symptom-chatbot/', views.symptom_chatbot_api, name='symptom_chatbot_api'),
    path('api/scan-id/', views.scan_id_card_api, name='scan_id_api'),
    path('api/scan-id/learn/', views.scan_id_learn_api, name='scan_id_learn_api'),
    path('api/scan-id/save-profile/', views.save_card_profile_api, name='save_card_profile_api'),
]
