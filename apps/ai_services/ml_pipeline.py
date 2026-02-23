"""
Machine Learning Pipeline for Disease Prediction.

Implements a continuous supervised learning system using Random Forest:
- Feature encoding (symptoms → multi-hot vector, demographics → numeric)
- Model training with train/test split
- Prediction with confidence scores
- Auto-retraining after 50 new confirmed cases
- Model version control with accuracy tracking
"""
import json
import os
import logging
from datetime import datetime
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# ML imports
try:
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        confusion_matrix, classification_report
    )
    from sklearn.preprocessing import LabelEncoder
    import joblib
    HAS_ML = True
except ImportError:
    HAS_ML = False
    logger.warning("scikit-learn/joblib not installed. ML features disabled.")

# Directory for saved models
MODEL_DIR = os.path.join(settings.BASE_DIR, 'ml_models')
os.makedirs(MODEL_DIR, exist_ok=True)

# Retraining threshold
RETRAIN_THRESHOLD = 50

# All recognized symptoms for feature encoding
ALL_SYMPTOMS = [
    'fever', 'headache', 'cough', 'chest_pain', 'abdominal_pain',
    'fatigue', 'shortness_of_breath', 'nausea', 'diarrhea', 'joint_pain',
    'skin_rash', 'dizziness', 'sore_throat', 'back_pain', 'vomiting',
    'weight_loss', 'weight_gain', 'muscle_weakness', 'blurred_vision',
    'frequent_urination', 'excessive_thirst', 'swelling', 'numbness',
    'tingling', 'palpitations', 'chest_tightness', 'wheezing',
    'runny_nose', 'sneezing', 'nasal_congestion', 'ear_pain',
    'eye_redness', 'eye_pain', 'difficulty_swallowing', 'hoarseness',
    'anxiety', 'depression', 'insomnia', 'confusion', 'memory_loss',
    'seizures', 'tremor', 'loss_of_appetite', 'bloating', 'constipation',
    'blood_in_stool', 'blood_in_urine', 'painful_urination', 'chills',
    'night_sweats', 'bruising', 'bleeding_gums', 'hair_loss',
    'dry_skin', 'itching', 'jaundice', 'dark_urine', 'pale_stool',
]


def encode_symptoms(symptom_string):
    """
    Convert comma-separated symptom string to multi-hot vector.

    Args:
        symptom_string: "fever,cough,headache"

    Returns:
        list: Binary vector of length len(ALL_SYMPTOMS)
    """
    symptoms = [s.strip().lower().replace(' ', '_') for s in symptom_string.split(',')]
    return [1 if symptom in symptoms else 0 for symptom in ALL_SYMPTOMS]


def encode_demographics(age, gender, bp_sys, bp_dia, heart_rate, temperature, spo2):
    """
    Encode demographic and vital sign features as numeric vector.

    Returns:
        list: [age_normalized, gender_encoded, bp_sys, bp_dia, hr, temp, spo2]
    """
    gender_map = {'male': 0, 'female': 1, 'other': 2}
    return [
        age / 100.0,  # normalize age
        gender_map.get(gender, 2),
        (bp_sys or 120) / 200.0,  # normalize BP
        (bp_dia or 80) / 120.0,
        (heart_rate or 72) / 150.0,  # normalize HR
        ((temperature or 37.0) - 35.0) / 7.0,  # normalize temp
        (spo2 or 98) / 100.0,
    ]


def build_feature_vector(symptom_string, age, gender,
                          bp_sys=None, bp_dia=None, heart_rate=None,
                          temperature=None, spo2=None):
    """
    Combine symptom and demographic features into single vector.

    Returns:
        list: Full feature vector
    """
    symptom_features = encode_symptoms(symptom_string)
    demo_features = encode_demographics(age, gender, bp_sys, bp_dia,
                                         heart_rate, temperature, spo2)
    return symptom_features + demo_features


