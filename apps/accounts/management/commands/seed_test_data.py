"""
Comprehensive test data seeder for the Hospital Management System.
Creates realistic data across ALL modules to test every function.

Usage:
    python manage.py seed_test_data          # Seed everything
    python manage.py seed_test_data --clear  # Clear existing data first
"""
import json
import os
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Department, DoctorProfile, DoctorSchedule, AuditLog
from apps.patients.models import Patient, PatientDocument
from apps.appointments.models import Appointment, AppointmentSlot
from apps.medical_records.models import (
    MedicalRecord, Diagnosis, Prescription, PrescriptionItem, LabTest,
)
from apps.pharmacy.models import (
    MedicineCategory, Medicine, MedicineStock, StockTransaction,
)
from apps.notifications.models import Notification
from apps.ai_services.models import TrainingData, MLModelVersion, PredictionLog

User = get_user_model()

# ────────────────────────────────────────────────────────────────
# Constants & Reference Data
# ────────────────────────────────────────────────────────────────

DEPARTMENTS = [
    ('Emergency Medicine', 'Emergency and acute care services'),
    ('Intensive Care Unit', 'Critical care for seriously ill patients'),
    ('General Surgery', 'Surgical procedures and post-operative care'),
    ('Cardiology', 'Heart and cardiovascular system specialists'),
    ('OB-GYN', 'Obstetrics and gynecology services'),
    ('Pediatrics', 'Medical care for children and adolescents'),
    ('Orthopedics', 'Bone, joint, and musculoskeletal care'),
    ('Neurology', 'Brain and nervous system disorders'),
    ('Radiology', 'Diagnostic imaging services'),
    ('Internal Medicine', 'General internal medicine and primary care'),
    ('Dermatology', 'Skin, hair, and nail conditions'),
    ('Ophthalmology', 'Eye care and vision specialists'),
    ('ENT', 'Ear, nose, and throat specialists'),
    ('Psychiatry', 'Mental health and behavioral disorders'),
    ('Oncology', 'Cancer diagnosis and treatment'),
    ('Nephrology', 'Kidney disease specialists'),
    ('Urology', 'Urinary tract and male reproductive system'),
    ('Gastroenterology', 'Digestive system disorders'),
    ('Pulmonology', 'Lung and respiratory conditions'),
    ('Endocrinology', 'Hormonal and metabolic disorders'),
]

DOCTORS_DATA = [
    # (email, first, last, department, specialization, qualification, license, exp_years, fee)
    ('dr.ahmed@hospital.com', 'Ahmed', 'Al-Rashid', 'Internal Medicine', 'General Practice', 'MD, MBBS', 'LIC-001', 15, 150),
    ('dr.fatima@hospital.com', 'Fatima', 'Hassan', 'Cardiology', 'Interventional Cardiology', 'MD, DM Cardiology', 'LIC-002', 12, 250),
    ('dr.omar@hospital.com', 'Omar', 'Khalil', 'Orthopedics', 'Joint Replacement', 'MS Ortho, MBBS', 'LIC-003', 18, 200),
    ('dr.sarah@hospital.com', 'Sarah', 'Ibrahim', 'Pediatrics', 'Neonatology', 'MD Pediatrics, DCH', 'LIC-004', 8, 180),
    ('dr.yusuf@hospital.com', 'Yusuf', 'Mansour', 'Neurology', 'Stroke Medicine', 'DM Neurology, MD', 'LIC-005', 20, 300),
    ('dr.layla@hospital.com', 'Layla', 'Nasser', 'Dermatology', 'Cosmetic Dermatology', 'MD Dermatology', 'LIC-006', 6, 175),
    ('dr.hassan@hospital.com', 'Hassan', 'Farooq', 'General Surgery', 'Laparoscopic Surgery', 'MS Surgery, MBBS', 'LIC-007', 14, 275),
    ('dr.amira@hospital.com', 'Amira', 'Zayed', 'OB-GYN', 'High-Risk Pregnancy', 'MD OB-GYN', 'LIC-008', 10, 225),
    ('dr.karim@hospital.com', 'Karim', 'Bakri', 'Psychiatry', 'Child Psychiatry', 'MD Psychiatry', 'LIC-009', 9, 200),
    ('dr.nadia@hospital.com', 'Nadia', 'Saleh', 'Gastroenterology', 'Hepatology', 'DM Gastro, MD', 'LIC-010', 11, 250),
    ('dr.tariq@hospital.com', 'Tariq', 'Mahmoud', 'Pulmonology', 'Sleep Medicine', 'DM Pulmonology', 'LIC-011', 7, 200),
    ('dr.hana@hospital.com', 'Hana', 'Qureshi', 'Endocrinology', 'Diabetes Management', 'DM Endocrinology', 'LIC-012', 13, 225),
    ('dr.rami@hospital.com', 'Rami', 'Othman', 'Oncology', 'Medical Oncology', 'DM Oncology, MD', 'LIC-013', 16, 350),
    ('dr.dina@hospital.com', 'Dina', 'Khoury', 'Nephrology', 'Dialysis', 'DM Nephrology', 'LIC-014', 10, 250),
    ('dr.ali@hospital.com', 'Ali', 'Hadid', 'Emergency Medicine', 'Trauma', 'MD Emergency Medicine', 'LIC-015', 12, 200),
]

PATIENTS_DATA = [
    # (email, first, last, gender, dob, phone, blood_group, allergies, chronic_conditions, national_id)
    ('patient.john@email.com', 'John', 'Williams', 'male', '1985-03-15', '555-1001', 'A+', 'Penicillin', 'Hypertension', 'NID10001'),
    ('patient.mary@email.com', 'Mary', 'Johnson', 'female', '1990-07-22', '555-1002', 'B+', 'None', '', 'NID10002'),
    ('patient.david@email.com', 'David', 'Brown', 'male', '1978-11-08', '555-1003', 'O+', 'Sulfa drugs', 'Type 2 Diabetes, Hypertension', 'NID10003'),
    ('patient.emma@email.com', 'Emma', 'Davis', 'female', '1995-01-30', '555-1004', 'AB+', 'Latex', '', 'NID10004'),
    ('patient.michael@email.com', 'Michael', 'Wilson', 'male', '1965-06-12', '555-1005', 'A-', 'Aspirin', 'COPD, Coronary Artery Disease', 'NID10005'),
    ('patient.sophia@email.com', 'Sophia', 'Martinez', 'female', '1988-09-25', '555-1006', 'O-', 'None', 'Asthma', 'NID10006'),
    ('patient.james@email.com', 'James', 'Anderson', 'male', '1972-04-18', '555-1007', 'B-', 'Ibuprofen', 'Chronic Kidney Disease', 'NID10007'),
    ('patient.olivia@email.com', 'Olivia', 'Taylor', 'female', '2000-12-05', '555-1008', 'AB-', 'None', '', 'NID10008'),
    ('patient.robert@email.com', 'Robert', 'Thomas', 'male', '1955-08-20', '555-1009', 'O+', 'Codeine', 'Atrial Fibrillation, Hypertension, Diabetes', 'NID10009'),
    ('patient.lisa@email.com', 'Lisa', 'Jackson', 'female', '1982-02-14', '555-1010', 'A+', 'Peanuts', 'Hypothyroidism', 'NID10010'),
    ('patient.daniel@email.com', 'Daniel', 'White', 'male', '1998-05-07', '555-1011', 'B+', 'None', '', 'NID10011'),
    ('patient.jennifer@email.com', 'Jennifer', 'Harris', 'female', '1975-10-31', '555-1012', 'O+', 'Morphine', 'Rheumatoid Arthritis', 'NID10012'),
    ('patient.william@email.com', 'William', 'Clark', 'male', '1960-01-25', '555-1013', 'A+', 'None', 'Heart Failure, Diabetes', 'NID10013'),
    ('patient.sarah@email.com', 'Sarah', 'Lewis', 'female', '1993-08-16', '555-1014', 'AB+', 'Shellfish', 'Migraine', 'NID10014'),
    ('patient.thomas@email.com', 'Thomas', 'Robinson', 'male', '1987-12-03', '555-1015', 'B-', 'None', 'Anxiety Disorder', 'NID10015'),
    ('patient.angela@email.com', 'Angela', 'Walker', 'female', '1970-04-09', '555-1016', 'O-', 'Erythromycin', 'Osteoporosis, Hypertension', 'NID10016'),
    ('patient.christopher@email.com', 'Christopher', 'Hall', 'male', '2005-06-20', '555-1017', 'A-', 'None', '', 'NID10017'),
    ('patient.karen@email.com', 'Karen', 'Allen', 'female', '1968-09-11', '555-1018', 'B+', 'Metformin', 'Chronic Liver Disease', 'NID10018'),
    ('patient.joseph@email.com', 'Joseph', 'Young', 'male', '1992-03-28', '555-1019', 'O+', 'None', 'Epilepsy', 'NID10019'),
    ('patient.nancy@email.com', 'Nancy', 'King', 'female', '1983-07-04', '555-1020', 'AB-', 'Contrast dye', 'Polycystic Ovary Syndrome', 'NID10020'),
    ('patient.mark@email.com', 'Mark', 'Wright', 'male', '1958-11-15', '555-1021', 'A+', 'Penicillin, Sulfa', 'Parkinson\'s Disease', 'NID10021'),
    ('patient.patricia@email.com', 'Patricia', 'Lopez', 'female', '1980-05-22', '555-1022', 'O+', 'None', 'Depression, Anxiety', 'NID10022'),
    ('patient.charles@email.com', 'Charles', 'Hill', 'male', '1974-08-30', '555-1023', 'B+', 'NSAIDs', 'Gout, Hypertension', 'NID10023'),
    ('patient.linda@email.com', 'Linda', 'Scott', 'female', '1996-02-18', '555-1024', 'AB+', 'None', '', 'NID10024'),
    ('patient.steven@email.com', 'Steven', 'Green', 'male', '1963-10-07', '555-1025', 'O-', 'Amoxicillin', 'GERD, Barrett\'s Esophagus', 'NID10025'),
    ('patient.betty@email.com', 'Betty', 'Adams', 'female', '1950-12-24', '555-1026', 'A-', 'None', 'Osteoarthritis, Hypertension, Diabetes', 'NID10026'),
    ('patient.paul@email.com', 'Paul', 'Baker', 'male', '1991-06-13', '555-1027', 'B-', 'Latex', 'Psoriasis', 'NID10027'),
    ('patient.sandra@email.com', 'Sandra', 'Nelson', 'female', '1977-03-06', '555-1028', 'O+', 'Codeine, Morphine', 'Fibromyalgia', 'NID10028'),
    ('patient.kevin@email.com', 'Kevin', 'Carter', 'male', '2001-09-19', '555-1029', 'A+', 'None', '', 'NID10029'),
    ('patient.margaret@email.com', 'Margaret', 'Mitchell', 'female', '1945-04-02', '555-1030', 'B+', 'ACE inhibitors', 'CHF, CKD Stage 3, Diabetes', 'NID10030'),
]

