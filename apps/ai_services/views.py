"""
Views for AI services - Disease prediction, feedback, and ML dashboard.
"""
import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Count, Q, F
from django.utils import timezone

from apps.accounts.models import User
from apps.appointments.models import Appointment
from .services import (
    get_patient_risk_score, calculate_wait_time,
    detect_outbreak_risk, get_disease_trend_data,
)
from .models import TrainingData, MLModelVersion, PredictionLog


@login_required
def patient_risk_api(request, patient_id):
    """API endpoint for patient risk score."""
    patient = get_object_or_404(User, pk=patient_id, role=User.Role.PATIENT)
    risk = get_patient_risk_score(patient)

    if risk:
        return JsonResponse(risk)
    return JsonResponse({'error': 'Could not calculate risk'}, status=500)


@login_required
def wait_time_api(request, appointment_id):
    """API endpoint for wait time estimation."""
    appointment = get_object_or_404(Appointment, pk=appointment_id)
    wait_time = calculate_wait_time(appointment)

    return JsonResponse({'estimated_wait': wait_time})


@login_required
def disease_prediction_view(request):
    """
    Disease prediction form for doctors.
    Doctor enters symptoms + demographics -> ML model predicts disease.
    """
    if not request.user.is_doctor and not request.user.is_admin:
        messages.error(request, 'Access denied. Only doctors can use disease prediction.')
        return redirect('accounts:dashboard')

    from .ml_pipeline import ALL_SYMPTOMS, predict_disease, HAS_ML

    prediction_result = None
    form_data = {}

    if request.method == 'POST':
        # Collect form data
        symptoms_list = request.POST.getlist('symptoms')
        custom_symptoms = request.POST.get('custom_symptoms', '').strip()
        age = int(request.POST.get('age', 0))
        gender = request.POST.get('gender', 'other')
        bp_sys = request.POST.get('bp_systolic')
        bp_dia = request.POST.get('bp_diastolic')
        heart_rate = request.POST.get('heart_rate')
        temperature = request.POST.get('temperature')
        spo2 = request.POST.get('spo2')
        patient_id = request.POST.get('patient_id')

        # Combine selected symptoms with custom
        all_symptoms = list(symptoms_list)
        if custom_symptoms:
            all_symptoms.extend([s.strip().lower().replace(' ', '_')
                                for s in custom_symptoms.split(',')])

        symptom_string = ','.join(all_symptoms)

        form_data = {
            'symptoms': symptoms_list,
            'custom_symptoms': custom_symptoms,
            'age': age,
            'gender': gender,
            'bp_systolic': bp_sys,
            'bp_diastolic': bp_dia,
            'heart_rate': heart_rate,
            'temperature': temperature,
            'spo2': spo2,
            'patient_id': patient_id,
            'symptom_string': symptom_string,
        }

        # Get ML prediction
        prediction_result = predict_disease(
            symptom_string, age, gender,
            int(bp_sys) if bp_sys else None,
            int(bp_dia) if bp_dia else None,
            int(heart_rate) if heart_rate else None,
            float(temperature) if temperature else None,
            int(spo2) if spo2 else None,
        )

        # Also get rule-based suggestions as fallback
        from .services import get_ai_diagnosis_suggestions
        rule_suggestions = get_ai_diagnosis_suggestions(all_symptoms)

        if prediction_result:
            # Log the prediction
            active_version = MLModelVersion.objects.filter(is_active=True).first()
            preds = prediction_result['predictions']
            PredictionLog.objects.create(
                patient_id=patient_id if patient_id else None,
                symptoms_input=symptom_string,
                patient_age=age,
                patient_gender=gender,
                prediction_1=preds[0]['disease'] if len(preds) > 0 else '',
                confidence_1=preds[0]['confidence'] / 100 if len(preds) > 0 else 0,
                prediction_2=preds[1]['disease'] if len(preds) > 1 else '',
                confidence_2=preds[1]['confidence'] / 100 if len(preds) > 1 else None,
                prediction_3=preds[2]['disease'] if len(preds) > 2 else '',
                confidence_3=preds[2]['confidence'] / 100 if len(preds) > 2 else None,
                model_version=active_version,
                predicted_by=request.user,
            )
        else:
            # Use rule-based as the result
            prediction_result = {
                'predictions': [
                    {
                        'disease': s['diagnosis'],
                        'confidence': s['confidence'],
                        'icd_code': s['icd_code'],
                    }
                    for s in rule_suggestions[:3]
                ],
                'model_version': 'Rule-based (no ML model trained yet)',
                'model_accuracy': None,
            }

    # Get available patients for the dropdown
    patients = User.objects.filter(role=User.Role.PATIENT, is_active=True).order_by('first_name')

    # Group symptoms by category for the form
    symptom_categories = {
        'General': ['fever', 'fatigue', 'chills', 'night_sweats', 'weight_loss',
                     'weight_gain', 'loss_of_appetite'],
        'Head & Neurological': ['headache', 'dizziness', 'confusion', 'memory_loss',
                                 'seizures', 'tremor', 'blurred_vision', 'insomnia'],
        'Respiratory': ['cough', 'shortness_of_breath', 'wheezing', 'chest_tightness',
                         'runny_nose', 'sneezing', 'nasal_congestion'],
        'Cardiovascular': ['chest_pain', 'palpitations', 'swelling'],
        'Gastrointestinal': ['nausea', 'vomiting', 'diarrhea', 'abdominal_pain',
                              'constipation', 'bloating', 'blood_in_stool'],
        'Musculoskeletal': ['joint_pain', 'back_pain', 'muscle_weakness', 'numbness', 'tingling'],
        'ENT': ['sore_throat', 'ear_pain', 'difficulty_swallowing', 'hoarseness'],
        'Skin': ['skin_rash', 'itching', 'dry_skin', 'bruising', 'hair_loss'],
        'Urinary': ['frequent_urination', 'painful_urination', 'blood_in_urine',
                     'dark_urine', 'excessive_thirst'],
        'Psychological': ['anxiety', 'depression'],
        'Other': ['eye_redness', 'eye_pain', 'jaundice', 'pale_stool',
                   'bleeding_gums'],
    }

    active_model = MLModelVersion.objects.filter(is_active=True).first()

    return render(request, 'ai_services/predict.html', {
        'symptom_categories': symptom_categories,
        'patients': patients,
        'prediction_result': prediction_result,
        'form_data': form_data,
        'active_model': active_model,
        'has_ml': HAS_ML,
    })