def get_active_model():
    """Load the currently active ML model and its label encoder."""
    from .models import MLModelVersion

    active_version = MLModelVersion.objects.filter(is_active=True).first()
    if not active_version:
        return None, None, None

    model_path = active_version.model_file
    encoder_path = model_path.replace('.joblib', '_encoder.joblib')

    if not os.path.exists(model_path):
        return None, None, None

    try:
        model = joblib.load(model_path)
        encoder = joblib.load(encoder_path) if os.path.exists(encoder_path) else None
        return model, encoder, active_version
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return None, None, None


def predict_disease(symptom_string, age, gender,
                    bp_sys=None, bp_dia=None, heart_rate=None,
                    temperature=None, spo2=None):
    """
    Predict disease using the active Random Forest model.

    Args:
        symptom_string: Comma-separated symptoms
        age: Patient age
        gender: Patient gender
        bp_sys/bp_dia: Blood pressure
        heart_rate: Heart rate
        temperature: Body temperature
        spo2: Oxygen saturation

    Returns:
        dict: {
            'predictions': [{'disease': str, 'confidence': float, 'icd_code': str}, ...],
            'model_version': str,
            'model_accuracy': float
        }
        or None if no model is available
    """
    if not HAS_ML:
        return None

    model, encoder, version = get_active_model()
    if model is None or encoder is None:
        return None

    try:
        features = build_feature_vector(symptom_string, age, gender,
                                         bp_sys, bp_dia, heart_rate,
                                         temperature, spo2)
        X = np.array([features])

        # Get probability predictions for all classes
        probabilities = model.predict_proba(X)[0]

        # Get top 3 predictions
        top_indices = np.argsort(probabilities)[::-1][:3]

        predictions = []
        for idx in top_indices:
            if probabilities[idx] > 0.01:  # Only include if > 1%
                disease_name = encoder.inverse_transform([idx])[0]
                predictions.append({
                    'disease': disease_name,
                    'confidence': round(float(probabilities[idx]) * 100, 1),
                    'icd_code': DISEASE_ICD_MAP.get(disease_name, ''),
                })

        return {
            'predictions': predictions,
            'model_version': version.version,
            'model_accuracy': round(version.accuracy * 100, 1),
        }

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return None


def check_retrain_needed():
    """
    Check if retraining is needed (50+ new unprocessed confirmed cases).

    Returns:
        tuple: (bool, int) - whether retraining is needed and count of new samples
    """
    from .models import TrainingData

    new_samples = TrainingData.objects.filter(used_for_training=False).count()
    return new_samples >= RETRAIN_THRESHOLD, new_samples