MEDICINE_CATEGORIES = [
    ('Antibiotics', 'Medications to treat bacterial infections'),
    ('Analgesics', 'Pain relief medications'),
    ('Cardiovascular', 'Heart and blood vessel medications'),
    ('Antidiabetics', 'Blood sugar management medications'),
    ('Antihypertensives', 'Blood pressure management medications'),
    ('Gastrointestinal', 'Digestive system medications'),
    ('Respiratory', 'Lung and airway medications'),
    ('Antihistamines', 'Allergy and immune response medications'),
    ('Neurological', 'Brain and nervous system medications'),
    ('Psychiatric', 'Mental health medications'),
    ('Vitamins & Supplements', 'Nutritional supplements'),
    ('Dermatological', 'Skin treatment medications'),
    ('Emergency Medicines', 'Critical care and emergency drugs'),
    ('Hormonal', 'Hormone therapy medications'),
    ('Musculoskeletal', 'Muscle and joint medications'),
]

MEDICINES_DATA = [
    # (name, generic, category, form, strength, manufacturer, requires_rx, contraindications, side_effects, storage)
    ('Amoxicillin 500mg', 'Amoxicillin', 'Antibiotics', 'capsule', '500mg', 'GlaxoSmithKline', True, 'Penicillin allergy', 'Nausea, diarrhea, rash', 'Store below 25°C'),
    ('Azithromycin 250mg', 'Azithromycin', 'Antibiotics', 'tablet', '250mg', 'Pfizer', True, 'Liver disease', 'Abdominal pain, nausea', 'Store below 30°C'),
    ('Ciprofloxacin 500mg', 'Ciprofloxacin', 'Antibiotics', 'tablet', '500mg', 'Bayer', True, 'Pregnancy, children <18', 'Tendon pain, nausea', 'Store below 25°C'),
    ('Metronidazole 400mg', 'Metronidazole', 'Antibiotics', 'tablet', '400mg', 'Sanofi', True, 'Alcohol use', 'Metallic taste, nausea', 'Protect from light'),
    ('Doxycycline 100mg', 'Doxycycline', 'Antibiotics', 'capsule', '100mg', 'Pfizer', True, 'Pregnancy', 'Photosensitivity, nausea', 'Store below 25°C'),
    ('Cephalexin 500mg', 'Cephalexin', 'Antibiotics', 'capsule', '500mg', 'Ranbaxy', True, 'Cephalosporin allergy', 'Diarrhea, abdominal pain', 'Store below 25°C'),

    ('Paracetamol 500mg', 'Acetaminophen', 'Analgesics', 'tablet', '500mg', 'GSK', False, 'Liver disease', 'Rare at normal doses', 'Store below 30°C'),
    ('Ibuprofen 400mg', 'Ibuprofen', 'Analgesics', 'tablet', '400mg', 'Abbott', False, 'Peptic ulcer, renal failure', 'GI upset, dizziness', 'Store below 25°C'),
    ('Diclofenac 50mg', 'Diclofenac Sodium', 'Analgesics', 'tablet', '50mg', 'Novartis', True, 'GI bleeding, aspirin allergy', 'GI upset, headache', 'Store below 30°C'),
    ('Tramadol 50mg', 'Tramadol HCl', 'Analgesics', 'capsule', '50mg', 'Grunenthal', True, 'Seizure disorders', 'Drowsiness, constipation', 'Store below 25°C'),
    ('Aspirin 100mg', 'Acetylsalicylic Acid', 'Analgesics', 'tablet', '100mg', 'Bayer', False, 'Bleeding disorders, children', 'GI upset, bleeding', 'Store in dry place'),

    ('Atorvastatin 20mg', 'Atorvastatin', 'Cardiovascular', 'tablet', '20mg', 'Pfizer', True, 'Liver disease, pregnancy', 'Muscle pain, headache', 'Store below 30°C'),
    ('Clopidogrel 75mg', 'Clopidogrel', 'Cardiovascular', 'tablet', '75mg', 'Sanofi', True, 'Active bleeding', 'Bleeding, bruising', 'Store below 25°C'),
    ('Warfarin 5mg', 'Warfarin Sodium', 'Cardiovascular', 'tablet', '5mg', 'Bristol-Myers', True, 'Pregnancy, active bleeding', 'Bleeding, bruising', 'Protect from light'),
    ('Digoxin 0.25mg', 'Digoxin', 'Cardiovascular', 'tablet', '0.25mg', 'Aspen', True, 'Heart block, hypokalemia', 'Nausea, visual changes', 'Store below 25°C'),

    ('Metformin 500mg', 'Metformin HCl', 'Antidiabetics', 'tablet', '500mg', 'Merck', True, 'Renal failure, acidosis', 'GI upset, lactic acidosis', 'Store below 30°C'),
    ('Glibenclamide 5mg', 'Glibenclamide', 'Antidiabetics', 'tablet', '5mg', 'Sanofi', True, 'Type 1 diabetes', 'Hypoglycemia, weight gain', 'Store below 30°C'),
    ('Insulin Glargine', 'Insulin Glargine', 'Antidiabetics', 'injection', '100IU/ml', 'Sanofi', True, 'Hypoglycemia', 'Hypoglycemia, injection site', 'Refrigerate 2-8°C'),

    ('Amlodipine 5mg', 'Amlodipine', 'Antihypertensives', 'tablet', '5mg', 'Pfizer', True, 'Severe aortic stenosis', 'Ankle swelling, flushing', 'Store below 30°C'),
    ('Lisinopril 10mg', 'Lisinopril', 'Antihypertensives', 'tablet', '10mg', 'AstraZeneca', True, 'Pregnancy, angioedema', 'Dry cough, dizziness', 'Store below 30°C'),
    ('Losartan 50mg', 'Losartan', 'Antihypertensives', 'tablet', '50mg', 'Merck', True, 'Pregnancy', 'Dizziness, hyperkalemia', 'Store below 30°C'),
    ('Metoprolol 50mg', 'Metoprolol', 'Antihypertensives', 'tablet', '50mg', 'AstraZeneca', True, 'Severe bradycardia, asthma', 'Fatigue, cold extremities', 'Protect from moisture'),
    ('Hydrochlorothiazide 25mg', 'HCTZ', 'Antihypertensives', 'tablet', '25mg', 'Novartis', True, 'Anuria, sulfa allergy', 'Hypokalemia, dizziness', 'Store below 30°C'),

    ('Omeprazole 20mg', 'Omeprazole', 'Gastrointestinal', 'capsule', '20mg', 'AstraZeneca', True, 'None significant', 'Headache, GI upset', 'Store below 25°C'),
    ('Pantoprazole 40mg', 'Pantoprazole', 'Gastrointestinal', 'tablet', '40mg', 'Pfizer', True, 'None significant', 'Headache, diarrhea', 'Store below 25°C'),
    ('Ondansetron 4mg', 'Ondansetron', 'Gastrointestinal', 'tablet', '4mg', 'Novartis', True, 'QT prolongation', 'Headache, constipation', 'Store below 30°C'),
    ('Loperamide 2mg', 'Loperamide', 'Gastrointestinal', 'capsule', '2mg', 'Johnson & Johnson', False, 'Bloody diarrhea', 'Constipation, cramps', 'Store below 25°C'),
    ('Lactulose 10g/15ml', 'Lactulose', 'Gastrointestinal', 'syrup', '10g/15ml', 'Abbott', False, 'Galactosemia', 'Bloating, flatulence', 'Store below 25°C'),

    ('Salbutamol Inhaler', 'Salbutamol', 'Respiratory', 'inhaler', '100mcg/dose', 'GSK', True, 'None significant', 'Tremor, tachycardia', 'Store below 30°C'),
    ('Montelukast 10mg', 'Montelukast', 'Respiratory', 'tablet', '10mg', 'Merck', True, 'None significant', 'Headache, mood changes', 'Protect from moisture'),
    ('Budesonide Inhaler', 'Budesonide', 'Respiratory', 'inhaler', '200mcg/dose', 'AstraZeneca', True, 'Active TB', 'Oral thrush, hoarseness', 'Store below 30°C'),
    ('Ambroxol 30mg', 'Ambroxol', 'Respiratory', 'tablet', '30mg', 'Boehringer', False, 'First trimester pregnancy', 'GI upset, rash', 'Store below 25°C'),

    ('Cetirizine 10mg', 'Cetirizine', 'Antihistamines', 'tablet', '10mg', 'UCB Pharma', False, 'Severe renal impairment', 'Drowsiness, dry mouth', 'Store below 25°C'),
    ('Loratadine 10mg', 'Loratadine', 'Antihistamines', 'tablet', '10mg', 'Bayer', False, 'None significant', 'Headache, dry mouth', 'Store below 30°C'),
    ('Chlorpheniramine 4mg', 'Chlorpheniramine', 'Antihistamines', 'tablet', '4mg', 'GSK', False, 'Glaucoma', 'Drowsiness, dry mouth', 'Store below 25°C'),

    ('Carbamazepine 200mg', 'Carbamazepine', 'Neurological', 'tablet', '200mg', 'Novartis', True, 'AV block, bone marrow', 'Drowsiness, dizziness', 'Protect from moisture'),
    ('Levodopa/Carbidopa', 'Levodopa+Carbidopa', 'Neurological', 'tablet', '250/25mg', 'Roche', True, 'Glaucoma, MAO inhibitors', 'Dyskinesia, nausea', 'Protect from light'),
    ('Gabapentin 300mg', 'Gabapentin', 'Neurological', 'capsule', '300mg', 'Pfizer', True, 'None significant', 'Drowsiness, dizziness', 'Store below 25°C'),
    ('Sumatriptan 50mg', 'Sumatriptan', 'Neurological', 'tablet', '50mg', 'GSK', True, 'Ischemic heart disease', 'Tingling, flushing', 'Store below 30°C'),

    ('Sertraline 50mg', 'Sertraline', 'Psychiatric', 'tablet', '50mg', 'Pfizer', True, 'MAO inhibitors', 'Nausea, insomnia', 'Store below 30°C'),
    ('Escitalopram 10mg', 'Escitalopram', 'Psychiatric', 'tablet', '10mg', 'Lundbeck', True, 'MAO inhibitors, QT prolongation', 'Nausea, headache', 'Store below 25°C'),
    ('Alprazolam 0.5mg', 'Alprazolam', 'Psychiatric', 'tablet', '0.5mg', 'Pfizer', True, 'Respiratory depression', 'Drowsiness, dependence', 'Store below 30°C'),
    ('Olanzapine 5mg', 'Olanzapine', 'Psychiatric', 'tablet', '5mg', 'Eli Lilly', True, 'None significant', 'Weight gain, drowsiness', 'Protect from moisture'),

    ('Vitamin C 500mg', 'Ascorbic Acid', 'Vitamins & Supplements', 'tablet', '500mg', 'Nature Made', False, 'Kidney stones (high dose)', 'GI upset at high doses', 'Store in cool dry place'),
    ('Vitamin D3 1000IU', 'Cholecalciferol', 'Vitamins & Supplements', 'tablet', '1000IU', 'Nature Made', False, 'Hypercalcemia', 'Rare at normal doses', 'Protect from light'),
    ('Iron Supplement', 'Ferrous Sulfate', 'Vitamins & Supplements', 'tablet', '325mg', 'Nature Made', False, 'Hemochromatosis', 'Constipation, dark stools', 'Store below 30°C'),
    ('Calcium + Vit D', 'Calcium Carbonate+D3', 'Vitamins & Supplements', 'tablet', '600mg+400IU', 'Caltrate', False, 'Hypercalcemia', 'Constipation, gas', 'Store below 30°C'),
    ('Folic Acid 5mg', 'Folic Acid', 'Vitamins & Supplements', 'tablet', '5mg', 'Nature Made', False, 'B12 deficiency (masks)', 'None significant', 'Protect from light'),

    ('Betamethasone Cream', 'Betamethasone', 'Dermatological', 'cream', '0.1%', 'GSK', True, 'Skin infections', 'Skin thinning, stretch marks', 'Store below 25°C'),
    ('Clotrimazole Cream', 'Clotrimazole', 'Dermatological', 'cream', '1%', 'Bayer', False, 'None significant', 'Local irritation', 'Store below 30°C'),
    ('Permethrin Cream', 'Permethrin', 'Dermatological', 'cream', '5%', 'Perrigo', True, 'Chrysanthemum allergy', 'Burning, stinging', 'Store at room temp'),

    ('Epinephrine Injection', 'Epinephrine', 'Emergency Medicines', 'injection', '1mg/ml', 'Mylan', True, 'None in emergency', 'Tachycardia, anxiety', 'Protect from light'),
    ('Atropine Injection', 'Atropine Sulfate', 'Emergency Medicines', 'injection', '0.6mg/ml', 'Pfizer', True, 'None in emergency', 'Dry mouth, tachycardia', 'Store below 25°C'),
    ('Hydrocortisone 100mg', 'Hydrocortisone', 'Emergency Medicines', 'injection', '100mg', 'Pfizer', True, 'Systemic fungal infections', 'Hyperglycemia', 'Store below 25°C'),
    ('Dextrose 50%', 'Glucose', 'Emergency Medicines', 'injection', '50%', 'Baxter', True, 'None in emergency', 'Injection site reaction', 'Store at room temp'),

    ('Levothyroxine 50mcg', 'Levothyroxine', 'Hormonal', 'tablet', '50mcg', 'Abbott', True, 'Untreated adrenal insufficiency', 'Tachycardia, tremor', 'Protect from moisture'),
    ('Prednisolone 5mg', 'Prednisolone', 'Hormonal', 'tablet', '5mg', 'Pfizer', True, 'Systemic infections', 'Weight gain, mood changes', 'Store below 25°C'),

    ('Allopurinol 100mg', 'Allopurinol', 'Musculoskeletal', 'tablet', '100mg', 'Aspen', True, 'Acute gout attack', 'Rash, GI upset', 'Store below 25°C'),
    ('Colchicine 0.5mg', 'Colchicine', 'Musculoskeletal', 'tablet', '0.5mg', 'Takeda', True, 'Renal/hepatic impairment', 'Diarrhea, nausea', 'Protect from light'),
    ('Methotrexate 2.5mg', 'Methotrexate', 'Musculoskeletal', 'tablet', '2.5mg', 'Pfizer', True, 'Pregnancy, liver/renal disease', 'Nausea, mouth sores', 'Protect from light'),
]

