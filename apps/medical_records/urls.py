"""
URL patterns for medical records app.
"""
from django.urls import path
from . import views

app_name = 'medical_records'

urlpatterns = [
    path('my/', views.my_records, name='my_records'),
    path('my/prescriptions/', views.my_prescriptions, name='my_prescriptions'),
    path('doctor/', views.doctor_records, name='doctor_records'),
    path('<int:pk>/', views.RecordDetailView.as_view(), name='detail'),
    path('create/', views.create_record, name='create'),
    path('create/<int:appointment_id>/', views.create_record, name='create'),
    path('prescription/create/', views.create_prescription, name='create_prescription'),
    path('prescription/create/<int:record_id>/', views.create_prescription, name='create_prescription'),

    # AI-powered APIs
    path('api/diagnosis-suggestions/', views.ai_diagnosis_api, name='ai_diagnosis_api'),
    path('api/symptom-keywords/', views.symptom_keywords_api, name='symptom_keywords_api'),
]
