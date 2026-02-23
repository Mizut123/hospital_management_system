"""
Admin configuration for AI services models.
"""
from django.contrib import admin
from .models import TrainingData, MLModelVersion, PredictionLog


@admin.register(TrainingData)
class TrainingDataAdmin(admin.ModelAdmin):
    list_display = [
        'symptoms_short', 'confirmed_disease', 'predicted_disease',
        'prediction_correct', 'patient_age', 'patient_gender',
        'used_for_training', 'created_at'
    ]
    list_filter = ['prediction_correct', 'used_for_training', 'patient_gender', 'created_at']
    search_fields = ['symptoms', 'confirmed_disease', 'predicted_disease']
    readonly_fields = ['created_at']

    def symptoms_short(self, obj):
        return obj.symptoms[:60] + '...' if len(obj.symptoms) > 60 else obj.symptoms
    symptoms_short.short_description = 'Symptoms'


@admin.register(MLModelVersion)
class MLModelVersionAdmin(admin.ModelAdmin):
    list_display = [
        'version', 'accuracy_pct', 'precision', 'recall', 'f1_score',
        'training_samples', 'num_classes', 'is_active', 'trained_at'
    ]
    list_filter = ['is_active', 'trained_at']
    search_fields = ['version', 'notes']
    readonly_fields = ['trained_at']

    def accuracy_pct(self, obj):
        return f"{obj.accuracy:.1%}"
    accuracy_pct.short_description = 'Accuracy'


@admin.register(PredictionLog)
class PredictionLogAdmin(admin.ModelAdmin):
    list_display = [
        'prediction_1', 'confidence_display', 'symptoms_short',
        'model_version', 'feedback_received', 'predicted_by', 'created_at'
    ]
    list_filter = ['feedback_received', 'created_at']
    search_fields = ['prediction_1', 'symptoms_input']
    readonly_fields = ['created_at']

    def confidence_display(self, obj):
        return f"{obj.confidence_1:.0%}"
    confidence_display.short_description = 'Confidence'

    def symptoms_short(self, obj):
        return obj.symptoms_input[:60] + '...' if len(obj.symptoms_input) > 60 else obj.symptoms_input
    symptoms_short.short_description = 'Symptoms'
