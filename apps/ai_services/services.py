"""
AI/ML Services for Hospital Management System.

This module contains machine learning models and services for:
- Patient risk prediction
- Appointment demand forecasting
- Medicine stock prediction
- Wait time estimation
- Anomaly detection
"""
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Avg

# Optional ML imports
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from sklearn.linear_model import LinearRegression
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


def get_patient_risk_score(user):
    """
    Calculate patient risk score using Random Forest-like logic.

    Features considered:
    - Age
    - Number of chronic conditions
    - Visit frequency
    - Number of active medications

    Returns:
        dict: {'score': int, 'level': str, 'factors': list}
    """
    try:
        from apps.patients.models import Patient
        from apps.medical_records.models import MedicalRecord, Prescription

        patient = getattr(user, 'patient_profile', None)
        if not patient:
            return None

        # Calculate features
        age = 0
        if user.date_of_birth:
            age = (timezone.now().date() - user.date_of_birth).days // 365

        # Chronic conditions count
        chronic_count = len(patient.chronic_conditions.split(',')) if patient.chronic_conditions else 0

        # Visit frequency (last 6 months)
        six_months_ago = timezone.now().date() - timedelta(days=180)
        visit_count = MedicalRecord.objects.filter(
            patient=user,
            visit_date__gte=six_months_ago
        ).count()

        # Active prescriptions
        active_prescriptions = Prescription.objects.filter(
            patient=user,
            status='pending'
        ).count()

        # Simple risk calculation (would use trained model in production)
        risk_score = 0

        # Age factor (0-25 points)
        if age > 70:
            risk_score += 25
        elif age > 60:
            risk_score += 20
        elif age > 50:
            risk_score += 15
        elif age > 40:
            risk_score += 10
        else:
            risk_score += 5

        # Chronic conditions (0-30 points)
        risk_score += min(chronic_count * 10, 30)

        # Visit frequency (0-25 points)
        if visit_count > 6:
            risk_score += 25
        elif visit_count > 3:
            risk_score += 15
        else:
            risk_score += 5

        # Medications (0-20 points)
        risk_score += min(active_prescriptions * 5, 20)

        # Determine risk level
        if risk_score >= 70:
            level = 'Critical'
        elif risk_score >= 50:
            level = 'High'
        elif risk_score >= 30:
            level = 'Medium'
        else:
            level = 'Low'

        factors = []
        if age > 60:
            factors.append('Age above 60')
        if chronic_count > 2:
            factors.append(f'{chronic_count} chronic conditions')
        if visit_count > 4:
            factors.append('Frequent hospital visits')

        # Update patient risk score
        patient.risk_score = risk_score
        patient.risk_level = level.lower()
        patient.save(update_fields=['risk_score', 'risk_level'])

        return {
            'score': risk_score,
            'level': level,
            'factors': factors,
        }

    except Exception as e:
        print(f"Error calculating risk score: {e}")
        return None


def calculate_wait_time(appointment):
    """
    Estimate wait time for a patient using Gradient Boosting-like logic.

    Features:
    - Queue position
    - Doctor's average consultation time
    - Time of day
    - Day of week

    Returns:
        int: Estimated wait time in minutes
    """
    try:
        from apps.appointments.models import Appointment

        # Get patients ahead in queue
        patients_ahead = Appointment.objects.filter(
            doctor=appointment.doctor,
            scheduled_date=appointment.scheduled_date,
            status='checked_in',
            queue_number__lt=appointment.queue_number
        ).count()

        # Get doctor's average consultation time
        avg_time = 15  # Default 15 minutes
        if hasattr(appointment.doctor, 'doctor_profile'):
            avg_time = appointment.doctor.doctor_profile.average_consultation_time

        # Time of day factor
        hour = timezone.now().hour
        time_factor = 1.0
        if 10 <= hour <= 12 or 14 <= hour <= 16:
            time_factor = 1.2  # Peak hours

        # Day of week factor
        day_factor = 1.0
        if timezone.now().weekday() == 0:  # Monday
            day_factor = 1.3

        estimated_wait = int(patients_ahead * avg_time * time_factor * day_factor)

        return estimated_wait

    except Exception as e:
        print(f"Error calculating wait time: {e}")
        return 15  # Default


def get_workload_optimization(doctor):
    """
    Analyze doctor's workload and provide optimization suggestions.

    Returns:
        dict: Workload analysis and suggestions
    """
    try:
        from apps.appointments.models import Appointment

        today = timezone.now().date()

        # Today's appointments
        today_appointments = Appointment.objects.filter(
            doctor=doctor,
            scheduled_date=today
        )

        total = today_appointments.count()
        completed = today_appointments.filter(status='completed').count()
        waiting = today_appointments.filter(status='checked_in').count()

        # Calculate workload level
        if total > 25:
            level = 'High'
        elif total > 15:
            level = 'Moderate'
        else:
            level = 'Light'

        # Estimate finish time
        avg_time = 15
        if hasattr(doctor, 'doctor_profile'):
            avg_time = doctor.doctor_profile.average_consultation_time

        remaining = total - completed
        minutes_needed = remaining * avg_time
        finish_time = timezone.now() + timedelta(minutes=minutes_needed)

        return {
            'level': level,
            'total_patients': total,
            'completed': completed,
            'waiting': waiting,
            'avg_time': avg_time,
            'finish_time': finish_time.strftime('%H:%M'),
        }

    except Exception as e:
        print(f"Error analyzing workload: {e}")
        return None


