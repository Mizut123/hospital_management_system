"""
Forms for patient management.
"""
from django import forms
from django.contrib.auth import get_user_model
from .models import Patient

User = get_user_model()


class PatientRegistrationForm(forms.ModelForm):
    """Form to register a new patient."""

    national_id = forms.CharField(
        max_length=14,
        min_length=14,
        required=True,
        help_text='National ID number (exactly 14 characters)',
        widget=forms.TextInput(attrs={
            'maxlength': '14',
            'minlength': '14',
            'pattern': r'\d{14}',
            'title': 'Must be exactly 14 digits',
        }),
    )
    blood_group = forms.ChoiceField(choices=[('', 'Select Blood Group')] + list(Patient.BLOOD_GROUPS), required=False)
    allergies = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False)
    chronic_conditions = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False)
    emergency_contact_name = forms.CharField(max_length=100, required=False)
    emergency_contact_phone = forms.CharField(max_length=20, required=False)
    # AI chatbot symptom assessment fields (stored as JSON)
    presenting_symptoms = forms.CharField(widget=forms.HiddenInput(), required=False)
    ai_triage_notes = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone', 'date_of_birth', 'gender', 'address']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
                'type': 'date',
            }),
            'gender': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
            }),
            'address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
                'rows': 2,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        extra_fields = ['national_id', 'blood_group', 'allergies', 'chronic_conditions',
                        'emergency_contact_name', 'emergency_contact_phone']
        for field_name in extra_fields:
            self.fields[field_name].widget.attrs.update({
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
            })

    def clean_national_id(self):
        """Validate that national_id is exactly 14 digits and unique."""
        national_id = self.cleaned_data.get('national_id', '').strip()
        if national_id:
            if len(national_id) != 14:
                raise forms.ValidationError('National ID must be exactly 14 characters.')
            if not national_id.isdigit():
                raise forms.ValidationError('National ID must contain digits only.')
            if Patient.objects.filter(national_id=national_id).exists():
                raise forms.ValidationError('A patient with this National ID already exists.')
        return national_id

    def save(self, commit=True):
        user = super().save(commit=False)
        # Generate random password for walk-in patients
        import secrets
        user.set_password(secrets.token_urlsafe(12))
        if commit:
            user.save()
        return user


class PatientProfileForm(forms.ModelForm):
    """Form to edit patient profile."""

    class Meta:
        model = Patient
        fields = ['blood_group', 'allergies', 'chronic_conditions', 'emergency_contact_name',
                  'emergency_contact_phone', 'emergency_contact_relation', 'insurance_provider',
                  'insurance_id', 'notes']
        widgets = {
            'blood_group': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
            }),
            'allergies': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
                'rows': 3,
            }),
            'chronic_conditions': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
                'rows': 3,
            }),
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
            }),
            'emergency_contact_phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
            }),
            'emergency_contact_relation': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
            }),
            'insurance_provider': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
            }),
            'insurance_id': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
                'rows': 3,
            }),
        }