SUPPLIERS = [
    'MedSupply International',
    'PharmaCare Distributors',
    'Global Health Supplies',
    'National Drug Store',
    'Premier Medical Wholesale',
]

DIAGNOSES_DATA = [
    # (description, icd_code, severity)
    ('Essential Hypertension', 'I10', 'moderate'),
    ('Type 2 Diabetes Mellitus', 'E11', 'moderate'),
    ('Acute Upper Respiratory Infection', 'J06.9', 'mild'),
    ('Acute Bronchitis', 'J20.9', 'mild'),
    ('Urinary Tract Infection', 'N39.0', 'mild'),
    ('Gastroesophageal Reflux Disease', 'K21.0', 'mild'),
    ('Major Depressive Disorder', 'F32.9', 'moderate'),
    ('Generalized Anxiety Disorder', 'F41.1', 'moderate'),
    ('Acute Gastroenteritis', 'K52.9', 'mild'),
    ('Migraine without Aura', 'G43.0', 'moderate'),
    ('Lumbar Disc Herniation', 'M51.1', 'moderate'),
    ('Iron Deficiency Anemia', 'D50.9', 'mild'),
    ('Allergic Rhinitis', 'J30.9', 'mild'),
    ('Atrial Fibrillation', 'I48', 'severe'),
    ('Community-Acquired Pneumonia', 'J18.9', 'severe'),
    ('Acute Myocardial Infarction', 'I21.9', 'critical'),
    ('Chronic Kidney Disease Stage 3', 'N18.3', 'moderate'),
    ('Hypothyroidism', 'E03.9', 'mild'),
    ('Osteoarthritis of Knee', 'M17.9', 'moderate'),
    ('Psoriasis Vulgaris', 'L40.0', 'mild'),
    ('Acute Appendicitis', 'K35.8', 'severe'),
    ('Cellulitis', 'L03.9', 'moderate'),
    ('Benign Prostatic Hyperplasia', 'N40', 'mild'),
    ('Peptic Ulcer Disease', 'K27.9', 'moderate'),
    ('Asthma Exacerbation', 'J45.9', 'moderate'),
]

