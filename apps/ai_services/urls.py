"""
URL patterns for AI services app.
"""
from django.urls import path
from . import views

app_name = 'ai_services'

urlpatterns = [
    path('risk/<int:patient_id>/', views.patient_risk_api, name='patient_risk'),
    path('wait-time/<int:appointment_id>/', views.wait_time_api, name='wait_time'),

    # Disease Prediction (ML)
    path('predict/', views.disease_prediction_view, name='predict'),
    path('confirm-diagnosis/', views.confirm_diagnosis_api, name='confirm_diagnosis'),

    # ML Dashboard & Retraining
    path('ml-dashboard/', views.ml_dashboard, name='ml_dashboard'),
    path('retrain/', views.trigger_retrain, name='retrain'),
]
