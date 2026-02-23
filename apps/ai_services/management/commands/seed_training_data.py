"""
Management command to seed initial training data for the ML disease prediction model.

Creates realistic symptom-diagnosis training records so the model can be
trained even before doctors start confirming diagnoses in production.

Usage:
    python manage.py seed_training_data
    python manage.py seed_training_data --count 200
    python manage.py seed_training_data --train  (seeds + trains a model)
"""
import random
from django.core.management.base import BaseCommand
from apps.ai_services.models import TrainingData


# Realistic disease profiles: symptoms, age ranges, gender tendencies, vitals
DISEASE_PROFILES = [
    {
        'disease': 'Influenza (Flu)',
        'icd_code': 'J11.1',
        'symptoms_pool': ['fever', 'cough', 'headache', 'fatigue', 'chills',
                          'muscle_weakness', 'sore_throat', 'runny_nose', 'sneezing',
                          'loss_of_appetite', 'night_sweats'],
        'required_symptoms': ['fever', 'cough'],
        'age_range': (5, 80),
        'gender_weights': {'male': 0.5, 'female': 0.5},
        'vitals': {'temp': (38.0, 40.0), 'hr': (80, 110), 'bp_sys': (110, 130),
                   'bp_dia': (70, 85), 'spo2': (94, 98)},
    },
    {
        'disease': 'Common Cold',
        'icd_code': 'J00',
        'symptoms_pool': ['cough', 'runny_nose', 'sneezing', 'sore_throat',
                          'nasal_congestion', 'headache', 'fatigue', 'fever'],
        'required_symptoms': ['runny_nose', 'cough'],
        'age_range': (3, 70),
        'gender_weights': {'male': 0.5, 'female': 0.5},
        'vitals': {'temp': (36.8, 38.0), 'hr': (70, 90), 'bp_sys': (110, 130),
                   'bp_dia': (70, 85), 'spo2': (96, 99)},
    },
    {
        'disease': 'Pneumonia',
        'icd_code': 'J18.9',
        'symptoms_pool': ['cough', 'fever', 'shortness_of_breath', 'chest_pain',
                          'fatigue', 'chills', 'night_sweats', 'loss_of_appetite'],
        'required_symptoms': ['cough', 'fever', 'shortness_of_breath'],
        'age_range': (20, 85),
        'gender_weights': {'male': 0.55, 'female': 0.45},
        'vitals': {'temp': (38.5, 40.5), 'hr': (90, 120), 'bp_sys': (100, 130),
                   'bp_dia': (60, 85), 'spo2': (88, 95)},
    },
    {
        'disease': 'Malaria',
        'icd_code': 'B54',
        'symptoms_pool': ['fever', 'chills', 'headache', 'nausea', 'vomiting',
                          'fatigue', 'muscle_weakness', 'night_sweats', 'loss_of_appetite'],
        'required_symptoms': ['fever', 'chills'],
        'age_range': (5, 70),
        'gender_weights': {'male': 0.5, 'female': 0.5},
        'vitals': {'temp': (38.5, 41.0), 'hr': (85, 120), 'bp_sys': (95, 125),
                   'bp_dia': (60, 80), 'spo2': (92, 97)},
    },
    {
        'disease': 'Gastroenteritis',
        'icd_code': 'K52.9',
        'symptoms_pool': ['nausea', 'vomiting', 'diarrhea', 'abdominal_pain',
                          'fever', 'fatigue', 'loss_of_appetite', 'bloating'],
        'required_symptoms': ['diarrhea', 'nausea'],
        'age_range': (5, 75),
        'gender_weights': {'male': 0.5, 'female': 0.5},
        'vitals': {'temp': (37.0, 39.0), 'hr': (80, 110), 'bp_sys': (100, 130),
                   'bp_dia': (65, 85), 'spo2': (96, 99)},
    },
    {
        'disease': 'Hypertension',
        'icd_code': 'I10',
        'symptoms_pool': ['headache', 'dizziness', 'blurred_vision', 'chest_pain',
                          'shortness_of_breath', 'palpitations', 'fatigue', 'nausea'],
        'required_symptoms': ['headache'],
        'age_range': (35, 80),
        'gender_weights': {'male': 0.55, 'female': 0.45},
        'vitals': {'temp': (36.5, 37.2), 'hr': (75, 100), 'bp_sys': (145, 190),
                   'bp_dia': (90, 120), 'spo2': (95, 99)},
    },
    {
        'disease': 'Diabetes Mellitus',
        'icd_code': 'E14',
        'symptoms_pool': ['excessive_thirst', 'frequent_urination', 'fatigue',
                          'blurred_vision', 'weight_loss', 'numbness', 'tingling',
                          'loss_of_appetite'],
        'required_symptoms': ['excessive_thirst', 'frequent_urination'],
        'age_range': (30, 80),
        'gender_weights': {'male': 0.55, 'female': 0.45},
        'vitals': {'temp': (36.5, 37.2), 'hr': (70, 95), 'bp_sys': (120, 150),
                   'bp_dia': (75, 95), 'spo2': (95, 99)},
    },
    {
        'disease': 'Asthma',
        'icd_code': 'J45.9',
        'symptoms_pool': ['shortness_of_breath', 'wheezing', 'cough',
                          'chest_tightness', 'fatigue'],
        'required_symptoms': ['shortness_of_breath', 'wheezing'],
        'age_range': (8, 65),
        'gender_weights': {'male': 0.45, 'female': 0.55},
        'vitals': {'temp': (36.5, 37.3), 'hr': (85, 115), 'bp_sys': (110, 135),
                   'bp_dia': (70, 90), 'spo2': (89, 96)},
    },
    {
        'disease': 'Urinary Tract Infection',
        'icd_code': 'N39.0',
        'symptoms_pool': ['painful_urination', 'frequent_urination', 'fever',
                          'abdominal_pain', 'blood_in_urine', 'chills', 'dark_urine'],
        'required_symptoms': ['painful_urination', 'frequent_urination'],
        'age_range': (18, 70),
        'gender_weights': {'male': 0.2, 'female': 0.8},
        'vitals': {'temp': (37.0, 39.0), 'hr': (75, 100), 'bp_sys': (110, 135),
                   'bp_dia': (70, 85), 'spo2': (96, 99)},
    },
    {
        'disease': 'Migraine',
        'icd_code': 'G43.9',
        'symptoms_pool': ['headache', 'nausea', 'blurred_vision', 'dizziness',
                          'fatigue', 'insomnia', 'vomiting'],
        'required_symptoms': ['headache'],
        'age_range': (15, 60),
        'gender_weights': {'male': 0.3, 'female': 0.7},
        'vitals': {'temp': (36.4, 37.2), 'hr': (65, 90), 'bp_sys': (110, 135),
                   'bp_dia': (70, 85), 'spo2': (97, 99)},
    },
    {
        'disease': 'Gastritis',
        'icd_code': 'K29.7',
        'symptoms_pool': ['abdominal_pain', 'nausea', 'vomiting', 'bloating',
                          'loss_of_appetite', 'fatigue'],
        'required_symptoms': ['abdominal_pain', 'nausea'],
        'age_range': (20, 70),
        'gender_weights': {'male': 0.5, 'female': 0.5},
        'vitals': {'temp': (36.5, 37.5), 'hr': (70, 90), 'bp_sys': (110, 130),
                   'bp_dia': (70, 85), 'spo2': (96, 99)},
    },
    {
        'disease': 'Anemia',
        'icd_code': 'D64.9',
        'symptoms_pool': ['fatigue', 'dizziness', 'shortness_of_breath',
                          'palpitations', 'muscle_weakness', 'headache', 'pale_stool'],
        'required_symptoms': ['fatigue', 'dizziness'],
        'age_range': (15, 70),
        'gender_weights': {'male': 0.3, 'female': 0.7},
        'vitals': {'temp': (36.3, 37.0), 'hr': (85, 110), 'bp_sys': (95, 120),
                   'bp_dia': (60, 80), 'spo2': (93, 97)},
    },
    {
        'disease': 'Typhoid Fever',
        'icd_code': 'A01.0',
        'symptoms_pool': ['fever', 'headache', 'abdominal_pain', 'fatigue',
                          'diarrhea', 'loss_of_appetite', 'constipation', 'chills'],
        'required_symptoms': ['fever', 'headache'],
        'age_range': (10, 60),
        'gender_weights': {'male': 0.5, 'female': 0.5},
        'vitals': {'temp': (38.5, 40.5), 'hr': (70, 95), 'bp_sys': (100, 125),
                   'bp_dia': (65, 80), 'spo2': (95, 98)},
    },
    {
        'disease': 'Allergic Dermatitis',
        'icd_code': 'L23.9',
        'symptoms_pool': ['skin_rash', 'itching', 'dry_skin', 'swelling',
                          'eye_redness'],
        'required_symptoms': ['skin_rash', 'itching'],
        'age_range': (5, 65),
        'gender_weights': {'male': 0.5, 'female': 0.5},
        'vitals': {'temp': (36.5, 37.2), 'hr': (70, 85), 'bp_sys': (110, 130),
                   'bp_dia': (70, 85), 'spo2': (97, 99)},
    },
    {
        'disease': 'Depression',
        'icd_code': 'F32.9',
        'symptoms_pool': ['fatigue', 'insomnia', 'loss_of_appetite', 'anxiety',
                          'depression', 'headache', 'weight_loss', 'confusion'],
        'required_symptoms': ['depression', 'fatigue'],
        'age_range': (18, 70),
        'gender_weights': {'male': 0.4, 'female': 0.6},
        'vitals': {'temp': (36.3, 37.0), 'hr': (60, 85), 'bp_sys': (105, 130),
                   'bp_dia': (65, 85), 'spo2': (97, 99)},
    },
    {
        'disease': 'Osteoarthritis',
        'icd_code': 'M19.9',
        'symptoms_pool': ['joint_pain', 'muscle_weakness', 'numbness',
                          'back_pain', 'swelling', 'fatigue'],
        'required_symptoms': ['joint_pain'],
        'age_range': (45, 80),
        'gender_weights': {'male': 0.45, 'female': 0.55},
        'vitals': {'temp': (36.5, 37.2), 'hr': (65, 85), 'bp_sys': (115, 140),
                   'bp_dia': (70, 90), 'spo2': (96, 99)},
    },
    {
        'disease': 'Anxiety Disorder',
        'icd_code': 'F41.9',
        'symptoms_pool': ['anxiety', 'palpitations', 'insomnia', 'dizziness',
                          'shortness_of_breath', 'nausea', 'tremor', 'chest_pain'],
        'required_symptoms': ['anxiety', 'palpitations'],
        'age_range': (18, 60),
        'gender_weights': {'male': 0.4, 'female': 0.6},
        'vitals': {'temp': (36.5, 37.2), 'hr': (85, 115), 'bp_sys': (115, 145),
                   'bp_dia': (75, 95), 'spo2': (96, 99)},
    },
    {
        'disease': 'COPD',
        'icd_code': 'J44.9',
        'symptoms_pool': ['cough', 'shortness_of_breath', 'wheezing',
                          'chest_tightness', 'fatigue', 'weight_loss'],
        'required_symptoms': ['cough', 'shortness_of_breath'],
        'age_range': (45, 80),
        'gender_weights': {'male': 0.6, 'female': 0.4},
        'vitals': {'temp': (36.5, 37.5), 'hr': (80, 110), 'bp_sys': (110, 140),
                   'bp_dia': (70, 90), 'spo2': (85, 94)},
    },
    {
        'disease': 'Kidney Stones',
        'icd_code': 'N20.0',
        'symptoms_pool': ['back_pain', 'abdominal_pain', 'painful_urination',
                          'blood_in_urine', 'nausea', 'vomiting', 'fever'],
        'required_symptoms': ['back_pain', 'painful_urination'],
        'age_range': (25, 65),
        'gender_weights': {'male': 0.65, 'female': 0.35},
        'vitals': {'temp': (36.5, 38.0), 'hr': (80, 110), 'bp_sys': (120, 150),
                   'bp_dia': (75, 95), 'spo2': (96, 99)},
    },
    {
        'disease': 'Hepatitis',
        'icd_code': 'K75.9',
        'symptoms_pool': ['jaundice', 'fatigue', 'nausea', 'abdominal_pain',
                          'loss_of_appetite', 'dark_urine', 'pale_stool', 'fever'],
        'required_symptoms': ['jaundice', 'fatigue'],
        'age_range': (20, 65),
        'gender_weights': {'male': 0.55, 'female': 0.45},
        'vitals': {'temp': (37.0, 38.5), 'hr': (70, 95), 'bp_sys': (105, 130),
                   'bp_dia': (65, 85), 'spo2': (95, 98)},
    },
]