@login_required
def confirm_diagnosis_api(request):
    """
    API endpoint for doctor to confirm or correct a prediction.
    Saves as labeled training data and triggers retraining if threshold met.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    if not request.user.is_doctor and not request.user.is_admin:
        return JsonResponse({'error': 'Access denied'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    symptoms = data.get('symptoms', '')
    age = data.get('age', 0)
    gender = data.get('gender', 'other')
    confirmed_disease = data.get('confirmed_disease', '')
    icd_code = data.get('icd_code', '')
    predicted_disease = data.get('predicted_disease', '')
    predicted_confidence = data.get('predicted_confidence')
    patient_id = data.get('patient_id')

    # Vitals
    bp_sys = data.get('bp_systolic')
    bp_dia = data.get('bp_diastolic')
    heart_rate = data.get('heart_rate')
    temperature = data.get('temperature')
    spo2 = data.get('spo2')

    if not symptoms or not confirmed_disease:
        return JsonResponse({'error': 'Symptoms and confirmed disease are required'}, status=400)

    from .ml_pipeline import save_training_data

    active_version = MLModelVersion.objects.filter(is_active=True).first()

    # Resolve patient object from ID
    patient_obj = None
    if patient_id:
        patient_obj = User.objects.filter(pk=patient_id, role=User.Role.PATIENT).first()

    record, retrained = save_training_data(
        symptoms=symptoms,
        age=age,
        gender=gender,
        confirmed_disease=confirmed_disease,
        icd_code=icd_code,
        predicted_disease=predicted_disease,
        predicted_confidence=predicted_confidence,
        doctor=request.user,
        patient=patient_obj,
        model_version=active_version,
        bp_sys=bp_sys,
        bp_dia=bp_dia,
        heart_rate=heart_rate,
        temperature=temperature,
        spo2=spo2,
    )

    # Check pending count for next retrain
    from .ml_pipeline import check_retrain_needed, RETRAIN_THRESHOLD
    _, pending_count = check_retrain_needed()

    response = {
        'status': 'saved',
        'training_data_id': record.id,
        'prediction_correct': record.prediction_correct,
        'retrained': retrained,
        'pending_for_retrain': pending_count,
        'retrain_threshold': RETRAIN_THRESHOLD,
    }

    if retrained:
        new_model = MLModelVersion.objects.filter(is_active=True).first()
        response['new_model'] = {
            'version': new_model.version,
            'accuracy': round(new_model.accuracy * 100, 1),
        }

    return JsonResponse(response)


@login_required
def ml_dashboard(request):
    """
    ML model performance dashboard.
    Shows accuracy over time, training data stats, and model versions.
    """
    if not request.user.is_doctor and not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    # Model versions
    model_versions = MLModelVersion.objects.all()[:20]

    # Active model
    active_model = MLModelVersion.objects.filter(is_active=True).first()

    # Training data stats
    total_training = TrainingData.objects.count()
    pending_training = TrainingData.objects.filter(used_for_training=False).count()
    correct_predictions = TrainingData.objects.filter(prediction_correct=True).count()
    prediction_accuracy = (correct_predictions / total_training * 100) if total_training > 0 else 0

    # Disease distribution in training data
    disease_distribution = list(
        TrainingData.objects.values('confirmed_disease')
        .annotate(count=Count('id'))
        .order_by('-count')[:15]
    )

    # Accuracy over versions for chart
    accuracy_history = list(
        MLModelVersion.objects.order_by('trained_at')
        .values('version', 'accuracy', 'training_samples', 'trained_at')
    )
    for item in accuracy_history:
        item['accuracy_pct'] = round(item['accuracy'] * 100, 1)
        item['trained_at'] = item['trained_at'].strftime('%Y-%m-%d %H:%M')

    # Recent predictions
    recent_predictions = PredictionLog.objects.select_related(
        'model_version', 'predicted_by'
    )[:10]

    # Prediction correctness rate by model version
    version_performance = list(
        TrainingData.objects.filter(model_version__isnull=False)
        .values('model_version__version')
        .annotate(
            total=Count('id'),
            correct=Count('id', filter=Q(prediction_correct=True)),
        )
        .order_by('model_version__version')
    )

    from .ml_pipeline import RETRAIN_THRESHOLD

    # Evaluation chart data for the active model
    confusion_matrix_data = active_model.confusion_matrix if active_model else '[]'
    class_labels_data = active_model.class_labels if active_model else '[]'
    feature_importances_data = active_model.feature_importances if active_model else '[]'
    per_class_metrics_data = active_model.per_class_metrics if active_model else '[]'

    # Outbreak / epidemic surveillance
    outbreak_alerts  = detect_outbreak_risk()
    disease_trend_js = json.dumps(get_disease_trend_data(30))

    return render(request, 'ai_services/ml_dashboard.html', {
        'model_versions': model_versions,
        'active_model': active_model,
        'total_training': total_training,
        'pending_training': pending_training,
        'correct_predictions': correct_predictions,
        'prediction_accuracy': round(prediction_accuracy, 1),
        'disease_distribution': disease_distribution,
        'accuracy_history': json.dumps(accuracy_history),
        'recent_predictions': recent_predictions,
        'version_performance': version_performance,
        'retrain_threshold': RETRAIN_THRESHOLD,
        'confusion_matrix_data': confusion_matrix_data,
        'class_labels_data': class_labels_data,
        'feature_importances_data': feature_importances_data,
        'per_class_metrics_data': per_class_metrics_data,
        'outbreak_alerts': outbreak_alerts,
        'disease_trend_js': disease_trend_js,
    })


@login_required
def trigger_retrain(request):
    """Manually trigger model retraining."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    if not request.user.is_admin and not request.user.is_doctor:
        return JsonResponse({'error': 'Access denied'}, status=403)

    from .ml_pipeline import train_model

    try:
        new_model = train_model(triggered_by=request.user)
        messages.success(
            request,
            f"Model {new_model.version} trained successfully! "
            f"Accuracy: {new_model.accuracy:.1%}"
        )
    except Exception as e:
        messages.error(request, f"Training failed: {str(e)}")

    return redirect('ai_services:ml_dashboard')
