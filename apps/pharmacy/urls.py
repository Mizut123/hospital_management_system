"""
URL patterns for pharmacy app.
"""
from django.urls import path
from . import views

app_name = 'pharmacy'

urlpatterns = [
    # Prescriptions
    path('prescriptions/', views.prescriptions_queue, name='prescriptions'),
    path('prescriptions/<int:pk>/dispense/', views.dispense_prescription, name='dispense'),

    # Medicines
    path('medicines/', views.medicines_list, name='medicines'),
    path('medicines/add/', views.add_medicine, name='add_medicine'),
    path('medicines/<int:pk>/edit/', views.edit_medicine, name='edit_medicine'),

    # Stock Management
    path('stock/', views.stock_management, name='stock'),
    path('stock/add/', views.add_stock, name='add_stock'),
    path('stock/<int:pk>/edit/', views.edit_stock, name='edit_stock'),
    path('stock/<int:pk>/adjust/', views.adjust_stock, name='adjust_stock'),
    path('stock/transactions/', views.stock_transactions, name='transactions'),
    path('stock/<int:pk>/transactions/', views.stock_transactions, name='stock_transactions'),

    # Alerts
    path('alerts/', views.stock_alerts, name='alerts'),

    # API Endpoints
    path('api/stock-check/<int:medicine_id>/', views.check_stock_api, name='check_stock_api'),
    path('api/medicine-search/', views.medicine_search_api, name='medicine_search_api'),
]