def get_stock_predictions():
    """
    Predict medicine stock demand using time series analysis.

    Returns:
        list: Predictions for medicines with estimated days until stockout
    """
    try:
        from apps.pharmacy.models import MedicineStock
        from apps.medical_records.models import PrescriptionItem
        from datetime import timedelta

        predictions = []

        # Get medicines with low stock
        low_stock = MedicineStock.objects.filter(
            quantity__gt=0
        ).select_related('medicine')[:10]

        for stock in low_stock:
            # Calculate average daily consumption (last 30 days)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            consumption = PrescriptionItem.objects.filter(
                medicine=stock.medicine,
                prescription__created_at__gte=thirty_days_ago,
                is_dispensed=True
            ).count()

            daily_avg = consumption / 30 if consumption > 0 else 0.5

            # Predict days until stockout
            if daily_avg > 0:
                days_left = int(stock.quantity / daily_avg)
            else:
                days_left = 999

            predictions.append({
                'medicine': stock.medicine.name,
                'current_stock': stock.quantity,
                'daily_avg': round(daily_avg, 1),
                'days_left': min(days_left, 999),
            })

        return sorted(predictions, key=lambda x: x['days_left'])[:5]

    except Exception as e:
        print(f"Error predicting stock: {e}")
        return []


def get_queue_wait_times():
    """
    Calculate current queue wait times.

    Returns:
        dict: Wait time statistics
    """
    try:
        from apps.appointments.models import Appointment

        today = timezone.now().date()

        waiting = Appointment.objects.filter(
            scheduled_date=today,
            status='checked_in'
        )

        wait_times = []
        for apt in waiting:
            if apt.check_in_time:
                wait = (timezone.now() - apt.check_in_time).seconds // 60
                wait_times.append(wait)

        if wait_times:
            return {
                'average': int(sum(wait_times) / len(wait_times)),
                'max': max(wait_times),
                'min': min(wait_times),
                'patients_waiting': len(wait_times),
            }

        return {
            'average': 0,
            'max': 0,
            'min': 0,
            'patients_waiting': 0,
        }

    except Exception as e:
        print(f"Error calculating queue times: {e}")
        return None


def get_hospital_analytics():
    """
    Generate AI-powered hospital analytics summary.

    Returns:
        dict: Analytics insights
    """
    try:
        from apps.appointments.models import Appointment
        from apps.accounts.models import User

        today = timezone.now().date()
        week_ago = today - timedelta(days=7)

        # Trends analysis
        this_week = Appointment.objects.filter(scheduled_date__gte=week_ago).count()
        last_week = Appointment.objects.filter(
            scheduled_date__gte=week_ago - timedelta(days=7),
            scheduled_date__lt=week_ago
        ).count()

        if last_week > 0:
            trend = ((this_week - last_week) / last_week) * 100
        else:
            trend = 0

        if trend > 10:
            summary = f"Patient visits increased by {trend:.0f}% compared to last week. Consider adding more appointment slots."
        elif trend < -10:
            summary = f"Patient visits decreased by {abs(trend):.0f}% compared to last week."
        else:
            summary = "Patient visit patterns are stable this week."

        return {
            'summary': summary,
            'trend': round(trend, 1),
            'this_week': this_week,
            'last_week': last_week,
        }

    except Exception as e:
        print(f"Error generating analytics: {e}")
        return None