def generate_record(profile):
    """Generate a single realistic training record from a disease profile."""
    # Select symptoms: required + random subset of optional
    symptoms = list(profile['required_symptoms'])
    optional = [s for s in profile['symptoms_pool'] if s not in symptoms]
    extra_count = random.randint(1, min(3, len(optional)))
    symptoms.extend(random.sample(optional, extra_count))
    random.shuffle(symptoms)

    # Demographics
    age = random.randint(*profile['age_range'])
    gender_roll = random.random()
    gender = 'male' if gender_roll < profile['gender_weights']['male'] else 'female'

    # Vitals with slight randomization
    vitals = profile['vitals']
    temp = round(random.uniform(*vitals['temp']), 1)
    hr = random.randint(*vitals['hr'])
    bp_sys = random.randint(*vitals['bp_sys'])
    bp_dia = random.randint(*vitals['bp_dia'])
    spo2 = random.randint(*vitals['spo2'])

    return {
        'symptoms': ','.join(symptoms),
        'confirmed_disease': profile['disease'],
        'icd_code': profile['icd_code'],
        'patient_age': age,
        'patient_gender': gender,
        'temperature': temp,
        'heart_rate': hr,
        'blood_pressure_systolic': bp_sys,
        'blood_pressure_diastolic': bp_dia,
        'spo2': spo2,
    }


