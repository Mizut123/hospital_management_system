"""
Forms for user authentication and management.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth import get_user_model

User = get_user_model()

INPUT_CLASS = 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200'


class LoginForm(AuthenticationForm):
    """Custom login form with styled fields."""

    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all',
            'placeholder': 'Email address',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all',
            'placeholder': 'Password',
        })
    )
    remember_me = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={
        'class': 'w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500',
    }))


class UserRegistrationForm(UserCreationForm):
    """Form for registering new users."""

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone', 'date_of_birth', 'gender', 'password1', 'password2']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
                'placeholder': 'Email address',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
                'placeholder': 'First name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
                'placeholder': 'Last name',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
                'placeholder': 'Phone number',
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
                'type': 'date',
            }),
            'gender': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
            'placeholder': 'Password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
            'placeholder': 'Confirm password',
        })


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'date_of_birth', 'gender', 'address', 'profile_image']
        widgets = {
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
                'rows': 3,
            }),
            'profile_image': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500',
            }),
        }


class AdminUserForm(forms.ModelForm):
    """Form for admins to create/edit users with role assignment."""

    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
            'placeholder': 'Leave blank to keep current password',
        })
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'role', 'phone', 'date_of_birth', 'gender', 'address', 'is_active']
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
            'role': forms.Select(attrs={
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
                'rows': 3,
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500',
            }),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class DoctorProfileForm(forms.Form):
    """Extra fields collected when creating/editing a doctor account."""

    department = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label='— Select department —',
        widget=forms.Select(attrs={'class': INPUT_CLASS}),
    )
    specialization = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. Cardiology, General Medicine'}),
    )
    qualification = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'e.g. MBBS, MD'}),
    )
    license_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Medical licence number'}),
    )
    experience_years = forms.IntegerField(
        min_value=0,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={'class': INPUT_CLASS}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Import inside __init__ to avoid circular import
        from apps.accounts.models import Department as Dept
        self.fields['department'].queryset = Dept.objects.filter(is_active=True).order_by('name')