def get_ml_stock_forecast(medicine_id=None, days_ahead=30):
    """
    Predict medicine stock demand using Linear Regression on historical data.

    Analyzes 90 days of dispensing history and predicts 30-day demand.

    Args:
        medicine_id: Optional specific medicine ID to forecast
        days_ahead: Number of days to forecast (default 30)

    Returns:
        list: Forecasts with predicted demand, confidence, and stockout risk
    """
    try:
        from apps.pharmacy.models import MedicineStock, Medicine, StockTransaction

        forecasts = []

        # Get medicines to forecast
        if medicine_id:
            medicines = Medicine.objects.filter(pk=medicine_id, is_active=True)
        else:
            # Get all medicines with stock
            stock_ids = MedicineStock.objects.values_list('medicine_id', flat=True).distinct()
            medicines = Medicine.objects.filter(pk__in=stock_ids, is_active=True)[:20]

        for medicine in medicines:
            # Get 90 days of transaction history
            ninety_days_ago = timezone.now() - timedelta(days=90)

            transactions = StockTransaction.objects.filter(
                stock__medicine=medicine,
                transaction_type='out',
                created_at__gte=ninety_days_ago
            ).order_by('created_at')

            # Aggregate by day
            daily_usage = {}
            for txn in transactions:
                day_key = txn.created_at.date()
                daily_usage[day_key] = daily_usage.get(day_key, 0) + txn.quantity

            # Need at least 7 days of data for meaningful prediction
            if len(daily_usage) < 7:
                # Fallback to simple average
                total_out = sum(daily_usage.values()) if daily_usage else 0
                days_with_data = len(daily_usage) if daily_usage else 1
                daily_avg = total_out / max(days_with_data, 1)
                predicted_demand = daily_avg * days_ahead
                confidence = 'Low'
            else:
                # Use ML if available
                if HAS_SKLEARN and HAS_NUMPY:
                    # Prepare data for linear regression
                    sorted_dates = sorted(daily_usage.keys())
                    X = np.array([(d - sorted_dates[0]).days for d in sorted_dates]).reshape(-1, 1)
                    y = np.array([daily_usage[d] for d in sorted_dates])

                    # Fit model
                    model = LinearRegression()
                    model.fit(X, y)

                    # Predict next 30 days
                    last_day = (sorted_dates[-1] - sorted_dates[0]).days
                    future_days = np.array(range(last_day + 1, last_day + days_ahead + 1)).reshape(-1, 1)
                    predictions = model.predict(future_days)

                    # Ensure no negative predictions
                    predictions = np.maximum(predictions, 0)
                    predicted_demand = predictions.sum()

                    # Calculate confidence based on R-squared
                    score = model.score(X, y)
                    if score > 0.7:
                        confidence = 'High'
                    elif score > 0.4:
                        confidence = 'Medium'
                    else:
                        confidence = 'Low'
                else:
                    # Fallback without sklearn
                    daily_avg = sum(daily_usage.values()) / len(daily_usage)
                    predicted_demand = daily_avg * days_ahead
                    confidence = 'Medium'

            # Get current stock level
            current_stock = MedicineStock.objects.filter(
                medicine=medicine,
                quantity__gt=0
            ).aggregate(total=Count('quantity'))['total'] or 0

            total_quantity = sum(
                MedicineStock.objects.filter(medicine=medicine).values_list('quantity', flat=True)
            )

            # Calculate days until stockout
            if predicted_demand > 0:
                daily_predicted = predicted_demand / days_ahead
                days_until_stockout = int(total_quantity / daily_predicted) if daily_predicted > 0 else 999
            else:
                days_until_stockout = 999

            # Determine risk level
            if days_until_stockout <= 7:
                risk_level = 'Critical'
                risk_color = 'red'
            elif days_until_stockout <= 14:
                risk_level = 'High'
                risk_color = 'orange'
            elif days_until_stockout <= 30:
                risk_level = 'Medium'
                risk_color = 'yellow'
            else:
                risk_level = 'Low'
                risk_color = 'green'

            forecasts.append({
                'medicine_id': medicine.pk,
                'medicine_name': medicine.name,
                'current_stock': total_quantity,
                'predicted_demand': round(predicted_demand, 0),
                'daily_average': round(predicted_demand / days_ahead, 1),
                'days_until_stockout': min(days_until_stockout, 999),
                'confidence': confidence,
                'risk_level': risk_level,
                'risk_color': risk_color,
                'recommended_order': max(0, round(predicted_demand * 1.2 - total_quantity)),
            })

        # Sort by stockout risk (days until stockout ascending)
        return sorted(forecasts, key=lambda x: x['days_until_stockout'])

    except Exception as e:
        print(f"Error in ML stock forecast: {e}")
        return []


