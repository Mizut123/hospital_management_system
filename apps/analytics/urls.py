"""
URL patterns for analytics app.
"""
from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('', views.analytics_dashboard, name='dashboard'),
    path('reports/', views.reports, name='reports'),
    path('reports/download/<str:report_type>/', views.download_report, name='download_report'),
    path('stock-forecast/', views.stock_forecast_view, name='stock_forecast'),
]