def train_model(triggered_by=None):
    """
    Train a new Random Forest model on all confirmed training data.

    Steps:
    1. Fetch all confirmed training data
    2. Build feature matrix X and label vector y
    3. Split into train/test (80/20)
    4. Train Random Forest with 100 estimators
    5. Evaluate on test set
    6. Save model with version number
    7. Mark training data as used
    8. Set new model as active

    Args:
        triggered_by: User who triggered training (optional)

    Returns:
        MLModelVersion: The newly created model version
    """
    if not HAS_ML:
        raise RuntimeError("scikit-learn is required for model training.")

    from .models import TrainingData, MLModelVersion

    # Fetch all training data
    all_data = TrainingData.objects.all().order_by('created_at')

    if all_data.count() < 10:
        raise ValueError(f"Need at least 10 training samples, have {all_data.count()}")

    # Build feature matrix and labels
    X = []
    y = []

    for record in all_data:
        features = build_feature_vector(
            record.symptoms,
            record.patient_age,
            record.patient_gender,
            record.blood_pressure_systolic,
            record.blood_pressure_diastolic,
            record.heart_rate,
            record.temperature,
            record.spo2,
        )
        X.append(features)
        y.append(record.confirmed_disease)

    X = np.array(X)
    y = np.array(y)

    # Encode labels
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)

    # Train/test split
    n_classes = len(set(y_encoded))
    n_samples = len(y_encoded)
    min_test = max(n_classes, 2)  # Need at least n_classes samples in test set

    if n_classes < 2 or n_samples < min_test + n_classes:
        # Not enough data for proper split, use all data for both
        X_train, X_test = X, X
        y_train, y_test = y_encoded, y_encoded
    else:
        # Ensure test_size is large enough for stratified split
        test_fraction = max(0.2, min_test / n_samples)
        test_fraction = min(test_fraction, 0.4)  # Cap at 40%
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=test_fraction, random_state=42, stratify=y_encoded
        )

    # Train Random Forest
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=3,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    # Evaluate
    y_pred = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    # Calculate per-class metrics (use weighted for multi-class)
    avg_method = 'weighted' if len(set(y_encoded)) > 2 else 'binary'
    try:
        prec = precision_score(y_test, y_pred, average=avg_method, zero_division=0)
        rec = recall_score(y_test, y_pred, average=avg_method, zero_division=0)
        f1 = f1_score(y_test, y_pred, average=avg_method, zero_division=0)
    except Exception:
        prec = rec = f1 = 0.0

    # --- Evaluation charts data ---

    # 1. Confusion Matrix
    class_names = list(label_encoder.classes_)
    cm = confusion_matrix(y_test, y_pred)
    cm_json = json.dumps(cm.tolist())
    class_labels_json = json.dumps(class_names)

    # 2. Feature Importances (top 20)
    importances = clf.feature_importances_
    feature_names = list(ALL_SYMPTOMS) + [
        'Age', 'Gender', 'BP Systolic', 'BP Diastolic',
        'Heart Rate', 'Temperature', 'SpO2'
    ]
    feat_imp_pairs = sorted(
        zip(feature_names, importances.tolist()),
        key=lambda x: x[1], reverse=True
    )[:20]
    feature_importances_json = json.dumps([
        {'feature': name, 'importance': round(val, 4)}
        for name, val in feat_imp_pairs
    ])

    # 3. Per-class Precision/Recall/F1
    try:
        report = classification_report(
            y_test, y_pred,
            target_names=class_names,
            output_dict=True,
            zero_division=0
        )
        per_class = []
        for cls_name in class_names:
            if cls_name in report:
                per_class.append({
                    'class': cls_name,
                    'precision': round(report[cls_name]['precision'], 3),
                    'recall': round(report[cls_name]['recall'], 3),
                    'f1': round(report[cls_name]['f1-score'], 3),
                    'support': report[cls_name]['support'],
                })
        per_class_json = json.dumps(per_class)
    except Exception:
        per_class_json = '[]'

    # Determine version number
    last_version = MLModelVersion.objects.order_by('-trained_at').first()
    if last_version:
        # Parse version number and increment
        try:
            parts = last_version.version.replace('v', '').split('.')
            major, minor = int(parts[0]), int(parts[1])
            new_version = f"v{major}.{minor + 1}"
        except (ValueError, IndexError):
            new_version = "v1.0"
    else:
        new_version = "v1.0"

    # Save model to disk
    model_filename = f"disease_predictor_{new_version.replace('.', '_')}.joblib"
    encoder_filename = f"disease_predictor_{new_version.replace('.', '_')}_encoder.joblib"
    model_path = os.path.join(MODEL_DIR, model_filename)
    encoder_path = os.path.join(MODEL_DIR, encoder_filename)

    joblib.dump(clf, model_path)
    joblib.dump(label_encoder, encoder_path)

    # Deactivate all previous models
    MLModelVersion.objects.filter(is_active=True).update(is_active=False)

    # Create new version record
    model_version = MLModelVersion.objects.create(
        version=new_version,
        accuracy=accuracy,
        precision=prec,
        recall=rec,
        f1_score=f1,
        training_samples=len(X_train),
        test_samples=len(X_test),
        num_classes=len(set(y_encoded)),
        feature_count=X.shape[1],
        model_file=model_path,
        is_active=True,
        notes=f"Trained on {all_data.count()} total samples. "
              f"Diseases: {', '.join(label_encoder.classes_[:10])}",
        trained_by=triggered_by,
        confusion_matrix=cm_json,
        class_labels=class_labels_json,
        feature_importances=feature_importances_json,
        per_class_metrics=per_class_json,
    )

    # Mark all training data as used
    TrainingData.objects.filter(used_for_training=False).update(used_for_training=True)

    logger.info(
        f"Model {new_version} trained. Accuracy: {accuracy:.2%}, "
        f"Samples: {all_data.count()}, Classes: {len(set(y_encoded))}"
    )

    return model_version


