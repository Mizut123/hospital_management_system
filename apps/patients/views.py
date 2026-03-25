"""
Views for patient management.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Q

from apps.accounts.models import User
from .models import Patient, PatientDocument
from .forms import PatientRegistrationForm, PatientProfileForm

import threading as _threading

# ── EasyOCR singleton ─────────────────────────────────────────────────────────
# Loaded ONCE in a background thread at startup.
# First scan may wait ~20s for the model; all subsequent scans take 1-3s.
_easyocr_reader = None
_easyocr_lock   = _threading.Lock()
_easyocr_ready  = False          # True once the reader is fully loaded


def _get_easyocr_reader():
    global _easyocr_reader, _easyocr_ready
    if _easyocr_reader is None:
        with _easyocr_lock:
            if _easyocr_reader is None:
                import easyocr
                _easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
                _easyocr_ready  = True
    return _easyocr_reader


def _warmup():
    try:
        _get_easyocr_reader()
    except Exception:
        pass


_threading.Thread(target=_warmup, daemon=True).start()


def _ocr_image(img):
    """
    OCR using EasyOCR — a deep-learning engine that handles real card photos
    (glare, shadows, perspective, coloured backgrounds) far better than
    rule-based Tesseract.

    The Reader is loaded once at server startup (~20 s one-off cost).
    Subsequent scans each take 1-3 s.
    """
    from PIL import Image as _Image, ImageEnhance
    import numpy as _np

    # 1200px is the sweet-spot for EasyOCR: enough detail to read card text,
    # small enough that CPU inference finishes in a few seconds.
    target_w = 1200
    if img.width != target_w:
        ratio = target_w / img.width
        img = img.resize((target_w, int(img.height * ratio)), _Image.LANCZOS)

    # Mild sharpness boost — EasyOCR prefers colour (RGB) input, not binary
    img = ImageEnhance.Sharpness(img.convert('RGB')).enhance(1.8)
    arr = _np.array(img)

    reader  = _get_easyocr_reader()
    results = reader.readtext(arr, detail=1, paragraph=False)

    # Sort top-to-bottom, filter very low-confidence detections
    results.sort(key=lambda r: r[0][0][1])
    blocks = [text.strip() for (_bbox, text, conf) in results
              if text.strip() and conf >= 0.15]
    return blocks


# ── Card profile (learned from a template scan) ────────────────────────────
import os as _os, json as _json

_CARD_PROFILE_PATH = _os.path.join(_os.path.dirname(__file__), 'card_profile.json')


def _load_card_profile():
    """Return saved card mapping dict, or None if not yet calibrated."""
    try:
        with open(_CARD_PROFILE_PATH, 'r', encoding='utf-8') as f:
            return _json.load(f)
    except (FileNotFoundError, _json.JSONDecodeError):
        return None


def _parse_dob_into(text, result):
    """
    Try to parse a date of birth from `text` and write it into result['date_of_birth'].
    Tries two formats:
      1. Numeric: "01/05/1990" or "01 / 05 / 1990" or "01-05-1990"
      2. Word month: "14 nov 2003" or "14 November 2003"
    """
    import re

    _MONTH_NUM = {
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',
    }

    # Format 1: numeric separators (with optional spaces)
    dm = re.search(r'(\d{1,2})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{4})', text)
    if dm:
        d, mo, y = dm.groups()
        result['date_of_birth'] = f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
        return

    # Format 2: "14 nov 2003" / "14 November 2003"
    mn = re.search(
        r'\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{4})\b',
        text, re.IGNORECASE,
    )
    if mn:
        d, mon, y = mn.group(1), mn.group(2)[:3].lower(), mn.group(3)
        result['date_of_birth'] = f"{y}-{_MONTH_NUM[mon]}-{d.zfill(2)}"


def _parse_id_text_with_profile(text_blocks, profile):
    """
    Run label-based extraction first (most reliable), then use the saved
    index-profile only to fill any fields that label extraction missed.
    This way a stale or slightly-off calibration never corrupts good data.
    """
    import re

    # 1 — label-based extraction is the primary result
    result = _parse_id_text(text_blocks)

    # 2 — profile fills only genuinely empty slots
    mapping = profile.get('mapping', [])
    for i, field_name in enumerate(mapping):
        if not field_name or i >= len(text_blocks):
            continue
        text = text_blocks[i].strip()
        if not text:
            continue

        if field_name == 'last_name' and not result['last_name']:
            result['last_name'] = _to_title(text)
        elif field_name == 'first_name' and not result['first_name']:
            result['first_name'] = _to_title(text)
        elif field_name == 'national_id' and not result['national_id']:
            result['national_id'] = text.upper()
        elif field_name == 'gender_dob':
            if not result['gender']:
                gm = re.search(r'\b([MF])\b', text, re.IGNORECASE)
                if gm:
                    result['gender'] = 'male' if gm.group(1).upper() == 'M' else 'female'
            if not result['date_of_birth']:
                _parse_dob_into(text, result)
        elif field_name == 'date_of_birth' and not result['date_of_birth']:
            _parse_dob_into(text, result)
        elif field_name == 'gender' and not result['gender']:
            gm = re.search(r'\b([MF])\b', text, re.IGNORECASE)
            if gm:
                result['gender'] = 'male' if gm.group(1).upper() == 'M' else 'female'

    return result


class PatientListView(LoginRequiredMixin, ListView):
    """List patients (for doctors and staff)."""

    model = Patient
    template_name = 'patients/patient_list.html'
    context_object_name = 'patients'
    paginate_by = 20

    def get_queryset(self):
        queryset = Patient.objects.select_related('user').all()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(patient_number__icontains=search) |
                Q(national_id__icontains=search) |
                Q(user__phone__icontains=search)
            )
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        return context


class PatientDetailView(LoginRequiredMixin, DetailView):
    """View patient details. The pk in the URL is the User pk, not the Patient profile pk."""

    model = Patient
    template_name = 'patients/patient_detail.html'
    context_object_name = 'patient'

    def get_object(self, queryset=None):
        # All templates link using user.pk (e.g. appointment.patient.pk).
        # Look up the Patient profile by user_id so both sources resolve correctly.
        user_pk = self.kwargs['pk']
        return get_object_or_404(Patient, user_id=user_pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.object

        # Get medical records
        context['medical_records'] = patient.user.medical_records.order_by('-visit_date')[:10]

        # Get appointments
        context['appointments'] = patient.user.patient_appointments.order_by('-scheduled_date')[:10]

        # Get prescriptions
        context['prescriptions'] = patient.user.prescriptions.order_by('-created_at')[:10]

        # Get risk score from AI
        try:
            from apps.ai_services.services import get_patient_risk_score
            context['ai_risk'] = get_patient_risk_score(patient.user)
        except:
            context['ai_risk'] = None

        return context


@login_required
def register_patient(request):
    """Register a new patient (for receptionists)."""
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = User.Role.PATIENT
            user.save()

            # Build notes from AI triage if provided
            presenting_symptoms = form.cleaned_data.get('presenting_symptoms', '')
            ai_triage_notes = form.cleaned_data.get('ai_triage_notes', '')
            notes = ''
            if presenting_symptoms or ai_triage_notes:
                notes = f"Initial Symptoms: {presenting_symptoms}\n\nAI Triage Notes: {ai_triage_notes}"

            # Create patient profile with all fields
            Patient.objects.create(
                user=user,
                national_id=form.cleaned_data.get('national_id', ''),
                blood_group=form.cleaned_data.get('blood_group', ''),
                allergies=form.cleaned_data.get('allergies', ''),
                chronic_conditions=form.cleaned_data.get('chronic_conditions', ''),
                emergency_contact_name=form.cleaned_data.get('emergency_contact_name', ''),
                emergency_contact_phone=form.cleaned_data.get('emergency_contact_phone', ''),
                notes=notes,
            )

            messages.success(request, f'Patient {user.get_full_name()} registered successfully. Patient ID: {user.patient_profile.national_id or user.patient_profile.patient_number}')
            return redirect('patients:detail', pk=user.pk)
    else:
        form = PatientRegistrationForm()

    # Get symptom keywords for chatbot
    try:
        from apps.ai_services.services import get_symptom_keywords
        symptom_keywords = get_symptom_keywords()
    except:
        symptom_keywords = []

    response = render(request, 'patients/register.html', {
        'form': form,
        'symptom_keywords': symptom_keywords,
    })
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return response


@login_required
def search_patients(request):
    """Search for patients with enhanced filtering and live JSON mode."""
    from django.http import JsonResponse as _JR

    query       = request.GET.get('q', '').strip()
    risk_filter = request.GET.get('risk', '')
    is_api      = request.GET.get('format') == 'json'

    qs = Patient.objects.select_related('user')

    # Doctors see only patients they have had appointments with
    if request.user.is_doctor:
        from apps.appointments.models import Appointment
        allocated_ids = Appointment.objects.filter(
            doctor=request.user
        ).values_list('patient_id', flat=True).distinct()
        qs = qs.filter(user_id__in=allocated_ids)

    if query:
        qs = qs.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(patient_number__icontains=query) |
            Q(national_id__icontains=query) |
            Q(user__phone__icontains=query) |
            Q(user__email__icontains=query) |
            Q(blood_group__icontains=query) |
            Q(chronic_conditions__icontains=query)
        )
    if risk_filter:
        qs = qs.filter(risk_level=risk_filter)

    patients = qs[:30]

    if is_api:
        from apps.appointments.models import Appointment as _Appt
        data = []
        for p in patients:
            last_appt = _Appt.objects.filter(patient=p.user).order_by('-scheduled_date').first()
            # Prefer NID as the displayed patient identifier
            display_id = p.national_id if p.national_id else p.patient_number
            data.append({
                'id': p.pk,
                'name': p.user.get_full_name(),
                'initials': (p.user.first_name[:1] + p.user.last_name[:1]).upper(),
                'patient_number': display_id,
                'national_id': p.national_id or '',
                'phone': p.user.phone or '',
                'blood_group': p.blood_group or '',
                'risk_level': p.risk_level,
                'risk_score': p.risk_score,
                'chronic_conditions': p.chronic_conditions[:60] if p.chronic_conditions else '',
                'last_appointment': last_appt.scheduled_date.strftime('%d %b %Y') if last_appt else '',
                'detail_url': f'/patients/{p.user_id}/',
            })
        return _JR({'patients': data, 'count': len(data)})

    return render(request, 'patients/search.html', {
        'patients': patients,
        'query': query,
        'risk_filter': risk_filter,
    })


@login_required
def patient_profile(request, pk):
    """Edit patient profile. pk is the Patient profile pk (from the /edit/ URL)."""
    patient = get_object_or_404(Patient, pk=pk)

    # Check permissions
    if not (request.user.is_admin or request.user.is_receptionist or
            request.user.is_doctor or request.user == patient.user):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = PatientProfileForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Patient profile updated successfully.')
            return redirect('patients:detail', pk=patient.user_id)
    else:
        form = PatientProfileForm(instance=patient)

    return render(request, 'patients/profile_edit.html', {
        'form': form,
        'patient': patient,
    })


@login_required
def symptom_chatbot_api(request):
    """
    API endpoint for the symptom assessment chatbot.

    POST: Process symptoms and return triage assessment
    """
    from django.http import JsonResponse
    import json

    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    try:
        data = json.loads(request.body)
        symptoms = data.get('symptoms', [])

        if not symptoms:
            return JsonResponse({'error': 'No symptoms provided'}, status=400)

        # Get AI diagnosis suggestions
        from apps.ai_services.services import get_ai_diagnosis_suggestions

        suggestions = get_ai_diagnosis_suggestions(symptoms)

        # Determine urgency level based on symptoms
        urgent_symptoms = ['chest_pain', 'shortness_of_breath', 'difficulty_breathing', 'severe_headache']
        symptom_normalized = [s.lower().replace(' ', '_') for s in symptoms]

        urgency = 'routine'
        urgency_message = 'Your symptoms appear to be manageable. Please proceed with registration.'

        for urgent in urgent_symptoms:
            if urgent in symptom_normalized:
                urgency = 'urgent'
                urgency_message = 'Some of your symptoms may require prompt attention. Please inform the staff immediately.'
                break

        # Check for multiple concerning symptoms
        if len(suggestions) > 0 and suggestions[0]['confidence'] > 70:
            top_diagnosis = suggestions[0]['diagnosis']
            if 'Infarction' in top_diagnosis or 'Failure' in top_diagnosis:
                urgency = 'emergency'
                urgency_message = 'Your symptoms suggest you may need immediate medical attention. Please alert staff immediately!'

        # Suggest doctors based on top condition
        suggested_doctors = []
        if suggestions:
            try:
                from apps.ai_services.services import suggest_doctors_for_condition
                suggested_doctors = suggest_doctors_for_condition(suggestions[0]['diagnosis'])
            except Exception:
                pass

        return JsonResponse({
            'success': True,
            'symptoms_received': symptoms,
            'possible_conditions': suggestions[:3],
            'urgency': urgency,
            'urgency_message': urgency_message,
            'triage_notes': f"Patient reported: {', '.join(symptoms)}. AI assessment suggests possible: {', '.join([s['diagnosis'] for s in suggestions[:2]])}." if suggestions else f"Patient reported: {', '.join(symptoms)}.",
            'disclaimer': 'This is an automated pre-screening tool. Final diagnosis must be made by a healthcare professional.',
            'suggested_doctors': suggested_doctors,
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def scan_id_status_api(request):
    """GET: returns whether the EasyOCR model has finished loading."""
    from django.http import JsonResponse
    return JsonResponse({'ready': _easyocr_ready})


def scan_id_card_api(request):
    """
    POST multipart/form-data with 'id_image'.
    Runs OCR synchronously and returns extracted fields directly.
    Response: { success, data: { national_id, first_name, last_name,
                                  date_of_birth, gender, address },
                blocks_found, raw_blocks }
    """
    from django.http import JsonResponse
    from PIL import Image

    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    image_file = request.FILES.get('id_image')
    if not image_file:
        return JsonResponse({'error': 'No image provided'}, status=400)

    if image_file.size < 8 * 1024:
        return JsonResponse({'error': 'Image too small — use a clearer photo.'}, status=400)

    try:
        img = Image.open(image_file).convert('RGB')
        # Keep between 1200-1500 px wide: wide enough for Tesseract accuracy,
        # small enough for fast processing (< 1 s on a typical server)
        max_w, min_w = 1500, 1200
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
        elif img.width < min_w:
            ratio = min_w / img.width
            img = img.resize((min_w, int(img.height * ratio)), Image.LANCZOS)
    except Exception as e:
        return JsonResponse({'error': f'Could not open image: {e}'}, status=400)

    try:
        texts     = _ocr_image(img)
        profile   = _load_card_profile()
        extracted = _parse_id_text_with_profile(texts, profile) if profile else _parse_id_text(texts)
        return JsonResponse({
            'success':      True,
            'data':         extracted,
            'blocks_found': len(texts),
            'used_profile': profile is not None,
            'raw_blocks':   [{'i': i, 'text': t} for i, t in enumerate(texts)],
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def scan_id_learn_api(request):
    """
    API: Run OCR on an ID card template and return raw text blocks for calibration.
    POST multipart/form-data with 'id_image'.
    Returns numbered blocks so the user can assign each one to a form field.
    """
    from django.http import JsonResponse
    from PIL import Image

    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    image_file = request.FILES.get('id_image')
    if not image_file:
        return JsonResponse({'error': 'No image provided'}, status=400)

    try:
        img = Image.open(image_file).convert('RGB')
        max_w = 2000
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)

        texts = _ocr_image(img)
        blocks = [{'index': i, 'text': t, 'y_pct': 0, 'conf': 100}
                  for i, t in enumerate(texts)]

        return JsonResponse({'success': True, 'blocks': blocks})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def save_card_profile_api(request):
    """
    API: Save the user's field mapping so future scans use it.
    POST JSON: { "mapping": ["last_name", "first_name", null, "gender_dob", null] }
    Values can be: "last_name", "first_name", "gender_dob", "date_of_birth",
                   "gender", "national_id", or null (skip this block).
    """
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    if not (request.user.is_admin or request.user.is_receptionist):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        import json as _j
        data = _j.loads(request.body)
        mapping = data.get('mapping', [])

        valid = {'last_name', 'first_name', 'gender_dob', 'date_of_birth',
                 'gender', 'national_id', None}
        if not all(v in valid for v in mapping):
            return JsonResponse({'error': 'Invalid field name in mapping'}, status=400)

        profile = {'version': 1, 'mapping': mapping}
        with open(_CARD_PROFILE_PATH, 'w', encoding='utf-8') as f:
            _j.dump(profile, f, indent=2)

        return JsonResponse({'success': True,
                             'message': f'Card profile saved ({len(mapping)} blocks).'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# Mobile-to-laptop QR bridge
# Flow: laptop generates token → shows QR → phone opens URL → takes photo →
#       uploads here → result stored in cache → laptop polls → auto-fills form
# ─────────────────────────────────────────────────────────────────────────────

def generate_scan_token(request):
    """Generate a short-lived token for a cross-device ID scan session."""
    from django.http import JsonResponse
    from django.core.cache import cache
    import uuid

    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    token = uuid.uuid4().hex
    cache.set(f'mobilescan_{token}', {'status': 'pending'}, 300)   # 5-min TTL
    return JsonResponse({'token': token})


def mobile_scan_page(request):
    """
    Mobile-friendly page opened by phone after scanning the QR code.
    No login required — access is secured by the short-lived token.
    """
    token = request.GET.get('token', '')
    from django.core.cache import cache
    if not token or cache.get(f'mobilescan_{token}') is None:
        return render(request, 'patients/mobile_scan.html', {'error': 'Link expired or invalid. Ask the receptionist to generate a new QR code.'})
    return render(request, 'patients/mobile_scan.html', {'token': token, 'error': None})


def mobile_scan_upload(request):
    """
    Receive photo from phone, run OCR, store result in cache.
    No login required — secured by token.
    """
    from django.http import JsonResponse
    from django.core.cache import cache

    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    token = request.GET.get('token') or request.POST.get('token', '')
    if not token:
        return JsonResponse({'error': 'No token'}, status=400)

    session = cache.get(f'mobilescan_{token}')
    if session is None:
        return JsonResponse({'error': 'Session expired. Ask the receptionist to generate a new QR code.'}, status=400)

    image_file = request.FILES.get('id_image')
    if not image_file:
        return JsonResponse({'error': 'No image provided'}, status=400)

    if image_file.size < 8 * 1024:
        return JsonResponse({'error': 'Image too small. Please use a clearer photo.'}, status=400)

    try:
        from PIL import Image

        img = Image.open(image_file).convert('RGB')
        max_w = 2000
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)

        texts = _ocr_image(img)
        profile = _load_card_profile()
        extracted = _parse_id_text_with_profile(texts, profile) if profile else _parse_id_text(texts)

        cache.set(f'mobilescan_{token}', {'status': 'done', 'data': extracted}, 300)
        return JsonResponse({'success': True, 'message': 'Done! Return to the computer.'})

    except Exception as e:
        cache.set(f'mobilescan_{token}', {'status': 'error', 'error': str(e)}, 300)
        return JsonResponse({'error': f'Processing failed: {str(e)}'}, status=500)


def poll_scan_result(request):
    """Laptop polls this every 2 s to check if the mobile photo has been processed."""
    from django.http import JsonResponse
    from django.core.cache import cache

    token = request.GET.get('token', '')
    if not token:
        return JsonResponse({'status': 'error', 'error': 'No token'}, status=400)

    session = cache.get(f'mobilescan_{token}')
    if session is None:
        return JsonResponse({'status': 'expired'})
    return JsonResponse(session)


def _to_title(s):
    """Convert OCR all-caps name to Title Case: "JOHN ADAM" → "John Adam"."""
    return ' '.join(w.capitalize() for w in s.split()) if s else s


def _parse_id_text(text_blocks):
    """
    Extract fields from a Mauritius National Identity Card (English).
    Card layout (each item is its own line in the OCR output):
        REPUBLIC OF MAURITIUS
        NATIONAL IDENTITY CARD
        SURNAME
        <surname value>
        GIVEN NAMES
        <given names value>
        DATE OF BIRTH
        <dd/mm/yyyy>
        SEX
        <M or F>
        NIC
        <nic value>
    """
    import re

    lines = [b.strip() for b in text_blocks if b.strip()]
    full  = ' '.join(lines)

    result = {
        'national_id': '', 'first_name': '', 'last_name': '',
        'date_of_birth': '', 'gender': '', 'address': '',
    }

    # ── Keywords that mark a header/label line (never a value) ───────────────
    # Allow optional spaces inside multi-word labels (EasyOCR sometimes merges)
    _LABEL = re.compile(
        r'^(?:REPUBLIC|NATIONAL|IDENTITY|CARD|MAURITIUS|BIOMETRIC|'
        r'SURNAME|GIVEN\s*NAMES?|FIRST\s*NAMES?|DATE\s*OF\s*BIRTH|'
        r'SEX[E]?|NIC|SIGNATURE|VALID|EXPIRY|HOLDER|OF|'
        r'NATIONALIDENTITY|IDENTITYCARD)$',           # merged OCR variants
        re.IGNORECASE,
    )

    def _words(line):
        """Return the set of uppercase words in a line, punctuation stripped."""
        return set(re.sub(r'[^\w\s]', '', line.upper()).split())

    def is_label(line):
        # A line is a label if ANY of its individual words matches a known label
        # keyword.  This handles bilingual lines like "SEX / SEXE" or "NIC / CIN"
        # where the old approach concatenated to "SEXSEXE"/"NICCIN" and failed.
        return any(bool(_LABEL.match(w)) for w in _words(line))

    def next_value(after_idx):
        """Return the first non-label line after after_idx, or ''."""
        for j in range(after_idx + 1, len(lines)):
            if not is_label(lines[j]):
                return lines[j]
        return ''

    def _gender_from(text):
        """Return 'male'/'female' from a raw OCR value, or ''."""
        val = re.sub(r'[^\w]', '', text).upper()
        if val in ('M', 'MALE', 'MASCULIN'):
            return 'male'
        if val in ('F', 'FEMALE', 'FEMININ', 'FEMININE'):
            return 'female'
        # Single-char with word boundary in original text
        m = re.search(r'\b([MF])\b', text, re.IGNORECASE)
        if m:
            return 'male' if m.group(1).upper() == 'M' else 'female'
        return ''

    # ── Pass 1: label → next non-label line ──────────────────────────────────
    for i, line in enumerate(lines):
        wset = _words(line)

        if 'SURNAME' in wset and not result['last_name']:
            result['last_name'] = next_value(i)

        elif wset & {'GIVENNAMES', 'FIRSTNAME', 'FIRSTNAMES'} or \
             ('GIVEN' in wset and ('NAME' in wset or 'NAMES' in wset)) or \
             ('FIRST' in wset and ('NAME' in wset or 'NAMES' in wset)):
            if not result['first_name']:
                result['first_name'] = next_value(i)

        elif ('DATE' in wset and 'BIRTH' in wset) or 'DOB' in wset:
            if not result['date_of_birth']:
                _parse_dob_into(next_value(i), result)

        elif 'SEX' in wset or 'SEXE' in wset:
            if not result['gender']:
                # Value may be inline: "SEX / SEXE  M"  OR on the next line: "M"
                # Strip the label words from the current line first
                stripped = re.sub(r'\b(?:SEX[E]?)\b', '', line, flags=re.IGNORECASE)
                stripped = re.sub(r'[^\w]', '', stripped).upper()   # e.g. "M" or ""
                g = _gender_from(stripped) if stripped else ''
                result['gender'] = g if g else _gender_from(next_value(i))

        elif 'NIC' in wset:
            if not result['national_id']:
                # Remove NIC/CIN label words, then look for a NIC-shaped token
                # e.g. "NIC / CIN  T141103019109A" → find "T141103019109A"
                no_label = re.sub(r'\b(?:NIC|CIN|N[Oº°]?)\b', '', line, flags=re.IGNORECASE)
                nic_m = re.search(
                    r'[A-Z]\d{4,14}[A-Z]?|\d{6}/\d{4}',
                    no_label, re.IGNORECASE,
                )
                if nic_m:
                    result['national_id'] = re.sub(r'\s+', '', nic_m.group(0)).upper()
                else:
                    nv = next_value(i)
                    if nv:
                        result['national_id'] = re.sub(r'\s+', '', nv).upper()

    # ── Pass 2: inline "LABEL value" on the same line ────────────────────────
    # Stop capture before the next known label keyword
    _STOP = r'(?=\s+(?:SURNAME|GIVEN|FIRST|DATE|SEX|NIC|SIGNATURE|$))'
    if not result['last_name']:
        m = re.search(r'\bSURNAME\b[:\s]+(\S.*?)' + _STOP, full, re.IGNORECASE)
        if m:
            result['last_name'] = m.group(1).strip()

    if not result['first_name']:
        m = re.search(r'\bGIVEN\s*NAMES?\b[:\s]+(\S.*?)' + _STOP, full, re.IGNORECASE)
        if not m:
            m = re.search(r'\bFIRST\s*NAMES?\b[:\s]+(\S.*?)' + _STOP, full, re.IGNORECASE)
        if m:
            result['first_name'] = m.group(1).strip()

    if not result['date_of_birth']:
        # Try "DATE OF BIRTH  12/07/1985" on the same line
        m = re.search(r'\bDATE\s*OF\s*BIRTH\b[:\s]+(\S[^\n]*)', full, re.IGNORECASE)
        if m:
            _parse_dob_into(m.group(1), result)
    if not result['date_of_birth']:
        _parse_dob_into(full, result)

    if not result['gender']:
        # "SEX / SEXE M" — find SEX label then the first standalone M or F nearby
        gm = re.search(r'\bSEXE?\b[^MF\n]{0,30}\b([MF])\b', full, re.IGNORECASE)
        if gm:
            result['gender'] = 'male' if gm.group(1).upper() == 'M' else 'female'
    if not result['gender']:
        if re.search(r'\bMASCULIN\b', full, re.IGNORECASE):
            result['gender'] = 'male'
        elif re.search(r'\bFEMININ\b', full, re.IGNORECASE):
            result['gender'] = 'female'
    if not result['gender']:
        # Last resort: scan every OCR block for one that is purely "M" or "F"
        # (ID cards show gender as a single letter on its own line)
        for block in lines:
            b = re.sub(r'[^\w]', '', block.strip()).upper()
            if b == 'M':
                result['gender'] = 'male'
                break
            elif b == 'F':
                result['gender'] = 'female'
                break

    if not result['national_id']:
        # "NIC / CIN T141103019109A" — skip "/ CIN" bilingual noise then grab NIC token
        m = re.search(
            r'\bNIC\b(?:\s*/\s*\w+)*\s+([A-Z]\d{4,14}[A-Z]?|\d{6}/\d{4})',
            full, re.IGNORECASE,
        )
        if m:
            result['national_id'] = re.sub(r'\s+', '', m.group(1)).upper()

    if not result['national_id']:
        # Old format: DDMMYY/NNNN  e.g. 120485/1234
        m = re.search(r'\b(\d{6}/\d{4})\b', full)
        if m:
            result['national_id'] = m.group(1)

    if not result['national_id']:
        # New biometric formats:
        #   letter + 6-14 digits + optional trailing letter  e.g. T141103019109A
        #   letter + 6-12 digits + optional /NNNN            e.g. A123456/1234
        m = re.search(r'\b([A-Z]\d{6,14}[A-Z]?(?:/\d{4})?)\b', full, re.IGNORECASE)
        if m:
            result['national_id'] = m.group(1).upper()

    if not result['national_id']:
        # Last resort: scan every OCR block for a standalone NIC-shaped token
        _NIC_RE = re.compile(
            r'^(?:[A-Z]\d{4,14}[A-Z]?|\d{6}/\d{4})$', re.IGNORECASE
        )
        for block in lines:
            b = re.sub(r'\s+', '', block.strip()).upper()
            if _NIC_RE.match(b):
                result['national_id'] = b
                break

    # ── Tidy up: title-case names, strip punctuation/noise ───────────────────
    def _clean_name(s):
        return _to_title(re.sub(r'[^\w\s\-]', '', s).strip()) if s else s

    result['last_name']   = _clean_name(result['last_name'])
    result['first_name']  = _clean_name(result['first_name'])
    # Keep word-chars and internal slashes (old NIC format); strip everything else
    result['national_id'] = re.sub(r'[^\w/]', '', result['national_id']).strip().strip('/')

    return result
