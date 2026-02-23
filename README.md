# Intelligent Hospital Management System (HMS)

A modern, scalable, AI-powered Hospital Management System built with Django, PostgreSQL, and Tailwind CSS.

## Features

### Core Modules
- **User Management**: Role-based access control (Admin, Doctor, Receptionist, Pharmacist, Patient)
- **Patient Management**: Registration, profiles, medical history, document uploads
- **Appointment System**: Online booking, queue management, check-in system
- **Medical Records**: Electronic Health Records (EHR), diagnoses, prescriptions, lab tests
- **Pharmacy**: Medicine database, stock management, prescription dispensing, alerts

### AI/ML Features
- **Patient Risk Prediction**: AI-calculated health risk scores
- **Wait Time Estimation**: Smart queue time predictions
- **Stock Forecasting**: Medicine demand prediction
- **Workload Optimization**: Doctor scheduling suggestions
- **Anomaly Detection**: Unusual pattern flagging

## Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 5.x |
| Database | PostgreSQL |
| Frontend | HTML, Tailwind CSS, Alpine.js |
| Charts | Chart.js |
| AI/ML | scikit-learn, pandas, numpy |

## Installation

### Prerequisites
- Python 3.10+
- PostgreSQL 15+
- Node.js (for Tailwind CSS, optional)

### Setup

1. **Clone and navigate to project**
```bash
cd hospital_management_system
```

2. **Create virtual environment**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure database**

Create a `.env` file:
```
SECRET_KEY=your-secret-key-here
DEBUG=True
DB_NAME=hospital_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
```

5. **Create database**
```bash
# In PostgreSQL
createdb hospital_db
```

6. **Run migrations**
```bash
python manage.py migrate
```

7. **Load demo data**
```bash
python manage.py setup_demo
```

8. **Run the server**
```bash
python manage.py runserver
```

9. **Access the application**
Open http://127.0.0.1:8000 in your browser

## Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@hospital.com | demo123 |
| Doctor | doctor@hospital.com | demo123 |
| Receptionist | reception@hospital.com | demo123 |
| Pharmacist | pharmacy@hospital.com | demo123 |
| Patient | patient@hospital.com | demo123 |

## Project Structure

```
hospital_management_system/
├── config/                 # Project configuration
│   ├── settings/          # Django settings
│   ├── urls.py            # Main URL routing
│   └── wsgi.py
├── apps/
│   ├── accounts/          # User authentication & roles
│   ├── patients/          # Patient management
│   ├── appointments/      # Scheduling & queue
│   ├── medical_records/   # EHR, prescriptions
│   ├── pharmacy/          # Medicine & stock
│   ├── notifications/     # Alert system
│   ├── analytics/         # Reports & dashboards
│   └── ai_services/       # ML models
├── templates/             # HTML templates
├── static/                # CSS, JS, images
├── fixtures/              # Sample data
└── ml_models/             # Trained ML models
```

## User Roles & Permissions

### Patient
- Book appointments online
- View medical history
- Access prescriptions and lab results
- Receive AI health insights

### Doctor
- View patient queue
- Access patient records
- Create diagnoses and prescriptions
- AI-assisted decision support

### Receptionist
- Register new patients
- Manage appointments
- Handle check-ins
- Queue management

### Pharmacist
- View prescription queue
- Dispense medications
- Manage stock levels
- Stock predictions

### Administrator
- User management
- Department configuration
- System analytics
- Audit logs

## AI/ML Models

### 1. Patient Risk Prediction
- **Algorithm**: Random Forest Classifier
- **Features**: Age, chronic conditions, visit frequency, medications
- **Output**: Risk score (0-100) and level

### 2. Wait Time Estimation
- **Algorithm**: Gradient Boosting
- **Features**: Queue position, doctor's avg time, time of day
- **Output**: Estimated wait in minutes

### 3. Stock Demand Prediction
- **Algorithm**: Time Series Analysis
- **Features**: Historical consumption, prescription trends
- **Output**: Days until stockout

## API Endpoints

### AI Services
- `GET /ai/risk/<patient_id>/` - Get patient risk score
- `GET /ai/wait-time/<appointment_id>/` - Get wait time estimate

## Development

### Running Tests
```bash
python manage.py test
```

### Creating Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Admin Panel
Access at http://127.0.0.1:8000/admin/

## Security Features

- Role-based access control
- Password hashing (Django's PBKDF2)
- CSRF protection
- Session management
- Audit logging

## Future Enhancements

- [ ] Mobile application (React Native)
- [ ] Telemedicine integration
- [ ] Billing module
- [ ] IoT device integration
- [ ] National health system API

## License

This project is developed for educational purposes as a capstone project.

## Contributors

Hospital Management System - Capstone Project