# Symptom-Diagnosis knowledge base (expanded - 30+ symptom categories)
SYMPTOM_DIAGNOSIS_RULES = {
    'fever': {
        'conditions': [
            {'name': 'Influenza (Flu)', 'icd_code': 'J11.1', 'weight': 0.8},
            {'name': 'Common Cold', 'icd_code': 'J00', 'weight': 0.7},
            {'name': 'COVID-19', 'icd_code': 'U07.1', 'weight': 0.6},
            {'name': 'Malaria', 'icd_code': 'B54', 'weight': 0.5},
            {'name': 'Typhoid Fever', 'icd_code': 'A01.0', 'weight': 0.4},
            {'name': 'Dengue Fever', 'icd_code': 'A90', 'weight': 0.4},
            {'name': 'Urinary Tract Infection', 'icd_code': 'N39.0', 'weight': 0.4},
            {'name': 'Meningitis', 'icd_code': 'G03.9', 'weight': 0.3},
        ]
    },
    'headache': {
        'conditions': [
            {'name': 'Tension Headache', 'icd_code': 'G44.2', 'weight': 0.9},
            {'name': 'Migraine', 'icd_code': 'G43.9', 'weight': 0.7},
            {'name': 'Sinusitis', 'icd_code': 'J32.9', 'weight': 0.5},
            {'name': 'Hypertension', 'icd_code': 'I10', 'weight': 0.4},
            {'name': 'Meningitis', 'icd_code': 'G03.9', 'weight': 0.3},
            {'name': 'Stroke', 'icd_code': 'I63.9', 'weight': 0.2},
        ]
    },
    'cough': {
        'conditions': [
            {'name': 'Acute Bronchitis', 'icd_code': 'J20.9', 'weight': 0.8},
            {'name': 'Common Cold', 'icd_code': 'J00', 'weight': 0.7},
            {'name': 'Pneumonia', 'icd_code': 'J18.9', 'weight': 0.5},
            {'name': 'Asthma', 'icd_code': 'J45.9', 'weight': 0.4},
            {'name': 'COVID-19', 'icd_code': 'U07.1', 'weight': 0.5},
            {'name': 'Tuberculosis', 'icd_code': 'A15.0', 'weight': 0.3},
            {'name': 'COPD', 'icd_code': 'J44.9', 'weight': 0.4},
        ]
    },
    'chest_pain': {
        'conditions': [
            {'name': 'Angina Pectoris', 'icd_code': 'I20.9', 'weight': 0.7},
            {'name': 'GERD', 'icd_code': 'K21.0', 'weight': 0.6},
            {'name': 'Costochondritis', 'icd_code': 'M94.0', 'weight': 0.5},
            {'name': 'Myocardial Infarction', 'icd_code': 'I21.9', 'weight': 0.4},
            {'name': 'Pneumonia', 'icd_code': 'J18.9', 'weight': 0.3},
        ]
    },
    'abdominal_pain': {
        'conditions': [
            {'name': 'Gastritis', 'icd_code': 'K29.7', 'weight': 0.8},
            {'name': 'Gastroenteritis', 'icd_code': 'K52.9', 'weight': 0.7},
            {'name': 'Appendicitis', 'icd_code': 'K37', 'weight': 0.4},
            {'name': 'Peptic Ulcer', 'icd_code': 'K27.9', 'weight': 0.5},
            {'name': 'Irritable Bowel Syndrome', 'icd_code': 'K58.9', 'weight': 0.5},
            {'name': 'Kidney Stones', 'icd_code': 'N20.0', 'weight': 0.3},
            {'name': 'Hepatitis', 'icd_code': 'K75.9', 'weight': 0.3},
        ]
    },
    'fatigue': {
        'conditions': [
            {'name': 'Anemia', 'icd_code': 'D64.9', 'weight': 0.7},
            {'name': 'Hypothyroidism', 'icd_code': 'E03.9', 'weight': 0.5},
            {'name': 'Diabetes Mellitus', 'icd_code': 'E14', 'weight': 0.5},
            {'name': 'Depression', 'icd_code': 'F32.9', 'weight': 0.6},
            {'name': 'Heart Failure', 'icd_code': 'I50.9', 'weight': 0.3},
            {'name': 'Chronic Fatigue Syndrome', 'icd_code': 'R53.82', 'weight': 0.5},
        ]
    },
    'shortness_of_breath': {
        'conditions': [
            {'name': 'Asthma', 'icd_code': 'J45.9', 'weight': 0.8},
            {'name': 'COPD', 'icd_code': 'J44.9', 'weight': 0.6},
            {'name': 'Heart Failure', 'icd_code': 'I50.9', 'weight': 0.5},
            {'name': 'Pneumonia', 'icd_code': 'J18.9', 'weight': 0.5},
            {'name': 'Anxiety Disorder', 'icd_code': 'F41.9', 'weight': 0.4},
            {'name': 'Anemia', 'icd_code': 'D64.9', 'weight': 0.3},
        ]
    },
    'nausea': {
        'conditions': [
            {'name': 'Gastroenteritis', 'icd_code': 'K52.9', 'weight': 0.8},
            {'name': 'Food Poisoning', 'icd_code': 'A05.9', 'weight': 0.7},
            {'name': 'Migraine', 'icd_code': 'G43.9', 'weight': 0.4},
            {'name': 'Hepatitis', 'icd_code': 'K75.9', 'weight': 0.4},
            {'name': 'Pregnancy', 'icd_code': 'O21.0', 'weight': 0.3},
        ]
    },
    'vomiting': {
        'conditions': [
            {'name': 'Gastroenteritis', 'icd_code': 'K52.9', 'weight': 0.8},
            {'name': 'Food Poisoning', 'icd_code': 'A05.9', 'weight': 0.8},
            {'name': 'Appendicitis', 'icd_code': 'K37', 'weight': 0.4},
            {'name': 'Meningitis', 'icd_code': 'G03.9', 'weight': 0.3},
            {'name': 'Kidney Stones', 'icd_code': 'N20.0', 'weight': 0.3},
        ]
    },
    'diarrhea': {
        'conditions': [
            {'name': 'Gastroenteritis', 'icd_code': 'K52.9', 'weight': 0.9},
            {'name': 'Food Poisoning', 'icd_code': 'A05.9', 'weight': 0.7},
            {'name': 'Irritable Bowel Syndrome', 'icd_code': 'K58.9', 'weight': 0.5},
            {'name': 'Cholera', 'icd_code': 'A00.9', 'weight': 0.3},
            {'name': 'Typhoid Fever', 'icd_code': 'A01.0', 'weight': 0.3},
        ]
    },
    'constipation': {
        'conditions': [
            {'name': 'Irritable Bowel Syndrome', 'icd_code': 'K58.9', 'weight': 0.7},
            {'name': 'Hypothyroidism', 'icd_code': 'E03.9', 'weight': 0.5},
            {'name': 'Bowel Obstruction', 'icd_code': 'K56.6', 'weight': 0.3},
            {'name': 'Colorectal Cancer', 'icd_code': 'C20', 'weight': 0.2},
        ]
    },
    'joint_pain': {
        'conditions': [
            {'name': 'Osteoarthritis', 'icd_code': 'M19.9', 'weight': 0.8},
            {'name': 'Rheumatoid Arthritis', 'icd_code': 'M06.9', 'weight': 0.6},
            {'name': 'Gout', 'icd_code': 'M10.9', 'weight': 0.5},
            {'name': 'Viral Arthritis', 'icd_code': 'M01.9', 'weight': 0.4},
            {'name': 'Lupus', 'icd_code': 'M32.9', 'weight': 0.3},
        ]
    },
    'skin_rash': {
        'conditions': [
            {'name': 'Allergic Dermatitis', 'icd_code': 'L23.9', 'weight': 0.8},
            {'name': 'Eczema', 'icd_code': 'L30.9', 'weight': 0.7},
            {'name': 'Psoriasis', 'icd_code': 'L40.9', 'weight': 0.5},
            {'name': 'Measles', 'icd_code': 'B05.9', 'weight': 0.3},
            {'name': 'Chickenpox', 'icd_code': 'B01.9', 'weight': 0.3},
            {'name': 'Lupus', 'icd_code': 'M32.9', 'weight': 0.2},
        ]
    },
    'dizziness': {
        'conditions': [
            {'name': 'Vertigo', 'icd_code': 'R42', 'weight': 0.8},
            {'name': 'Hypotension', 'icd_code': 'I95.9', 'weight': 0.6},
            {'name': 'Anemia', 'icd_code': 'D64.9', 'weight': 0.5},
            {'name': 'Inner Ear Infection', 'icd_code': 'H83.0', 'weight': 0.5},
            {'name': 'Stroke', 'icd_code': 'I63.9', 'weight': 0.2},
        ]
    },
    'sore_throat': {
        'conditions': [
            {'name': 'Pharyngitis', 'icd_code': 'J02.9', 'weight': 0.9},
            {'name': 'Tonsillitis', 'icd_code': 'J03.9', 'weight': 0.7},
            {'name': 'Strep Throat', 'icd_code': 'J02.0', 'weight': 0.6},
            {'name': 'Common Cold', 'icd_code': 'J00', 'weight': 0.5},
            {'name': 'COVID-19', 'icd_code': 'U07.1', 'weight': 0.3},
        ]
    },
    'back_pain': {
        'conditions': [
            {'name': 'Lumbar Strain', 'icd_code': 'S39.0', 'weight': 0.8},
            {'name': 'Herniated Disc', 'icd_code': 'M51.1', 'weight': 0.5},
            {'name': 'Sciatica', 'icd_code': 'M54.3', 'weight': 0.5},
            {'name': 'Kidney Stones', 'icd_code': 'N20.0', 'weight': 0.3},
            {'name': 'Osteoporosis', 'icd_code': 'M81.0', 'weight': 0.3},
        ]
    },
    'frequent_urination': {
        'conditions': [
            {'name': 'Urinary Tract Infection', 'icd_code': 'N39.0', 'weight': 0.8},
            {'name': 'Diabetes Mellitus', 'icd_code': 'E14', 'weight': 0.7},
            {'name': 'Prostate Enlargement', 'icd_code': 'N40', 'weight': 0.5},
            {'name': 'Overactive Bladder', 'icd_code': 'N32.81', 'weight': 0.5},
        ]
    },
    'painful_urination': {
        'conditions': [
            {'name': 'Urinary Tract Infection', 'icd_code': 'N39.0', 'weight': 0.9},
            {'name': 'Kidney Stones', 'icd_code': 'N20.0', 'weight': 0.5},
            {'name': 'Sexually Transmitted Infection', 'icd_code': 'A64', 'weight': 0.4},
        ]
    },
    'excessive_thirst': {
        'conditions': [
            {'name': 'Diabetes Mellitus', 'icd_code': 'E14', 'weight': 0.9},
            {'name': 'Diabetes Insipidus', 'icd_code': 'E23.2', 'weight': 0.5},
            {'name': 'Dehydration', 'icd_code': 'E86.0', 'weight': 0.6},
        ]
    },
    'weight_loss': {
        'conditions': [
            {'name': 'Hyperthyroidism', 'icd_code': 'E05.9', 'weight': 0.7},
            {'name': 'Diabetes Mellitus', 'icd_code': 'E14', 'weight': 0.6},
            {'name': 'Tuberculosis', 'icd_code': 'A15.0', 'weight': 0.5},
            {'name': 'Depression', 'icd_code': 'F32.9', 'weight': 0.4},
            {'name': 'Cancer (unspecified)', 'icd_code': 'C80', 'weight': 0.3},
        ]
    },
    'palpitations': {
        'conditions': [
            {'name': 'Anxiety Disorder', 'icd_code': 'F41.9', 'weight': 0.7},
            {'name': 'Atrial Fibrillation', 'icd_code': 'I48.91', 'weight': 0.6},
            {'name': 'Hyperthyroidism', 'icd_code': 'E05.9', 'weight': 0.5},
            {'name': 'Anemia', 'icd_code': 'D64.9', 'weight': 0.4},
        ]
    },
    'swelling': {
        'conditions': [
            {'name': 'Heart Failure', 'icd_code': 'I50.9', 'weight': 0.6},
            {'name': 'Kidney Disease', 'icd_code': 'N18.9', 'weight': 0.5},
            {'name': 'Deep Vein Thrombosis', 'icd_code': 'I82.9', 'weight': 0.5},
            {'name': 'Liver Cirrhosis', 'icd_code': 'K74.6', 'weight': 0.3},
        ]
    },
    'wheezing': {
        'conditions': [
            {'name': 'Asthma', 'icd_code': 'J45.9', 'weight': 0.9},
            {'name': 'COPD', 'icd_code': 'J44.9', 'weight': 0.7},
            {'name': 'Acute Bronchitis', 'icd_code': 'J20.9', 'weight': 0.5},
            {'name': 'Allergic Reaction', 'icd_code': 'T78.4', 'weight': 0.4},
        ]
    },
    'runny_nose': {
        'conditions': [
            {'name': 'Common Cold', 'icd_code': 'J00', 'weight': 0.9},
            {'name': 'Allergic Rhinitis', 'icd_code': 'J30.9', 'weight': 0.8},
            {'name': 'Sinusitis', 'icd_code': 'J32.9', 'weight': 0.5},
            {'name': 'Influenza (Flu)', 'icd_code': 'J11.1', 'weight': 0.4},
        ]
    },
    'ear_pain': {
        'conditions': [
            {'name': 'Otitis Media', 'icd_code': 'H66.9', 'weight': 0.9},
            {'name': 'Otitis Externa', 'icd_code': 'H60.9', 'weight': 0.7},
            {'name': 'TMJ Disorder', 'icd_code': 'M26.6', 'weight': 0.4},
            {'name': 'Pharyngitis', 'icd_code': 'J02.9', 'weight': 0.3},
        ]
    },
    'eye_redness': {
        'conditions': [
            {'name': 'Conjunctivitis', 'icd_code': 'H10.9', 'weight': 0.9},
            {'name': 'Allergic Conjunctivitis', 'icd_code': 'H10.1', 'weight': 0.7},
            {'name': 'Glaucoma', 'icd_code': 'H40.9', 'weight': 0.3},
            {'name': 'Uveitis', 'icd_code': 'H20.9', 'weight': 0.3},
        ]
    },
    'blurred_vision': {
        'conditions': [
            {'name': 'Diabetes Mellitus', 'icd_code': 'E14', 'weight': 0.6},
            {'name': 'Glaucoma', 'icd_code': 'H40.9', 'weight': 0.5},
            {'name': 'Migraine', 'icd_code': 'G43.9', 'weight': 0.5},
            {'name': 'Cataracts', 'icd_code': 'H26.9', 'weight': 0.4},
            {'name': 'Hypertension', 'icd_code': 'I10', 'weight': 0.3},
        ]
    },
    'numbness': {
        'conditions': [
            {'name': 'Peripheral Neuropathy', 'icd_code': 'G62.9', 'weight': 0.7},
            {'name': 'Diabetes Mellitus', 'icd_code': 'E14', 'weight': 0.6},
            {'name': 'Carpal Tunnel Syndrome', 'icd_code': 'G56.0', 'weight': 0.6},
            {'name': 'Stroke', 'icd_code': 'I63.9', 'weight': 0.4},
            {'name': 'Multiple Sclerosis', 'icd_code': 'G35', 'weight': 0.3},
        ]
    },
    'anxiety': {
        'conditions': [
            {'name': 'Generalized Anxiety Disorder', 'icd_code': 'F41.1', 'weight': 0.9},
            {'name': 'Panic Disorder', 'icd_code': 'F41.0', 'weight': 0.6},
            {'name': 'Hyperthyroidism', 'icd_code': 'E05.9', 'weight': 0.4},
            {'name': 'Depression', 'icd_code': 'F32.9', 'weight': 0.5},
        ]
    },
    'insomnia': {
        'conditions': [
            {'name': 'Insomnia Disorder', 'icd_code': 'G47.0', 'weight': 0.8},
            {'name': 'Anxiety Disorder', 'icd_code': 'F41.9', 'weight': 0.6},
            {'name': 'Depression', 'icd_code': 'F32.9', 'weight': 0.6},
            {'name': 'Hyperthyroidism', 'icd_code': 'E05.9', 'weight': 0.3},
        ]
    },
    'jaundice': {
        'conditions': [
            {'name': 'Hepatitis', 'icd_code': 'K75.9', 'weight': 0.8},
            {'name': 'Gallstones', 'icd_code': 'K80.2', 'weight': 0.6},
            {'name': 'Liver Cirrhosis', 'icd_code': 'K74.6', 'weight': 0.5},
            {'name': 'Hemolytic Anemia', 'icd_code': 'D59.9', 'weight': 0.4},
            {'name': 'Pancreatic Cancer', 'icd_code': 'C25.9', 'weight': 0.2},
        ]
    },
    'night_sweats': {
        'conditions': [
            {'name': 'Tuberculosis', 'icd_code': 'A15.0', 'weight': 0.7},
            {'name': 'Lymphoma', 'icd_code': 'C85.9', 'weight': 0.4},
            {'name': 'HIV/AIDS', 'icd_code': 'B20', 'weight': 0.3},
            {'name': 'Hyperthyroidism', 'icd_code': 'E05.9', 'weight': 0.4},
            {'name': 'Menopause', 'icd_code': 'N95.1', 'weight': 0.5},
        ]
    },
    'chills': {
        'conditions': [
            {'name': 'Influenza (Flu)', 'icd_code': 'J11.1', 'weight': 0.8},
            {'name': 'Malaria', 'icd_code': 'B54', 'weight': 0.6},
            {'name': 'Urinary Tract Infection', 'icd_code': 'N39.0', 'weight': 0.5},
            {'name': 'Pneumonia', 'icd_code': 'J18.9', 'weight': 0.5},
        ]
    },
    'muscle_weakness': {
        'conditions': [
            {'name': 'Myasthenia Gravis', 'icd_code': 'G70.0', 'weight': 0.5},
            {'name': 'Multiple Sclerosis', 'icd_code': 'G35', 'weight': 0.4},
            {'name': 'Hypothyroidism', 'icd_code': 'E03.9', 'weight': 0.5},
            {'name': 'Anemia', 'icd_code': 'D64.9', 'weight': 0.5},
            {'name': 'Stroke', 'icd_code': 'I63.9', 'weight': 0.3},
        ]
    },
    'blood_in_urine': {
        'conditions': [
            {'name': 'Urinary Tract Infection', 'icd_code': 'N39.0', 'weight': 0.7},
            {'name': 'Kidney Stones', 'icd_code': 'N20.0', 'weight': 0.7},
            {'name': 'Bladder Cancer', 'icd_code': 'C67.9', 'weight': 0.3},
            {'name': 'Glomerulonephritis', 'icd_code': 'N05.9', 'weight': 0.4},
        ]
    },
    'blood_in_stool': {
        'conditions': [
            {'name': 'Hemorrhoids', 'icd_code': 'K64.9', 'weight': 0.7},
            {'name': 'Inflammatory Bowel Disease', 'icd_code': 'K51.9', 'weight': 0.5},
            {'name': 'Gastric Ulcer', 'icd_code': 'K25.9', 'weight': 0.4},
            {'name': 'Colorectal Cancer', 'icd_code': 'C20', 'weight': 0.2},
        ]
    },
    'hair_loss': {
        'conditions': [
            {'name': 'Alopecia', 'icd_code': 'L65.9', 'weight': 0.8},
            {'name': 'Hypothyroidism', 'icd_code': 'E03.9', 'weight': 0.5},
            {'name': 'Iron Deficiency Anemia', 'icd_code': 'D50.9', 'weight': 0.5},
            {'name': 'Lupus', 'icd_code': 'M32.9', 'weight': 0.3},
        ]
    },
    'seizures': {
        'conditions': [
            {'name': 'Epilepsy', 'icd_code': 'G40.9', 'weight': 0.8},
            {'name': 'Meningitis', 'icd_code': 'G03.9', 'weight': 0.4},
            {'name': 'Brain Tumor', 'icd_code': 'D43.9', 'weight': 0.3},
            {'name': 'Stroke', 'icd_code': 'I63.9', 'weight': 0.3},
        ]
    },
    'difficulty_swallowing': {
        'conditions': [
            {'name': 'GERD', 'icd_code': 'K21.0', 'weight': 0.6},
            {'name': 'Tonsillitis', 'icd_code': 'J03.9', 'weight': 0.6},
            {'name': 'Esophageal Stricture', 'icd_code': 'K22.2', 'weight': 0.4},
            {'name': 'Stroke', 'icd_code': 'I63.9', 'weight': 0.3},
        ]
    },
}


