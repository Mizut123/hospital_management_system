"""
Models for the AI/ML continuous learning system.

Stores training data, model versions, and prediction logs for
the supervised disease prediction pipeline.
"""
from django.db import models
from django.conf import settings


class TrainingData(models.Model):
    """
    Labeled training data for disease prediction.
    Each record = one confirmed symptom-diagnosis pair from a doctor.
    """
    # Patient demographics
    patient_age = models.IntegerField()
    patient_gender = models.CharField(max_length=10, choices=[
        ('male', 'Male'), ('female', 'Female'), ('other', 'Other')
    ])

    # Vital signs
    blood_pressure_systolic = models.IntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.IntegerField(null=True, blank=True)
    heart_rate = models.IntegerField(null=True, blank=True)
    temperature = models.FloatField(null=True, blank=True, help_text="Body temperature in Celsius")
    spo2 = models.IntegerField(null=True, blank=True, help_text="Oxygen saturation %")

    # Symptoms (stored as comma-separated normalized keywords)
    symptoms = models.TextField(help_text="Comma-separated symptom keywords")

    # ML prediction vs doctor's confirmed diagnosis
    predicted_disease = models.CharField(max_length=200, blank=True,
                                         help_text="What the ML model predicted")
    predicted_confidence = models.FloatField(null=True, blank=True)
    confirmed_disease = models.CharField(max_length=200,
                                         help_text="Doctor's confirmed/corrected diagnosis")
    icd_code = models.CharField(max_length=20, blank=True, help_text="ICD-10 code")

    # Whether the ML prediction matched the doctor's diagnosis
    prediction_correct = models.BooleanField(default=False)

    # Metadata
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                               null=True, related_name='training_confirmations')
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                null=True, blank=True, related_name='training_records')
    model_version = models.ForeignKey('MLModelVersion', on_delete=models.SET_NULL,
                                      null=True, blank=True,
                                      help_text="Model version used for prediction")
    used_for_training = models.BooleanField(default=False,
                                            help_text="Whether this record has been used in training")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Training Data'
        verbose_name_plural = 'Training Data'

    def __str__(self):
        return f"{self.symptoms[:50]} -> {self.confirmed_disease}"


class MLModelVersion(models.Model):
    """
    Tracks each trained version of the disease prediction model.
    Stores accuracy metrics and metadata for version control.
    """
    version = models.CharField(max_length=20, unique=True, help_text="e.g. v1.0, v1.1")
    accuracy = models.FloatField(help_text="Test accuracy 0.0 - 1.0")
    precision = models.FloatField(null=True, blank=True)
    recall = models.FloatField(null=True, blank=True)
    f1_score = models.FloatField(null=True, blank=True)
    training_samples = models.IntegerField(help_text="Number of samples used for training")
    test_samples = models.IntegerField(default=0)
    num_classes = models.IntegerField(default=0, help_text="Number of disease classes")
    feature_count = models.IntegerField(default=0, help_text="Number of features used")
    model_file = models.CharField(max_length=255, help_text="Path to serialized model file")
    is_active = models.BooleanField(default=False, help_text="Currently active model")
    notes = models.TextField(blank=True)

    # Evaluation data stored as JSON
    confusion_matrix = models.TextField(blank=True, help_text="JSON: confusion matrix")
    class_labels = models.TextField(blank=True, help_text="JSON: class label names")
    feature_importances = models.TextField(blank=True, help_text="JSON: feature importance scores")
    per_class_metrics = models.TextField(blank=True, help_text="JSON: per-class P/R/F1")
    trained_at = models.DateTimeField(auto_now_add=True)
    trained_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True)

    class Meta:
        ordering = ['-trained_at']
        verbose_name = 'ML Model Version'
        verbose_name_plural = 'ML Model Versions'

    def __str__(self):
        return f"{self.version} - Accuracy: {self.accuracy:.1%} ({self.training_samples} samples)"


class PredictionLog(models.Model):
    """
    Logs every prediction made by the ML model for auditing and analysis.
    """
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                null=True, blank=True)
    symptoms_input = models.TextField()
    patient_age = models.IntegerField(null=True, blank=True)
    patient_gender = models.CharField(max_length=10, blank=True)

    # Prediction results (top 3)
    prediction_1 = models.CharField(max_length=200)
    confidence_1 = models.FloatField()
    prediction_2 = models.CharField(max_length=200, blank=True)
    confidence_2 = models.FloatField(null=True, blank=True)
    prediction_3 = models.CharField(max_length=200, blank=True)
    confidence_3 = models.FloatField(null=True, blank=True)

    model_version = models.ForeignKey(MLModelVersion, on_delete=models.SET_NULL, null=True)
    feedback_received = models.BooleanField(default=False,
                                            help_text="Whether doctor confirmed/corrected")
    predicted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, related_name='predictions_made')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.prediction_1} ({self.confidence_1:.0%}) - {self.created_at.strftime('%Y-%m-%d')}"