class Command(BaseCommand):
    help = 'Seed initial training data for the ML disease prediction model.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count', type=int, default=150,
            help='Total number of training records to create (default: 150)'
        )
        parser.add_argument(
            '--train', action='store_true',
            help='Train a model immediately after seeding data'
        )
        parser.add_argument(
            '--clear', action='store_true',
            help='Clear existing training data before seeding'
        )

    def handle(self, *args, **options):
        count = options['count']
        do_train = options['train']
        do_clear = options['clear']

        if do_clear:
            deleted, _ = TrainingData.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Cleared {deleted} existing training records."))

        # Distribute records across disease profiles
        records_per_disease = max(count // len(DISEASE_PROFILES), 3)
        remainder = count - (records_per_disease * len(DISEASE_PROFILES))

        created = 0
        for profile in DISEASE_PROFILES:
            n = records_per_disease + (1 if remainder > 0 else 0)
            remainder -= 1

            for _ in range(n):
                data = generate_record(profile)
                TrainingData.objects.create(
                    symptoms=data['symptoms'],
                    confirmed_disease=data['confirmed_disease'],
                    icd_code=data['icd_code'],
                    patient_age=data['patient_age'],
                    patient_gender=data['patient_gender'],
                    temperature=data['temperature'],
                    heart_rate=data['heart_rate'],
                    blood_pressure_systolic=data['blood_pressure_systolic'],
                    blood_pressure_diastolic=data['blood_pressure_diastolic'],
                    spo2=data['spo2'],
                    predicted_disease='',
                    prediction_correct=False,
                    used_for_training=False,
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Created {created} training records across {len(DISEASE_PROFILES)} diseases."
        ))

        # Show distribution
        self.stdout.write("\nDisease distribution:")
        for profile in DISEASE_PROFILES:
            n = TrainingData.objects.filter(confirmed_disease=profile['disease']).count()
            self.stdout.write(f"  {profile['disease']}: {n} records")

        if do_train:
            self.stdout.write("\nTraining model...")
            try:
                from apps.ai_services.ml_pipeline import train_model
                model = train_model()
                self.stdout.write(self.style.SUCCESS(
                    f"Model {model.version} trained! "
                    f"Accuracy: {model.accuracy:.1%}, "
                    f"Classes: {model.num_classes}, "
                    f"Samples: {model.training_samples}"
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Training failed: {e}"))
