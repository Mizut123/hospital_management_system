"""
Management command to set up demo data for the Hospital Management System.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.accounts.models import Department, DoctorProfile
from apps.patients.models import Patient
from apps.pharmacy.models import Medicine, MedicineCategory, MedicineStock
from datetime import date, timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up demo data for HMS'

    def handle(self, *args, **options):
        self.stdout.write('Setting up demo data...')

        # Create departments
        departments = [
            ('General Medicine', 'General medical consultations and primary care'),
            ('Cardiology', 'Heart and cardiovascular system specialists'),
            ('Pediatrics', 'Medical care for infants, children, and adolescents'),
            ('Orthopedics', 'Musculoskeletal system specialists'),
            ('Dermatology', 'Skin, hair, and nail specialists'),
        ]

        for name, desc in departments:
            Department.objects.get_or_create(name=name, defaults={'description': desc})
        self.stdout.write(self.style.SUCCESS(f'Created {len(departments)} departments'))

        # Create demo users
        demo_users = [
            ('admin@hospital.com', 'Admin', 'User', 'admin', None),
            ('doctor@hospital.com', 'John', 'Smith', 'doctor', 'General Medicine'),
            ('doctor2@hospital.com', 'Sarah', 'Johnson', 'doctor', 'Cardiology'),
            ('reception@hospital.com', 'Mary', 'Wilson', 'receptionist', None),
            ('pharmacy@hospital.com', 'James', 'Brown', 'pharmacist', None),
            ('patient@hospital.com', 'Robert', 'Davis', 'patient', None),
            ('patient2@hospital.com', 'Emily', 'Taylor', 'patient', None),
        ]

        for email, first, last, role, dept_name in demo_users:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'role': role,
                    'phone': '555-0100',
                    'is_active': True,
                }
            )
            if created:
                user.set_password('demo123')
                user.save()

                # Create doctor profile if doctor
                if role == 'doctor' and dept_name:
                    dept = Department.objects.get(name=dept_name)
                    DoctorProfile.objects.create(
                        user=user,
                        department=dept,
                        specialization=dept_name,
                        qualification='MD, MBBS',
                        license_number=f'LIC{user.pk:06d}',
                        experience_years=10,
                    )

                # Create patient profile if patient
                if role == 'patient':
                    Patient.objects.create(
                        user=user,
                        blood_group='O+',
                        allergies='None known',
                    )

        self.stdout.write(self.style.SUCCESS(f'Created demo users'))

        # Create medicine categories
        categories = [
            ('Antibiotics', 'Medications used to treat bacterial infections'),
            ('Analgesics', 'Pain relief medications'),
            ('Cardiovascular', 'Heart and blood vessel medications'),
            ('Vitamins', 'Nutritional supplements'),
            ('Antihistamines', 'Allergy medications'),
        ]

        for name, desc in categories:
            MedicineCategory.objects.get_or_create(name=name, defaults={'description': desc})

        # Create sample medicines
        medicines_data = [
            ('Amoxicillin', 'Amoxicillin', 'Antibiotics', 'capsule', '500mg'),
            ('Paracetamol', 'Acetaminophen', 'Analgesics', 'tablet', '500mg'),
            ('Ibuprofen', 'Ibuprofen', 'Analgesics', 'tablet', '400mg'),
            ('Aspirin', 'Acetylsalicylic acid', 'Cardiovascular', 'tablet', '100mg'),
            ('Vitamin C', 'Ascorbic acid', 'Vitamins', 'tablet', '1000mg'),
            ('Cetirizine', 'Cetirizine', 'Antihistamines', 'tablet', '10mg'),
            ('Omeprazole', 'Omeprazole', 'Analgesics', 'capsule', '20mg'),
            ('Metformin', 'Metformin', 'Cardiovascular', 'tablet', '500mg'),
        ]

        for name, generic, cat_name, form, strength in medicines_data:
            category = MedicineCategory.objects.get(name=cat_name)
            med, created = Medicine.objects.get_or_create(
                name=name,
                defaults={
                    'generic_name': generic,
                    'category': category,
                    'dosage_form': form,
                    'strength': strength,
                    'manufacturer': 'Generic Pharma',
                }
            )

            if created:
                # Create stock entry
                MedicineStock.objects.create(
                    medicine=med,
                    batch_number=f'BATCH{med.pk:04d}',
                    quantity=100,
                    expiry_date=date.today() + timedelta(days=365),
                    received_date=date.today(),
                    reorder_level=20,
                )

        self.stdout.write(self.style.SUCCESS(f'Created sample medicines'))
        self.stdout.write(self.style.SUCCESS('Demo setup complete!'))
        self.stdout.write('')
        self.stdout.write('Demo accounts (password: demo123):')
        self.stdout.write('  Admin: admin@hospital.com')
        self.stdout.write('  Doctor: doctor@hospital.com')
        self.stdout.write('  Receptionist: reception@hospital.com')
        self.stdout.write('  Pharmacist: pharmacy@hospital.com')
        self.stdout.write('  Patient: patient@hospital.com')