def get_ai_diagnosis_suggestions(symptoms_list):
    """
    Generate AI-powered diagnosis suggestions based on reported symptoms.

    Uses a rule-based system with weighted scoring to suggest possible diagnoses.

    Args:
        symptoms_list: List of symptom keywords (e.g., ['fever', 'cough', 'headache'])

    Returns:
        list: Top 5 diagnoses with confidence scores and ICD codes
    """
    if not symptoms_list:
        return []

    # Normalize symptoms
    normalized_symptoms = []
    for symptom in symptoms_list:
        symptom = symptom.lower().strip().replace(' ', '_')
        # Handle common variations
        variations = {
            # Abdominal/GI
            'stomach_pain': 'abdominal_pain',
            'belly_pain': 'abdominal_pain',
            'tummy_pain': 'abdominal_pain',
            'stomach_ache': 'abdominal_pain',
            'cramps': 'abdominal_pain',
            'throwing_up': 'vomiting',
            'puking': 'vomiting',
            'feeling_sick': 'nausea',
            'queasy': 'nausea',
            'loose_stool': 'diarrhea',
            'watery_stool': 'diarrhea',
            'hard_stool': 'constipation',
            'difficulty_passing_stool': 'constipation',
            'gas': 'bloating',
            'flatulence': 'bloating',
            'bloody_stool': 'blood_in_stool',
            'rectal_bleeding': 'blood_in_stool',
            # General
            'tired': 'fatigue',
            'tiredness': 'fatigue',
            'exhaustion': 'fatigue',
            'exhausted': 'fatigue',
            'lethargic': 'fatigue',
            'lethargy': 'fatigue',
            'weak': 'fatigue',
            'high_temperature': 'fever',
            'pyrexia': 'fever',
            'feverish': 'fever',
            'shivering': 'chills',
            'cold_sweats': 'chills',
            'rigor': 'chills',
            'sweating_at_night': 'night_sweats',
            'no_appetite': 'loss_of_appetite',
            'not_hungry': 'loss_of_appetite',
            'losing_weight': 'weight_loss',
            'slimming': 'weight_loss',
            'gaining_weight': 'weight_gain',
            # Respiratory
            'breathlessness': 'shortness_of_breath',
            'difficulty_breathing': 'shortness_of_breath',
            'cant_breathe': 'shortness_of_breath',
            'dyspnea': 'shortness_of_breath',
            'breathing_difficulty': 'shortness_of_breath',
            'tight_chest': 'chest_tightness',
            'stuffy_nose': 'nasal_congestion',
            'blocked_nose': 'nasal_congestion',
            'nose_running': 'runny_nose',
            'sniffles': 'runny_nose',
            'sneezy': 'sneezing',
            'whistling_breath': 'wheezing',
            'dry_cough': 'cough',
            'wet_cough': 'cough',
            'persistent_cough': 'cough',
            # Head & Neurological
            'head_pain': 'headache',
            'migraine': 'headache',
            'head_spinning': 'dizziness',
            'lightheaded': 'dizziness',
            'lightheadedness': 'dizziness',
            'vertigo': 'dizziness',
            'faint': 'dizziness',
            'fainting': 'dizziness',
            'confused': 'confusion',
            'disoriented': 'confusion',
            'forgetful': 'memory_loss',
            'cant_remember': 'memory_loss',
            'fits': 'seizures',
            'convulsion': 'seizures',
            'convulsions': 'seizures',
            'shaking': 'tremor',
            'trembling': 'tremor',
            'cant_sleep': 'insomnia',
            'sleepless': 'insomnia',
            'sleep_problems': 'insomnia',
            'worried': 'anxiety',
            'anxious': 'anxiety',
            'nervousness': 'anxiety',
            'nervous': 'anxiety',
            'panic': 'anxiety',
            'sad': 'depression',
            'depressed': 'depression',
            'low_mood': 'depression',
            'hopeless': 'depression',
            # Cardiovascular
            'heart_racing': 'palpitations',
            'heart_pounding': 'palpitations',
            'irregular_heartbeat': 'palpitations',
            'edema': 'swelling',
            'swollen': 'swelling',
            'swollen_legs': 'swelling',
            'swollen_feet': 'swelling',
            # Musculoskeletal
            'rash': 'skin_rash',
            'itchy_skin': 'skin_rash',
            'hives': 'skin_rash',
            'skin_irritation': 'skin_rash',
            'itch': 'itching',
            'itchiness': 'itching',
            'scratching': 'itching',
            'throat_pain': 'sore_throat',
            'painful_throat': 'sore_throat',
            'scratchy_throat': 'sore_throat',
            'lower_back_pain': 'back_pain',
            'lumbago': 'back_pain',
            'spine_pain': 'back_pain',
            'muscle_ache': 'joint_pain',
            'body_ache': 'joint_pain',
            'body_pain': 'joint_pain',
            'arthritis': 'joint_pain',
            'stiff_joints': 'joint_pain',
            'muscle_pain': 'muscle_weakness',
            'weak_muscles': 'muscle_weakness',
            'pins_and_needles': 'tingling',
            'prickling': 'tingling',
            'numb': 'numbness',
            'loss_of_sensation': 'numbness',
            # ENT
            'earache': 'ear_pain',
            'ear_infection': 'ear_pain',
            'hard_to_swallow': 'difficulty_swallowing',
            'trouble_swallowing': 'difficulty_swallowing',
            'dysphagia': 'difficulty_swallowing',
            'voice_change': 'hoarseness',
            'raspy_voice': 'hoarseness',
            'lost_voice': 'hoarseness',
            # Eyes
            'red_eyes': 'eye_redness',
            'bloodshot_eyes': 'eye_redness',
            'pink_eye': 'eye_redness',
            'eye_ache': 'eye_pain',
            'sore_eyes': 'eye_pain',
            'fuzzy_vision': 'blurred_vision',
            'poor_vision': 'blurred_vision',
            'vision_problems': 'blurred_vision',
            'cant_see_clearly': 'blurred_vision',
            # Urinary
            'peeing_a_lot': 'frequent_urination',
            'urinating_often': 'frequent_urination',
            'polyuria': 'frequent_urination',
            'burning_urination': 'painful_urination',
            'dysuria': 'painful_urination',
            'pain_when_peeing': 'painful_urination',
            'blood_in_pee': 'blood_in_urine',
            'hematuria': 'blood_in_urine',
            'very_thirsty': 'excessive_thirst',
            'polydipsia': 'excessive_thirst',
            'always_thirsty': 'excessive_thirst',
            'brown_urine': 'dark_urine',
            'tea_colored_urine': 'dark_urine',
            'light_colored_stool': 'pale_stool',
            'clay_colored_stool': 'pale_stool',
            # Skin & Other
            'yellow_skin': 'jaundice',
            'yellow_eyes': 'jaundice',
            'yellowing': 'jaundice',
            'easy_bruising': 'bruising',
            'bruise_easily': 'bruising',
            'gum_bleeding': 'bleeding_gums',
            'losing_hair': 'hair_loss',
            'balding': 'hair_loss',
            'thinning_hair': 'hair_loss',
            'flaky_skin': 'dry_skin',
            'rough_skin': 'dry_skin',
        }
        normalized = variations.get(symptom, symptom)
        if normalized in SYMPTOM_DIAGNOSIS_RULES:
            normalized_symptoms.append(normalized)

    if not normalized_symptoms:
        return []

    # Aggregate condition scores
    condition_scores = {}

    for symptom in normalized_symptoms:
        if symptom in SYMPTOM_DIAGNOSIS_RULES:
            for condition in SYMPTOM_DIAGNOSIS_RULES[symptom]['conditions']:
                name = condition['name']
                if name not in condition_scores:
                    condition_scores[name] = {
                        'score': 0,
                        'icd_code': condition['icd_code'],
                        'matched_symptoms': [],
                    }
                condition_scores[name]['score'] += condition['weight']
                condition_scores[name]['matched_symptoms'].append(symptom.replace('_', ' '))

    # Calculate confidence percentage (normalize by number of symptoms)
    max_possible_score = len(normalized_symptoms)  # Max 1.0 per symptom

    results = []
    for name, data in condition_scores.items():
        # Confidence based on weighted score relative to symptoms matched
        raw_confidence = (data['score'] / max_possible_score) * 100
        # Boost confidence if multiple symptoms match
        symptom_bonus = min(len(data['matched_symptoms']) * 5, 20)
        confidence = min(raw_confidence + symptom_bonus, 95)  # Cap at 95%

        results.append({
            'diagnosis': name,
            'icd_code': data['icd_code'],
            'confidence': round(confidence, 1),
            'matched_symptoms': data['matched_symptoms'],
            'symptom_count': len(data['matched_symptoms']),
        })

    # Sort by confidence and return top 5
    results.sort(key=lambda x: (-x['confidence'], -x['symptom_count']))
    return results[:5]


def get_symptom_keywords():
    """
    Get list of all recognized symptom keywords for autocomplete.

    Returns:
        list: Sorted list of symptom names
    """
    symptoms = list(SYMPTOM_DIAGNOSIS_RULES.keys())
    return sorted([s.replace('_', ' ').title() for s in symptoms])