LAB_TESTS_DATA = [
    # (test_name, test_type, normal_range_info)
    ('Complete Blood Count', 'Hematology', {'WBC': '4.5-11.0', 'RBC': '4.5-5.5', 'Hemoglobin': '12-17'}),
    ('Basic Metabolic Panel', 'Chemistry', {'Glucose': '70-100', 'Creatinine': '0.7-1.3', 'BUN': '7-20'}),
    ('Liver Function Test', 'Chemistry', {'ALT': '7-56', 'AST': '10-40', 'Bilirubin': '0.1-1.2'}),
    ('Lipid Panel', 'Chemistry', {'Total Cholesterol': '<200', 'LDL': '<100', 'HDL': '>40'}),
    ('Thyroid Panel', 'Endocrine', {'TSH': '0.4-4.0', 'T3': '80-200', 'T4': '4.5-12.5'}),
    ('Urinalysis', 'Urine', {'pH': '4.5-8.0', 'Specific Gravity': '1.005-1.030'}),
    ('HbA1c', 'Endocrine', {'HbA1c': '<5.7% normal, 5.7-6.4% prediabetes'}),
    ('Serum Creatinine', 'Chemistry', {'Creatinine': '0.7-1.3 mg/dL'}),
    ('Chest X-Ray', 'Radiology', {}),
    ('ECG', 'Cardiology', {}),
    ('Blood Culture', 'Microbiology', {}),
    ('Urine Culture', 'Microbiology', {}),
    ('PT/INR', 'Hematology', {'INR': '0.8-1.2 (2-3 on warfarin)'}),
    ('Serum Electrolytes', 'Chemistry', {'Na': '136-145', 'K': '3.5-5.0', 'Cl': '98-106'}),
    ('C-Reactive Protein', 'Immunology', {'CRP': '<10 mg/L'}),
]

APPOINTMENT_REASONS = [
    'Routine checkup',
    'Follow-up visit',
    'Chest pain evaluation',
    'Persistent headache',
    'Knee pain',
    'Skin rash evaluation',
    'Blood pressure monitoring',
    'Diabetes management',
    'Cough and cold symptoms',
    'Abdominal pain',
    'Back pain',
    'Difficulty breathing',
    'Annual physical examination',
    'Medication review',
    'Post-surgical follow-up',
    'Joint stiffness',
    'Dizziness and vertigo',
    'Urinary symptoms',
    'Anxiety and sleep issues',
    'Weight management consultation',
]