def save_training_data(symptoms, age, gender, confirmed_disease, icd_code='',
                       predicted_disease='', predicted_confidence=None,
                       doctor=None, patient=None, model_version=None,
                       bp_sys=None, bp_dia=None, heart_rate=None,
                       temperature=None, spo2=None):
    """
    Save a confirmed diagnosis as labeled training data.
    Checks if retraining threshold is reached and triggers if needed.

    Returns:
        tuple: (TrainingData, bool) - the saved record and whether retraining was triggered
    """
    from .models import TrainingData

    prediction_correct = (
        predicted_disease.lower().strip() == confirmed_disease.lower().strip()
        if predicted_disease else False
    )

    record = TrainingData.objects.create(
        patient_age=age,
        patient_gender=gender,
        blood_pressure_systolic=bp_sys,
        blood_pressure_diastolic=bp_dia,
        heart_rate=heart_rate,
        temperature=temperature,
        spo2=spo2,
        symptoms=symptoms,
        predicted_disease=predicted_disease,
        predicted_confidence=predicted_confidence,
        confirmed_disease=confirmed_disease,
        icd_code=icd_code,
        prediction_correct=prediction_correct,
        doctor=doctor,
        patient=patient,
        model_version=model_version,
    )

    # Check if retraining is needed
    needs_retrain, count = check_retrain_needed()
    retrained = False

    if needs_retrain:
        try:
            train_model(triggered_by=doctor)
            retrained = True
            logger.info(f"Auto-retrained after {count} new samples.")
        except Exception as e:
            logger.error(f"Auto-retrain failed: {e}")

    return record, retrained


# Disease to ICD-10 mapping for predictions
DISEASE_ICD_MAP = {
    'Influenza': 'J11.1',
    'Common Cold': 'J00',
    'COVID-19': 'U07.1',
    'Malaria': 'B54',
    'Typhoid Fever': 'A01.0',
    'Dengue Fever': 'A90',
    'Pneumonia': 'J18.9',
    'Bronchitis': 'J20.9',
    'Asthma': 'J45.9',
    'COPD': 'J44.9',
    'Tuberculosis': 'A15.0',
    'Hypertension': 'I10',
    'Heart Failure': 'I50.9',
    'Angina': 'I20.9',
    'Myocardial Infarction': 'I21.9',
    'Diabetes Type 2': 'E11.9',
    'Diabetes Type 1': 'E10.9',
    'Hypothyroidism': 'E03.9',
    'Hyperthyroidism': 'E05.9',
    'Anemia': 'D64.9',
    'Gastritis': 'K29.7',
    'Gastroenteritis': 'K52.9',
    'Peptic Ulcer': 'K27.9',
    'Appendicitis': 'K37',
    'Irritable Bowel Syndrome': 'K58.9',
    'Hepatitis': 'K75.9',
    'Urinary Tract Infection': 'N39.0',
    'Kidney Stones': 'N20.0',
    'Migraine': 'G43.9',
    'Tension Headache': 'G44.2',
    'Epilepsy': 'G40.9',
    'Stroke': 'I63.9',
    'Meningitis': 'G03.9',
    'Depression': 'F32.9',
    'Anxiety Disorder': 'F41.9',
    'Allergic Rhinitis': 'J30.9',
    'Sinusitis': 'J32.9',
    'Tonsillitis': 'J03.9',
    'Pharyngitis': 'J02.9',
    'Otitis Media': 'H66.9',
    'Conjunctivitis': 'H10.9',
    'Dermatitis': 'L30.9',
    'Psoriasis': 'L40.9',
    'Eczema': 'L20.9',
    'Osteoarthritis': 'M19.9',
    'Rheumatoid Arthritis': 'M06.9',
    'Gout': 'M10.9',
    'Sciatica': 'M54.3',
    'Lumbar Strain': 'S39.0',
    'Vertigo': 'R42',
    'Food Poisoning': 'A05.9',
    'Chickenpox': 'B01.9',
    'Measles': 'B05.9',
}