class Command(BaseCommand):
    help = 'Seed comprehensive test data for every module in the HMS'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true',
                            help='Clear existing data before seeding')

    def handle(self, *args, **options):
        if options['clear']:
            self.clear_data()

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Hospital Management System - Comprehensive Test Data ===\n'))  # noqa

        departments = self.create_departments()
        admin_users = self.create_admin_users()
        receptionists = self.create_receptionists()
        pharmacists = self.create_pharmacists()
        doctors = self.create_doctors(departments)
        patients = self.create_patients()
        self.create_doctor_schedules(doctors)
        categories, medicines = self.create_medicines()
        stocks = self.create_stock(medicines, pharmacists)
        appointments = self.create_appointments(patients, doctors, departments, receptionists)
        records = self.create_medical_records(appointments, doctors, patients)
        prescriptions = self.create_prescriptions(records, medicines, pharmacists)
        self.create_lab_tests(records, doctors, patients)
        self.create_stock_transactions(stocks, prescriptions, pharmacists)
        self.create_notifications(patients, doctors, pharmacists, appointments)
        self.create_audit_logs(admin_users, doctors, receptionists, pharmacists)
        self.create_appointment_slots(doctors)

        # ML Training Data + Progressive Model Training
        self.create_ml_training_data(doctors, patients)
        self.train_ml_models_progressive(doctors)
        self.create_prediction_logs(doctors, patients)

        self.stdout.write(self.style.SUCCESS('\n=== All test data created successfully! ===\n'))
        self.print_summary()

    def clear_data(self):
        self.stdout.write('Clearing existing data...')
        # Clear in reverse dependency order
        AuditLog.objects.all().delete()
        Notification.objects.all().delete()
        PredictionLog.objects.all().delete()
        StockTransaction.objects.all().delete()
        PrescriptionItem.objects.all().delete()
        Prescription.objects.all().delete()
        LabTest.objects.all().delete()
        Diagnosis.objects.all().delete()
        MedicalRecord.objects.all().delete()
        AppointmentSlot.objects.all().delete()
        Appointment.objects.all().delete()
        MedicineStock.objects.all().delete()
        Medicine.objects.all().delete()
        MedicineCategory.objects.all().delete()
        DoctorSchedule.objects.all().delete()
        DoctorProfile.objects.all().delete()
        PatientDocument.objects.all().delete()
        Patient.objects.all().delete()
        # Clear ML data too
        TrainingData.objects.all().delete()
        MLModelVersion.objects.all().delete()
        # Clean up saved model files
        import glob as glob_mod
        model_dir = os.path.join(settings.BASE_DIR, 'ml_models')
        if os.path.exists(model_dir):
            for f in glob_mod.glob(os.path.join(model_dir, '*.joblib')):
                os.remove(f)
        # Don't delete superuser
        User.objects.filter(is_superuser=False).delete()
        Department.objects.all().delete()
        self.stdout.write(self.style.WARNING('  Cleared ALL data (except superuser)'))

    # ─── Departments ────────────────────────────────────────────
    def create_departments(self):
        self.stdout.write('Creating departments...')
        depts = {}
        for name, desc in DEPARTMENTS:
            dept, _ = Department.objects.get_or_create(
                name=name, defaults={'description': desc}
            )
            depts[name] = dept
        self.stdout.write(self.style.SUCCESS(f'  {len(depts)} departments'))
        return depts

    # ─── Admin Users ────────────────────────────────────────────
    def create_admin_users(self):
        self.stdout.write('Creating admin users...')
        admins = []
        admin_data = [
            ('admin@hospital.com', 'System', 'Administrator', 'male'),
            ('admin2@hospital.com', 'Deputy', 'Admin', 'female'),
        ]
        for email, first, last, gender in admin_data:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first, 'last_name': last,
                    'role': 'admin', 'gender': gender,
                    'phone': '555-0001', 'is_active': True, 'is_staff': True,
                }
            )
            if created:
                user.set_password('Test@123')
                user.save()
            admins.append(user)
        self.stdout.write(self.style.SUCCESS(f'  {len(admins)} admin users'))
        return admins

    # ─── Receptionists ──────────────────────────────────────────
    def create_receptionists(self):
        self.stdout.write('Creating receptionists...')
        receps = []
        data = [
            ('reception1@hospital.com', 'Mona', 'Al-Said', 'female'),
            ('reception2@hospital.com', 'Khaled', 'Yousef', 'male'),
            ('reception3@hospital.com', 'Reem', 'Abdulla', 'female'),
        ]
        for email, first, last, gender in data:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first, 'last_name': last,
                    'role': 'receptionist', 'gender': gender,
                    'phone': '555-0010', 'is_active': True,
                }
            )
            if created:
                user.set_password('Test@123')
                user.save()
            receps.append(user)
        self.stdout.write(self.style.SUCCESS(f'  {len(receps)} receptionists'))
        return receps

    # ─── Pharmacists ────────────────────────────────────────────
    def create_pharmacists(self):
        self.stdout.write('Creating pharmacists...')
        pharmas = []
        data = [
            ('pharma1@hospital.com', 'Zain', 'Hamdan', 'male'),
            ('pharma2@hospital.com', 'Lina', 'Darwish', 'female'),
            ('pharma3@hospital.com', 'Faisal', 'Jaber', 'male'),
        ]
        for email, first, last, gender in data:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first, 'last_name': last,
                    'role': 'pharmacist', 'gender': gender,
                    'phone': '555-0020', 'is_active': True,
                }
            )
            if created:
                user.set_password('Test@123')
                user.save()
            pharmas.append(user)
        self.stdout.write(self.style.SUCCESS(f'  {len(pharmas)} pharmacists'))
        return pharmas

    # ─── Doctors ────────────────────────────────────────────────
    def create_doctors(self, departments):
        self.stdout.write('Creating doctors with profiles...')
        docs = []
        for email, first, last, dept_name, spec, qual, lic, exp, fee in DOCTORS_DATA:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first, 'last_name': last,
                    'role': 'doctor', 'gender': random.choice(['male', 'female']),
                    'phone': f'555-{random.randint(2000, 2999)}',
                    'is_active': True,
                }
            )
            if created:
                user.set_password('Test@123')
                user.save()

            dept = departments.get(dept_name)
            if dept and not DoctorProfile.objects.filter(user=user).exists():
                DoctorProfile.objects.create(
                    user=user, department=dept, specialization=spec,
                    qualification=qual, license_number=lic,
                    experience_years=exp,
                    consultation_fee=Decimal(str(fee)),
                    bio=f'Dr. {first} {last} is a specialist in {spec} with {exp} years of experience.',
                    average_consultation_time=random.choice([10, 15, 20, 25, 30]),
                    max_patients_per_day=random.randint(15, 35),
                )
            docs.append(user)

        # Assign head doctors to some departments
        for dept_name, dept in departments.items():
            matching = [d for d in docs if hasattr(d, 'doctor_profile') and
                        d.doctor_profile.department == dept]
            if not matching:
                # Reload to get profiles
                for d in docs:
                    try:
                        d.refresh_from_db()
                        prof = DoctorProfile.objects.filter(user=d).first()
                        if prof and prof.department == dept:
                            matching.append(d)
                    except Exception:
                        pass
            if matching:
                dept.head_doctor = matching[0]
                dept.save()

        self.stdout.write(self.style.SUCCESS(f'  {len(docs)} doctors with profiles'))
        return docs

    # ─── Patients ───────────────────────────────────────────────
    def create_patients(self):
        self.stdout.write('Creating patients...')
        pats = []
        for (email, first, last, gender, dob, phone, blood_group,
             allergies, chronic, national_id) in PATIENTS_DATA:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first, 'last_name': last,
                    'role': 'patient', 'gender': gender,
                    'date_of_birth': date.fromisoformat(dob),
                    'phone': phone, 'is_active': True,
                    'address': f'{random.randint(1, 999)} {random.choice(["Main St", "Oak Ave", "Park Blvd", "Hospital Rd", "Cedar Lane"])}',
                }
            )
            if created:
                user.set_password('Test@123')
                user.save()

            if not Patient.objects.filter(user=user).exists():
                risk_score = random.randint(0, 100)
                if risk_score < 30:
                    risk_level = 'low'
                elif risk_score < 60:
                    risk_level = 'medium'
                elif risk_score < 85:
                    risk_level = 'high'
                else:
                    risk_level = 'critical'

                Patient.objects.create(
                    user=user,
                    national_id=national_id,
                    blood_group=blood_group,
                    allergies=allergies,
                    chronic_conditions=chronic,
                    emergency_contact_name=f'{random.choice(["Ahmad", "Sara", "Mohammed", "Fatima"])} {last}',
                    emergency_contact_phone=f'555-{random.randint(3000, 3999)}',
                    emergency_contact_relation=random.choice(['Spouse', 'Parent', 'Sibling', 'Child']),
                    insurance_provider=random.choice(['', 'National Health Insurance', 'MedCare Plus', 'HealthShield', 'Royal Insurance']),
                    insurance_id=f'INS{random.randint(100000, 999999)}' if random.random() > 0.3 else '',
                    risk_score=risk_score,
                    risk_level=risk_level,
                    notes=chronic if chronic else '',
                )
            pats.append(user)
        self.stdout.write(self.style.SUCCESS(f'  {len(pats)} patients with profiles'))
        return pats

    # ─── Doctor Schedules ───────────────────────────────────────
    def create_doctor_schedules(self, doctors):
        self.stdout.write('Creating doctor schedules...')
        count = 0
        for doc in doctors:
            # Each doctor works 5-6 days
            work_days = random.sample(range(0, 7), random.randint(5, 6))
            for day in work_days:
                start_hour = random.choice([8, 9])
                end_hour = random.choice([16, 17, 18])
                DoctorSchedule.objects.get_or_create(
                    doctor=doc, day_of_week=day,
                    defaults={
                        'start_time': time(start_hour, 0),
                        'end_time': time(end_hour, 0),
                        'max_patients': random.randint(15, 25),
                        'is_available': True,
                    }
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f'  {count} schedule entries'))

    # ─── Medicines ──────────────────────────────────────────────
    def create_medicines(self):
        self.stdout.write('Creating medicine categories and medicines...')
        cats = {}
        for name, desc in MEDICINE_CATEGORIES:
            cat, _ = MedicineCategory.objects.get_or_create(
                name=name, defaults={'description': desc}
            )
            cats[name] = cat

        meds = []
        for (name, generic, cat_name, form, strength, manufacturer,
             requires_rx, contras, side_fx, storage) in MEDICINES_DATA:
            cat = cats.get(cat_name)
            med, _ = Medicine.objects.get_or_create(
                name=name,
                defaults={
                    'generic_name': generic,
                    'category': cat,
                    'dosage_form': form,
                    'strength': strength,
                    'manufacturer': manufacturer,
                    'requires_prescription': requires_rx,
                    'contraindications': contras,
                    'side_effects': side_fx,
                    'storage_instructions': storage,
                    'is_active': True,
                }
            )
            meds.append(med)
        self.stdout.write(self.style.SUCCESS(f'  {len(cats)} categories, {len(meds)} medicines'))
        return cats, meds

    # ─── Stock Entries ──────────────────────────────────────────
    def create_stock(self, medicines, pharmacists):
        self.stdout.write('Creating medicine stock entries...')
        stocks = []
        today = date.today()

        for med in medicines:
            # 1-3 batches per medicine
            num_batches = random.randint(1, 3)
            for b in range(num_batches):
                days_ago = random.randint(10, 180)
                expiry_days = random.randint(90, 730)
                qty = random.randint(20, 500)

                # Some items with low stock for testing alerts
                if random.random() < 0.15:
                    qty = random.randint(2, 8)

                # One expired batch for testing
                if random.random() < 0.05:
                    expiry_days = -random.randint(1, 60)

                stock = MedicineStock.objects.create(
                    medicine=med,
                    batch_number=f'BTH-{med.pk:03d}-{b+1:02d}-{random.randint(1000, 9999)}',
                    quantity=qty,
                    unit_price=Decimal(str(round(random.uniform(0.5, 50.0), 2))),
                    expiry_date=today + timedelta(days=expiry_days),
                    received_date=today - timedelta(days=days_ago),
                    supplier=random.choice(SUPPLIERS),
                    reorder_level=random.choice([10, 15, 20, 25]),
                    notes='' if random.random() > 0.2 else 'Checked on receipt',
                )
                stocks.append(stock)
        self.stdout.write(self.style.SUCCESS(f'  {len(stocks)} stock entries'))
        return stocks

    # ─── Appointments ───────────────────────────────────────────
    def create_appointments(self, patients, doctors, departments, receptionists):
        self.stdout.write('Creating appointments...')
        appointments = []
        today = date.today()
        statuses_past = ['completed', 'cancelled', 'no_show']
        statuses_future = ['scheduled', 'confirmed']
        appt_types = ['regular', 'followup', 'emergency', 'walkin']

        # Past appointments (60 days back)
        for i in range(80):
            patient = random.choice(patients)
            doctor = random.choice(doctors)
            dept_name = None
            try:
                prof = DoctorProfile.objects.get(user=doctor)
                dept_name = prof.department.name
            except DoctorProfile.DoesNotExist:
                pass

            days_ago = random.randint(1, 60)
            appt_date = today - timedelta(days=days_ago)
            appt_time = time(random.randint(8, 16), random.choice([0, 15, 30, 45]))

            status = random.choices(statuses_past, weights=[70, 15, 15])[0]
            appt_type = random.choices(appt_types, weights=[50, 25, 15, 10])[0]

            dept = departments.get(dept_name) if dept_name else random.choice(list(departments.values()))

            appt = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                department=dept,
                scheduled_date=appt_date,
                scheduled_time=appt_time,
                appointment_type=appt_type,
                status=status,
                reason=random.choice(APPOINTMENT_REASONS),
                notes='Patient seen and treated.' if status == 'completed' else '',
                queue_number=random.randint(1, 30) if status == 'completed' else None,
                check_in_time=timezone.make_aware(
                    datetime.combine(appt_date, appt_time)
                ) if status == 'completed' else None,
                start_time=timezone.make_aware(
                    datetime.combine(appt_date, appt_time) + timedelta(minutes=random.randint(5, 30))
                ) if status == 'completed' else None,
                end_time=timezone.make_aware(
                    datetime.combine(appt_date, appt_time) + timedelta(minutes=random.randint(20, 60))
                ) if status == 'completed' else None,
                estimated_wait=random.randint(5, 45) if status == 'completed' else None,
                ai_priority=random.random() < 0.1,
                ai_priority_reason='High risk patient' if random.random() < 0.1 else '',
                created_by=random.choice(receptionists),
            )
            appointments.append(appt)

        # Today's appointments
        for i in range(15):
            patient = random.choice(patients)
            doctor = random.choice(doctors)
            dept = random.choice(list(departments.values()))
            appt_time = time(random.randint(8, 16), random.choice([0, 15, 30, 45]))
            status = random.choice(['scheduled', 'confirmed', 'checked_in', 'in_progress', 'completed'])

            appt = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                department=dept,
                scheduled_date=today,
                scheduled_time=appt_time,
                appointment_type=random.choice(appt_types),
                status=status,
                reason=random.choice(APPOINTMENT_REASONS),
                queue_number=i + 1,
                check_in_time=timezone.now() - timedelta(minutes=random.randint(10, 120)) if status in ['checked_in', 'in_progress', 'completed'] else None,
                start_time=timezone.now() - timedelta(minutes=random.randint(5, 60)) if status in ['in_progress', 'completed'] else None,
                end_time=timezone.now() - timedelta(minutes=random.randint(1, 10)) if status == 'completed' else None,
                estimated_wait=random.randint(5, 30),
                created_by=random.choice(receptionists),
            )
            appointments.append(appt)

        # Future appointments (next 30 days)
        for i in range(30):
            patient = random.choice(patients)
            doctor = random.choice(doctors)
            dept = random.choice(list(departments.values()))
            days_ahead = random.randint(1, 30)
            appt_date = today + timedelta(days=days_ahead)
            appt_time = time(random.randint(8, 16), random.choice([0, 15, 30, 45]))

            appt = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                department=dept,
                scheduled_date=appt_date,
                scheduled_time=appt_time,
                appointment_type=random.choice(['regular', 'followup']),
                status=random.choice(statuses_future),
                reason=random.choice(APPOINTMENT_REASONS),
                created_by=random.choice(receptionists),
            )
            appointments.append(appt)

        self.stdout.write(self.style.SUCCESS(f'  {len(appointments)} appointments (80 past + 15 today + 30 future)'))
        return appointments

    # ─── Medical Records ────────────────────────────────────────
    def create_medical_records(self, appointments, doctors, patients):
        self.stdout.write('Creating medical records with diagnoses...')
        records = []
        completed_appts = [a for a in appointments if a.status == 'completed']

        vital_templates = [
            {'blood_pressure': '120/80', 'pulse': 72, 'temperature': 36.6, 'spo2': 98, 'weight': 70, 'height': 170},
            {'blood_pressure': '140/90', 'pulse': 88, 'temperature': 37.2, 'spo2': 96, 'weight': 85, 'height': 175},
            {'blood_pressure': '160/100', 'pulse': 95, 'temperature': 38.5, 'spo2': 94, 'weight': 92, 'height': 168},
            {'blood_pressure': '110/70', 'pulse': 65, 'temperature': 36.5, 'spo2': 99, 'weight': 55, 'height': 162},
            {'blood_pressure': '130/85', 'pulse': 78, 'temperature': 36.8, 'spo2': 97, 'weight': 78, 'height': 180},
            {'blood_pressure': '150/95', 'pulse': 102, 'temperature': 39.1, 'spo2': 92, 'weight': 68, 'height': 165},
        ]

        complaints = [
            ('Chest pain radiating to left arm for 2 hours', 'Patient reports substernal chest pain since morning, 7/10 severity'),
            ('Persistent cough for 2 weeks with yellow sputum', 'Non-productive cough progressed to productive over past week'),
            ('Severe headache with visual disturbances', 'Patient reports worst headache of life, sudden onset'),
            ('Knee pain and swelling after fall', 'Right knee swollen and tender, limited ROM'),
            ('Abdominal pain with nausea and vomiting', 'Epigastric pain radiating to back, 6/10 severity'),
            ('Difficulty breathing on exertion', 'Progressive dyspnea over 3 weeks, now at rest'),
            ('Burning sensation during urination', 'Dysuria with frequency and urgency for 3 days'),
            ('Skin rash spreading across torso', 'Erythematous papular rash noted 5 days ago, spreading'),
            ('Persistent fatigue and weight loss', 'Unintentional weight loss of 5kg over 2 months'),
            ('Joint stiffness worse in mornings', 'Morning stiffness lasting >1 hour, bilateral hands'),
            ('Dizziness and occasional fainting', 'Orthostatic symptoms when standing up quickly'),
            ('Fever with sore throat for 3 days', 'Fever up to 39°C with odynophagia'),
            ('Back pain radiating down the leg', 'Lower back pain with left leg radiculopathy'),
            ('Anxiety and panic attacks', 'Patient reports 3 panic attacks this week, affecting work'),
            ('Routine diabetes follow-up', 'Quarterly HbA1c check and medication review'),
        ]

        for appt in completed_appts:
            complaint_data = random.choice(complaints)
            vitals = random.choice(vital_templates).copy()
            # Add some variation
            vitals['pulse'] = vitals['pulse'] + random.randint(-5, 5)
            vitals['temperature'] = round(vitals['temperature'] + random.uniform(-0.3, 0.5), 1)

            record = MedicalRecord.objects.create(
                patient=appt.patient,
                doctor=appt.doctor,
                appointment=appt,
                visit_date=appt.scheduled_date,
                chief_complaint=complaint_data[0],
                history_of_present_illness=complaint_data[1],
                vital_signs=vitals,
                physical_examination=random.choice([
                    'General: Alert, oriented. Heart: RRR, no murmurs. Lungs: CTA bilaterally.',
                    'General: Appears unwell. Heart: Irregular rhythm. Lungs: Crackles at bases.',
                    'General: Well-nourished, no distress. Abdomen: Soft, non-tender.',
                    'General: Febrile. Throat: Erythematous with exudates. Neck: Tender lymphadenopathy.',
                    'MSK: Right knee swollen, warm. ROM limited. Neurovascular intact distally.',
                ]),
                assessment=random.choice([
                    'Assessment consistent with acute presentation. Requires further workup.',
                    'Stable chronic condition. Medication adjustment recommended.',
                    'New diagnosis. Initiated treatment plan with follow-up in 2 weeks.',
                    'Improving from previous visit. Continue current management.',
                    'Complex case requiring multidisciplinary approach.',
                ]),
                plan=random.choice([
                    'Start medications as prescribed. Follow-up in 1 week. Labs ordered.',
                    'Continue current medications. Lifestyle modifications discussed. Return in 1 month.',
                    'Refer to specialist. Imaging ordered. Symptomatic treatment initiated.',
                    'Admit for observation. IV medications started. Monitor vitals q4h.',
                    'Discharge with prescriptions. Return if symptoms worsen. Follow-up in 2 weeks.',
                ]),
                notes='',
                follow_up_date=appt.scheduled_date + timedelta(days=random.choice([7, 14, 30, 60])),
            )
            records.append(record)

            # Add 1-2 diagnoses per record
            num_dx = random.randint(1, 2)
            selected_dx = random.sample(DIAGNOSES_DATA, min(num_dx, len(DIAGNOSES_DATA)))
            for idx, (desc, icd, severity) in enumerate(selected_dx):
                Diagnosis.objects.create(
                    medical_record=record,
                    icd_code=icd,
                    description=desc,
                    severity=severity,
                    is_primary=(idx == 0),
                    notes='' if random.random() > 0.3 else 'Confirmed by lab results',
                )

        self.stdout.write(self.style.SUCCESS(f'  {len(records)} medical records with diagnoses'))
        return records

    # ─── Prescriptions ──────────────────────────────────────────
    def create_prescriptions(self, records, medicines, pharmacists):
        self.stdout.write('Creating prescriptions...')
        prescriptions = []
        frequencies = ['Once daily', 'Twice daily', 'Three times daily', 'Every 8 hours',
                       'Every 12 hours', 'At bedtime', 'As needed', 'Before meals']
        durations = ['3 days', '5 days', '7 days', '10 days', '14 days', '30 days',
                     '3 months', '6 months', 'Ongoing']
        instructions = ['Take with food', 'Take on empty stomach', 'Avoid alcohol',
                        'Take with plenty of water', 'Do not crush or chew',
                        'Apply thin layer to affected area', '']

        # Create prescriptions for ~70% of records
        for record in records:
            if random.random() < 0.3:
                continue

            status_weights = [40, 35, 15, 10]
            status = random.choices(['dispensed', 'pending', 'partial', 'cancelled'],
                                    weights=status_weights)[0]

            dispensed_pharmacist = random.choice(pharmacists) if status == 'dispensed' else None
            dispensed_time = (timezone.make_aware(
                datetime.combine(record.visit_date, time(random.randint(10, 17), random.randint(0, 59)))
            )) if status == 'dispensed' else None

            prescription = Prescription.objects.create(
                patient=record.patient,
                doctor=record.doctor,
                medical_record=record,
                status=status,
                notes=random.choice(['', 'Urgent', 'Patient counseled on side effects',
                                     'Check allergies before dispensing']),
                dispensed_by=dispensed_pharmacist,
                dispensed_at=dispensed_time,
            )

            # Add 1-4 prescription items
            num_items = random.randint(1, 4)
            selected_meds = random.sample(medicines, min(num_items, len(medicines)))
            for med in selected_meds:
                PrescriptionItem.objects.create(
                    prescription=prescription,
                    medicine=med,
                    dosage=med.strength,
                    frequency=random.choice(frequencies),
                    duration=random.choice(durations),
                    quantity=random.randint(7, 90),
                    instructions=random.choice(instructions),
                    is_dispensed=(status == 'dispensed'),
                )
            prescriptions.append(prescription)

        self.stdout.write(self.style.SUCCESS(f'  {len(prescriptions)} prescriptions with items'))
        return prescriptions

    # ─── Lab Tests ──────────────────────────────────────────────
    def create_lab_tests(self, records, doctors, patients):
        self.stdout.write('Creating lab tests...')
        count = 0
        lab_statuses = ['ordered', 'collected', 'processing', 'completed', 'cancelled']

        for record in records:
            if random.random() < 0.5:
                continue

            num_tests = random.randint(1, 3)
            selected_tests = random.sample(LAB_TESTS_DATA, min(num_tests, len(LAB_TESTS_DATA)))

            for test_name, test_type, normal_ranges in selected_tests:
                status = random.choices(lab_statuses, weights=[10, 10, 15, 60, 5])[0]
                is_abnormal = random.random() < 0.25

                results = {}
                if status == 'completed' and normal_ranges:
                    for key, range_str in normal_ranges.items():
                        # Generate some realistic values
                        results[key] = f'{random.uniform(0.5, 200):.1f}'
                    results = json.dumps(results)
                else:
                    results = None

                LabTest.objects.create(
                    patient=record.patient,
                    doctor=record.doctor,
                    medical_record=record,
                    test_name=test_name,
                    test_type=test_type,
                    status=status,
                    results=json.loads(results) if results else {},
                    result_summary=f'{"ABNORMAL: " if is_abnormal else ""}Results reviewed' if status == 'completed' else '',
                    is_abnormal=is_abnormal if status == 'completed' else False,
                    notes='' if random.random() > 0.2 else 'Rush order',
                    completed_at=timezone.now() - timedelta(days=random.randint(0, 30)) if status == 'completed' else None,
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f'  {count} lab tests'))

    # ─── Stock Transactions ─────────────────────────────────────
    def create_stock_transactions(self, stocks, prescriptions, pharmacists):
        self.stdout.write('Creating stock transactions...')
        count = 0

        # Stock-in transactions for each stock entry
        for stock in stocks:
            StockTransaction.objects.create(
                stock=stock,
                transaction_type='in',
                quantity=stock.quantity + random.randint(10, 50),
                reference=f'PO-{random.randint(10000, 99999)}',
                notes=f'Initial stock from {stock.supplier}',
                performed_by=random.choice(pharmacists),
            )
            count += 1

        # Stock-out for dispensed prescriptions
        dispensed = [p for p in prescriptions if p.status == 'dispensed']
        for presc in dispensed[:30]:
            items = presc.items.all()
            for item in items:
                matching_stocks = [s for s in stocks if s.medicine == item.medicine]
                if matching_stocks:
                    stock = matching_stocks[0]
                    StockTransaction.objects.create(
                        stock=stock,
                        transaction_type='out',
                        quantity=item.quantity,
                        reference=f'RX-{presc.pk}',
                        notes=f'Dispensed for prescription #{presc.pk}',
                        performed_by=presc.dispensed_by,
                    )
                    count += 1

        # Some adjustment transactions
        for _ in range(10):
            stock = random.choice(stocks)
            StockTransaction.objects.create(
                stock=stock,
                transaction_type='adjustment',
                quantity=random.randint(-5, 10),
                reference=f'ADJ-{random.randint(1000, 9999)}',
                notes=random.choice(['Physical count correction', 'Damaged stock removed',
                                     'Returned to supplier', 'Inventory audit']),
                performed_by=random.choice(pharmacists),
            )
            count += 1

        # Some expired transactions
        expired_stocks = [s for s in stocks if s.expiry_date < date.today()]
        for stock in expired_stocks:
            StockTransaction.objects.create(
                stock=stock,
                transaction_type='expired',
                quantity=stock.quantity,
                reference=f'EXP-{random.randint(1000, 9999)}',
                notes='Batch expired - removed from inventory',
                performed_by=random.choice(pharmacists),
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'  {count} stock transactions'))

    # ─── Notifications ──────────────────────────────────────────
    def create_notifications(self, patients, doctors, pharmacists, appointments):
        self.stdout.write('Creating notifications...')
        count = 0
        now = timezone.now()

        # Appointment reminders for patients
        for appt in appointments[:20]:
            Notification.objects.create(
                user=appt.patient,
                notification_type='appointment',
                title='Appointment Reminder',
                message=f'You have an appointment on {appt.scheduled_date} at {appt.scheduled_time}',
                link=f'/appointments/{appt.pk}/',
                is_read=random.random() < 0.5,
            )
            count += 1

        # Prescription notifications
        for patient in patients[:15]:
            Notification.objects.create(
                user=patient,
                notification_type='prescription',
                title='Prescription Ready',
                message='Your prescription is ready for pickup at the pharmacy.',
                is_read=random.random() < 0.4,
            )
            count += 1

        # Lab result notifications
        for patient in patients[:10]:
            Notification.objects.create(
                user=patient,
                notification_type='lab_result',
                title='Lab Results Available',
                message='Your lab test results are now available. Please check your records.',
                is_read=random.random() < 0.3,
            )
            count += 1

        # Doctor notifications
        for doctor in doctors:
            Notification.objects.create(
                user=doctor,
                notification_type='appointment',
                title='New Appointment',
                message='A new appointment has been scheduled for today.',
                is_read=random.random() < 0.6,
            )
            count += 1

            Notification.objects.create(
                user=doctor,
                notification_type='alert',
                title='High Risk Patient Alert',
                message='Patient with critical risk score has an upcoming appointment.',
                is_read=random.random() < 0.3,
            )
            count += 1

        # Pharmacist stock alerts
        for pharmacist in pharmacists:
            Notification.objects.create(
                user=pharmacist,
                notification_type='alert',
                title='Low Stock Alert',
                message='Multiple medicines are running low on stock. Please review inventory.',
                is_read=random.random() < 0.4,
            )
            count += 1

            Notification.objects.create(
                user=pharmacist,
                notification_type='prescription',
                title='New Prescription to Dispense',
                message='A new prescription has been submitted and awaiting dispensing.',
                is_read=random.random() < 0.5,
            )
            count += 1

        # System notifications for admins
        Notification.objects.create(
            user=User.objects.filter(role='admin').first(),
            notification_type='system',
            title='System Update',
            message='The hospital management system has been updated to the latest version.',
            is_read=False,
        )
        count += 1

        # Reminder notifications
        for patient in patients[:8]:
            Notification.objects.create(
                user=patient,
                notification_type='reminder',
                title='Follow-up Reminder',
                message='Please remember to schedule your follow-up appointment.',
                is_read=False,
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'  {count} notifications'))

    # ─── Prediction Logs ────────────────────────────────────────
    def create_prediction_logs(self, doctors, patients):
        self.stdout.write('Creating prediction logs...')
        active_model = MLModelVersion.objects.filter(is_active=True).first()

        symptoms_sets = [
            ('fever,cough,shortness_of_breath', 'Pneumonia', 0.82, 'Bronchitis', 0.65, 'COVID-19', 0.41),
            ('chest_pain,palpitations,shortness_of_breath', 'Coronary Artery Disease', 0.75, 'Angina', 0.68, 'Panic Disorder', 0.22),
            ('headache,nausea,blurred_vision', 'Migraine', 0.88, 'Hypertension Crisis', 0.45, 'Brain Tumor', 0.12),
            ('abdominal_pain,nausea,vomiting', 'Gastritis', 0.71, 'Appendicitis', 0.58, 'Peptic Ulcer', 0.42),
            ('joint_pain,swelling,fatigue', 'Rheumatoid Arthritis', 0.79, 'Gout', 0.55, 'Lupus', 0.31),
            ('fever,sore_throat,fatigue', 'Strep Throat', 0.84, 'Mononucleosis', 0.52, 'Influenza', 0.48),
            ('skin_rash,itching,fever', 'Contact Dermatitis', 0.73, 'Psoriasis', 0.60, 'Drug Reaction', 0.35),
            ('frequent_urination,burning,fever', 'Urinary Tract Infection', 0.91, 'Pyelonephritis', 0.55, 'Cystitis', 0.48),
            ('fatigue,weight_loss,excessive_thirst', 'Diabetes Mellitus', 0.87, 'Hyperthyroidism', 0.42, 'Addison Disease', 0.15),
            ('back_pain,numbness,weakness', 'Disc Herniation', 0.76, 'Spinal Stenosis', 0.61, 'Sciatica', 0.58),
            ('dizziness,ear_pain,nausea', 'Vertigo', 0.80, 'Meniere Disease', 0.55, 'Labyrinthitis', 0.43),
            ('anxiety,insomnia,palpitations', 'Generalized Anxiety', 0.85, 'Panic Disorder', 0.62, 'Hyperthyroidism', 0.28),
        ]

        count = 0
        for symptoms, p1, c1, p2, c2, p3, c3 in symptoms_sets:
            patient = random.choice(patients)
            doctor = random.choice(doctors)
            PredictionLog.objects.create(
                patient=patient,
                symptoms_input=symptoms,
                patient_age=random.randint(20, 75),
                patient_gender=random.choice(['male', 'female']),
                prediction_1=p1,
                confidence_1=c1,
                prediction_2=p2,
                confidence_2=c2,
                prediction_3=p3,
                confidence_3=c3,
                model_version=active_model,
                feedback_received=random.random() < 0.6,
                predicted_by=doctor,
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'  {count} prediction logs'))

    # ─── Audit Logs ─────────────────────────────────────────────
    def create_audit_logs(self, admins, doctors, receptionists, pharmacists):
        self.stdout.write('Creating audit logs...')
        all_users = admins + doctors + receptionists + pharmacists
        actions = ['create', 'update', 'delete', 'login', 'logout', 'view', 'export']
        models = ['Appointment', 'Patient', 'MedicalRecord', 'Prescription',
                   'Medicine', 'MedicineStock', 'User', 'Department']

        count = 0
        for _ in range(100):
            user = random.choice(all_users)
            action = random.choices(actions, weights=[20, 25, 5, 20, 15, 10, 5])[0]
            model = random.choice(models)

            AuditLog.objects.create(
                user=user,
                action=action,
                model_name=model if action in ['create', 'update', 'delete', 'view'] else '',
                object_id=str(random.randint(1, 200)) if action in ['create', 'update', 'delete', 'view'] else '',
                object_repr=f'{model} #{random.randint(1, 200)}' if action in ['create', 'update', 'delete'] else '',
                changes={'field': 'status', 'old': 'pending', 'new': 'completed'} if action == 'update' else {},
                ip_address=f'192.168.1.{random.randint(1, 254)}',
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'  {count} audit log entries'))

    # ─── Appointment Slots ──────────────────────────────────────
    def create_appointment_slots(self, doctors):
        self.stdout.write('Creating appointment slots...')
        count = 0
        today = date.today()

        for doctor in doctors:
            # Create slots for next 14 days
            for day_offset in range(14):
                slot_date = today + timedelta(days=day_offset)
                weekday = slot_date.weekday()

                # Skip if doctor doesn't work this day
                schedule = DoctorSchedule.objects.filter(
                    doctor=doctor, day_of_week=weekday, is_available=True
                ).first()
                if not schedule:
                    continue

                # Create hourly slots
                current_hour = schedule.start_time.hour
                while current_hour < schedule.end_time.hour:
                    booked = random.randint(0, 1) if day_offset < 3 else 0
                    AppointmentSlot.objects.get_or_create(
                        doctor=doctor,
                        date=slot_date,
                        start_time=time(current_hour, 0),
                        defaults={
                            'end_time': time(current_hour + 1, 0),
                            'is_available': booked == 0,
                            'max_patients': 3,
                            'booked_count': booked,
                        }
                    )
                    count += 1
                    current_hour += 1

        self.stdout.write(self.style.SUCCESS(f'  {count} appointment slots'))

    # ─── ML Training Data + Progressive Training ──────────────
    def create_ml_training_data(self, doctors, patients):
        """
        Create ML training data in progressive batches and train after each batch
        to generate a realistic learning curve with improving accuracy.
        """
        self.stdout.write('Creating ML training data + training models progressively...')

        from apps.ai_services.management.commands.seed_training_data import (
            DISEASE_PROFILES, generate_record,
        )
        from apps.ai_services.ml_pipeline import ALL_SYMPTOMS

        all_symptom_list = list(ALL_SYMPTOMS)

        def _make_noisy_record(profile, doctors, patients):
            """Generate a training record with realistic noise."""
            data = generate_record(profile)
            symptoms = data['symptoms'].split(',')

            # Add random irrelevant symptoms (~30%)
            if random.random() < 0.30:
                available = [s for s in all_symptom_list if s not in symptoms]
                if available:
                    extra = random.sample(available, k=min(random.randint(1, 3), len(available)))
                    symptoms.extend(extra)

            # Remove a non-required symptom (~15%) to mimic incomplete reporting
            if random.random() < 0.15:
                optional = [s for s in symptoms if s not in profile.get('required_symptoms', [])]
                if len(optional) > 1:
                    symptoms.remove(random.choice(optional))

            data['symptoms'] = ','.join(symptoms)

            # Vital sign noise
            if data.get('temperature') and random.random() < 0.2:
                data['temperature'] = round(data['temperature'] + random.uniform(-1.0, 1.0), 1)
            if data.get('heart_rate') and random.random() < 0.2:
                data['heart_rate'] = data['heart_rate'] + random.randint(-15, 15)

            doctor = random.choice(doctors) if random.random() < 0.7 else None
            patient = random.choice(patients) if random.random() < 0.5 else None

            # Simulate prior predictions for ~40% of records
            predicted = ''
            pred_correct = False
            pred_confidence = None
            if random.random() < 0.4:
                if random.random() < 0.7:
                    predicted = data['confirmed_disease']
                    pred_correct = True
                    pred_confidence = round(random.uniform(0.5, 0.95), 2)
                else:
                    others = [p for p in DISEASE_PROFILES if p['disease'] != data['confirmed_disease']]
                    predicted = random.choice(others)['disease']
                    pred_correct = False
                    pred_confidence = round(random.uniform(0.2, 0.6), 2)

            return {
                **data,
                'doctor': doctor,
                'patient': patient,
                'predicted_disease': predicted,
                'predicted_confidence': pred_confidence,
                'prediction_correct': pred_correct,
            }

        # Progressive batches: 3, 4, 5, 6, 7 records per disease (= 60, 80, 100, 120, 140)
        # Total: 500 records across 5 rounds
        batch_sizes = [3, 4, 5, 6, 7]
        total_created = 0

        for batch_idx, per_disease in enumerate(batch_sizes):
            batch_count = 0
            for profile in DISEASE_PROFILES:
                for _ in range(per_disease):
                    rec = _make_noisy_record(profile, doctors, patients)
                    TrainingData.objects.create(
                        symptoms=rec['symptoms'],
                        confirmed_disease=rec['confirmed_disease'],
                        icd_code=rec['icd_code'],
                        patient_age=rec['patient_age'],
                        patient_gender=rec['patient_gender'],
                        temperature=rec['temperature'],
                        heart_rate=rec['heart_rate'],
                        blood_pressure_systolic=rec['blood_pressure_systolic'],
                        blood_pressure_diastolic=rec['blood_pressure_diastolic'],
                        spo2=rec['spo2'],
                        predicted_disease=rec['predicted_disease'],
                        predicted_confidence=rec['predicted_confidence'],
                        prediction_correct=rec['prediction_correct'],
                        used_for_training=False,
                        doctor=rec['doctor'],
                        patient=rec['patient'],
                    )
                    batch_count += 1

            total_created += batch_count
            self.stdout.write(f'  Batch {batch_idx + 1}: +{batch_count} records (total: {total_created})')

        self.stdout.write(self.style.SUCCESS(
            f'  {total_created} training records across {len(DISEASE_PROFILES)} diseases'
        ))

    # ─── Progressive ML Model Training ──────────────────────────
    def train_ml_models_progressive(self, doctors):
        """
        Train ML models progressively by deleting and re-adding data.
        Since train_model() uses TrainingData.objects.all(), we control
        what's in the DB at each training step.
        """
        self.stdout.write('Training ML models (5 progressive rounds)...')

        try:
            from apps.ai_services.ml_pipeline import train_model, HAS_ML
            if not HAS_ML:
                self.stdout.write(self.style.WARNING(
                    '  scikit-learn not installed - skipping ML training'
                ))
                return
        except ImportError:
            self.stdout.write(self.style.WARNING('  ML pipeline not available'))
            return

        # Save all records, then we'll delete and re-add in batches
        all_records_data = list(
            TrainingData.objects.all().order_by('id').values()
        )
        total = len(all_records_data)
        if total < 40:
            self.stdout.write(self.style.WARNING('  Not enough training data'))
            return

        # Clear all training data - we'll re-add in stages
        TrainingData.objects.all().delete()

        # 5 progressive rounds: 60, 140, 240, 360, 500 records
        # (cumulative from batch_sizes: 3*20=60, +4*20=80, +5*20=100, +6*20=120, +7*20=140)
        cumulative_counts = [60, 140, 240, 360, total]

        for round_idx, target_count in enumerate(cumulative_counts):
            # Add records up to target_count
            current = TrainingData.objects.count()
            records_to_add = all_records_data[current:target_count]

            for rec in records_to_add:
                # Remove auto-generated fields
                rec_copy = {k: v for k, v in rec.items()
                            if k not in ('id', 'created_at')}
                rec_copy['used_for_training'] = False
                TrainingData.objects.create(**rec_copy)

            try:
                triggered_by = random.choice(doctors)
                model = train_model(triggered_by=triggered_by)
                self.stdout.write(self.style.SUCCESS(
                    f'  Round {round_idx + 1}/5: {model.version} - '
                    f'Accuracy: {model.accuracy:.1%} '
                    f'({model.training_samples} samples, {model.num_classes} classes)'
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Round {round_idx + 1} failed: {e}'))

        # Final state: mark all as used, except last 25 for retrain progress
        TrainingData.objects.all().update(used_for_training=True)
        last_ids = list(
            TrainingData.objects.order_by('-id').values_list('id', flat=True)[:25]
        )
        TrainingData.objects.filter(id__in=last_ids).update(used_for_training=False)

        model_count = MLModelVersion.objects.count()
        active = MLModelVersion.objects.filter(is_active=True).first()
        if active:
            self.stdout.write(self.style.SUCCESS(
                f'  {model_count} model versions. Active: {active.version} ({active.accuracy:.1%})'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(f'  {model_count} model versions trained'))

    # ─── Summary ────────────────────────────────────────────────
    def print_summary(self):
        self.stdout.write(self.style.MIGRATE_HEADING('\n-- Data Summary --'))
        self.stdout.write(f'  Departments:        {Department.objects.count()}')
        self.stdout.write(f'  Users (total):      {User.objects.count()}')
        self.stdout.write(f'    - Admins:         {User.objects.filter(role="admin").count()}')
        self.stdout.write(f'    - Doctors:        {User.objects.filter(role="doctor").count()}')
        self.stdout.write(f'    - Receptionists:  {User.objects.filter(role="receptionist").count()}')
        self.stdout.write(f'    - Pharmacists:    {User.objects.filter(role="pharmacist").count()}')
        self.stdout.write(f'    - Patients:       {User.objects.filter(role="patient").count()}')
        self.stdout.write(f'  Doctor Profiles:    {DoctorProfile.objects.count()}')
        self.stdout.write(f'  Doctor Schedules:   {DoctorSchedule.objects.count()}')
        self.stdout.write(f'  Patient Profiles:   {Patient.objects.count()}')
        self.stdout.write(f'  Appointments:       {Appointment.objects.count()}')
        self.stdout.write(f'  Appointment Slots:  {AppointmentSlot.objects.count()}')
        self.stdout.write(f'  Medical Records:    {MedicalRecord.objects.count()}')
        self.stdout.write(f'  Diagnoses:          {Diagnosis.objects.count()}')
        self.stdout.write(f'  Prescriptions:      {Prescription.objects.count()}')
        self.stdout.write(f'  Prescription Items: {PrescriptionItem.objects.count()}')
        self.stdout.write(f'  Lab Tests:          {LabTest.objects.count()}')
        self.stdout.write(f'  Medicine Categories:{MedicineCategory.objects.count()}')
        self.stdout.write(f'  Medicines:          {Medicine.objects.count()}')
        self.stdout.write(f'  Stock Entries:      {MedicineStock.objects.count()}')
        self.stdout.write(f'  Transactions:       {StockTransaction.objects.count()}')
        self.stdout.write(f'  Notifications:      {Notification.objects.count()}')
        self.stdout.write(f'  Prediction Logs:    {PredictionLog.objects.count()}')
        self.stdout.write(f'  ML Training Data:   {TrainingData.objects.count()}')
        self.stdout.write(f'  ML Model Versions:  {MLModelVersion.objects.count()}')
        self.stdout.write(f'  Audit Logs:         {AuditLog.objects.count()}')

        self.stdout.write(self.style.MIGRATE_HEADING('\n-- Login Credentials (password: Test@123) --'))
        self.stdout.write('  Admin:         admin@hospital.com')
        self.stdout.write('  Doctors:       dr.ahmed@hospital.com, dr.fatima@hospital.com, ...')
        self.stdout.write('  Receptionist:  reception1@hospital.com')
        self.stdout.write('  Pharmacist:    pharma1@hospital.com')
        self.stdout.write('  Patient:       patient.john@email.com, patient.mary@email.com, ...')
        self.stdout.write('')
