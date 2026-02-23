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

# Module-level OCR reader cache — loaded once on first use, reused on all subsequent calls.
# Loading takes ~10-30s the first time; after that each scan takes ~2-5s.
_ocr_reader = None

def _get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        _ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    return _ocr_reader


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
    Extract fields using the saved card profile.
    profile['mapping'] is a list whose index matches the OCR block order:
      e.g. ["last_name", "first_name", null, "gender_dob", null]
    The national_id is always taken from the last 8-14 digit sequence.
    """
    import re
    mapping = profile.get('mapping', [])
    result = {
        'national_id': '', 'first_name': '', 'last_name': '',
        'date_of_birth': '', 'gender': '', 'address': '',
    }

    for i, field_name in enumerate(mapping):
        if not field_name or i >= len(text_blocks):
            continue
        text = text_blocks[i].strip()

        if field_name == 'last_name':
            result['last_name'] = text

        elif field_name == 'first_name':
            result['first_name'] = text

        elif field_name == 'gender_dob':
            # Gender and DOB on same line: "M 01/05/1990" or "M 14 nov 2003"
            gm = re.search(r'\b([MF])\b', text, re.IGNORECASE)
            if gm:
                result['gender'] = 'male' if gm.group(1).upper() == 'M' else 'female'
            _parse_dob_into(text, result)

        elif field_name == 'date_of_birth':
            _parse_dob_into(text, result)

        elif field_name == 'gender':
            gm = re.search(r'\b([MF])\b', text, re.IGNORECASE)
            if gm:
                result['gender'] = 'male' if gm.group(1).upper() == 'M' else 'female'

    # ID number: exactly 14 digits.
    # OCR often adds spaces inside the number ("1234 5678 9012 34").
    # Collect ALL blocks that are exactly 14 digits when non-digits stripped;
    # take the LAST one — ID is at the bottom so OCR encounters it last.
    id_candidates = []
    for b in text_blocks:
        d = re.sub(r'\D', '', b)
        if len(d) == 14:
            id_candidates.append(d)
    if id_candidates:
        result['national_id'] = id_candidates[-1]
    # Fallback: contiguous 14-digit run in full joined text
    if not result['national_id']:
        all_ids = re.findall(r'\b(\d{14})\b', ' '.join(text_blocks))
        if all_ids:
            result['national_id'] = all_ids[-1]

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
    """View patient details."""

    model = Patient
    template_name = 'patients/patient_detail.html'
    context_object_name = 'patient'

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

            messages.success(request, f'Patient {user.get_full_name()} registered successfully. Patient ID: {user.patient_profile.patient_number}')
            return redirect('patients:detail', pk=user.patient_profile.pk)
    else:
        form = PatientRegistrationForm()

    # Get symptom keywords for chatbot
    try:
        from apps.ai_services.services import get_symptom_keywords
        symptom_keywords = get_symptom_keywords()
    except:
        symptom_keywords = []

    return render(request, 'patients/register.html', {
        'form': form,
        'symptom_keywords': symptom_keywords,
    })


@login_required
def search_patients(request):
    """Search for patients."""
    query = request.GET.get('q', '')
    patients = []

    if query:
        patients = Patient.objects.select_related('user').filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(patient_number__icontains=query) |
            Q(national_id__icontains=query) |
            Q(user__phone__icontains=query) |
            Q(user__email__icontains=query)
        )[:20]

    return render(request, 'patients/search.html', {
        'patients': patients,
        'query': query,
    })


@login_required
def patient_profile(request, pk):
    """Edit patient profile."""
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
            return redirect('patients:detail', pk=pk)
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

        return JsonResponse({
            'success': True,
            'symptoms_received': symptoms,
            'possible_conditions': suggestions[:3],
            'urgency': urgency,
            'urgency_message': urgency_message,
            'triage_notes': f"Patient reported: {', '.join(symptoms)}. AI assessment suggests possible: {', '.join([s['diagnosis'] for s in suggestions[:2]])}." if suggestions else f"Patient reported: {', '.join(symptoms)}.",
            'disclaimer': 'This is an automated pre-screening tool. Final diagnosis must be made by a healthcare professional.',
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def scan_id_card_api(request):
    """
    API: Scan a national ID card image and extract fields using EasyOCR.
    Free, runs locally on the server, supports Arabic + English text.

    POST multipart/form-data:
        id_image  — image file (JPEG / PNG / WebP)

    Returns JSON:
        { success: true, data: { national_id, first_name, last_name,
                                 date_of_birth, gender, address } }
    """
    from django.http import JsonResponse
    from PIL import Image

    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    image_file = request.FILES.get('id_image')
    if not image_file:
        return JsonResponse({'error': 'No image provided'}, status=400)

    # Reject obviously bad images (< 30 KB = blurry / thumbnail)
    if image_file.size < 30 * 1024:
        return JsonResponse(
            {'error': 'Image too small or low quality. Please retake the photo.'},
            status=400,
        )

    try:
        import easyocr
    except ImportError:
        return JsonResponse(
            {'error': 'OCR library not installed. Run: pip install easyocr',
             'data': {}},
            status=503,
        )

    try:
        from PIL import ImageEnhance, ImageFilter
        import numpy as np

        img = Image.open(image_file).convert('RGB')

        # ── Resize: 1600px preserves fine text; 900px was too small ─────
        max_w = 1600
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
        elif img.width < 600:
            # Upscale very small captures 2×
            img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)

        # ── Sharpen to remove phone-camera blur; keep colour ────────────
        # EasyOCR uses colour internally for text/background separation,
        # so we no longer convert to greyscale.
        img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=130, threshold=2))

        img_array = np.array(img)

        # ── Use module-level cached reader (loaded once, reused always) ─
        reader = _get_ocr_reader()
        results = reader.readtext(img_array, detail=1, paragraph=False, min_size=10)

        # Keep blocks with confidence > 20 % (lower threshold catches faint text)
        texts = [r[1] for r in results if r[2] > 0.20]

        # Use saved card profile for accurate field mapping, fall back to regex
        profile = _load_card_profile()
        if profile:
            extracted = _parse_id_text_with_profile(texts, profile)
        else:
            extracted = _parse_id_text(texts)

        return JsonResponse({
            'success': True,
            'data': extracted,
            'blocks_found': len(texts),
            'used_profile': profile is not None,
            # raw_blocks included so developers can inspect OCR output in browser devtools
            'raw_blocks': [{'i': i, 'text': t} for i, t in enumerate(texts)],
        })

    except Exception as e:
        return JsonResponse({'error': f'OCR processing failed: {str(e)}'}, status=500)


@login_required
def scan_id_learn_api(request):
    """
    API: Run OCR on an ID card template and return raw text blocks for calibration.
    POST multipart/form-data with 'id_image'.
    Returns numbered blocks so the user can assign each one to a form field.
    """
    from django.http import JsonResponse
    from PIL import Image, ImageEnhance, ImageFilter
    import numpy as np

    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    image_file = request.FILES.get('id_image')
    if not image_file:
        return JsonResponse({'error': 'No image provided'}, status=400)

    try:
        import easyocr
    except ImportError:
        return JsonResponse({'error': 'easyocr not installed'}, status=503)

    try:
        img = Image.open(image_file).convert('RGB')
        max_w = 1600
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
        elif img.width < 600:
            img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
        img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=130, threshold=2))
        img_array = np.array(img)
        h, w = img_array.shape[:2]

        reader = _get_ocr_reader()
        results = reader.readtext(img_array, detail=1, paragraph=False, min_size=10)

        blocks = []
        for bbox, text, conf in results:
            if conf < 0.20:
                continue
            y_top = min(pt[1] for pt in bbox)
            blocks.append({
                'index': len(blocks),
                'text': text,
                'y_pct': round(y_top / h * 100),
                'conf': round(conf * 100),
            })

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


def _parse_id_text(text_blocks):
    """
    Parse OCR text blocks from a national ID card with this field order:
        1. Surname (last name)
        2. First name
        3. Surname at birth  ← may be blank / absent, always skipped
        4. Gender            ← on the same line as date of birth
        5. Date of birth     ← same line as gender
        6. Signature         ← ignored
        7. ID number         ← bottom-left corner

    Supports French labels (NOM, PRÉNOM, SEXE, DATE DE NAISSANCE) and
    Arabic labels (اللقب, الاسم الشخصي, الجنس, تاريخ الازدياد).
    """
    import re

    # Words that look like names but are actually labels / card text — skip them.
    _NON_NAME = {
        'nom', 'prenom', 'prénom', 'surname', 'firstname', 'first', 'name',
        'naissance', 'birth', 'sexe', 'genre', 'gender', 'sex', 'signature',
        'republic', 'national', 'identity', 'card', 'kingdom', 'passport',
        'kingdom', 'date', 'lieu', 'place', 'valid', 'expiry', 'authority',
        'moroccan', 'algerian', 'tunisian', 'kingdom', 'democratic',
    }

    full_text = ' '.join(text_blocks)

    result = {
        'national_id': '',
        'first_name': '',
        'last_name': '',
        'date_of_birth': '',   # YYYY-MM-DD for Django's date input widget
        'gender': '',
        'address': '',
    }

    # ── 1. National ID number (bottom of card = LAST match in OCR top→bottom order) ─
    id_labeled = re.search(
        r'(?:N[°º]?\s*(?:CNIE?|CIN|NNI|ID)\b|رقم\s*(?:البطاقة|الهوية))[:\s]*(\d{14})',
        full_text, re.IGNORECASE,
    )
    if id_labeled:
        result['national_id'] = id_labeled.group(1)
    else:
        # OCR often adds spaces inside ("1234 5678 9012 34"); strip non-digits per block.
        # Collect ALL 14-digit blocks and take the LAST (ID is at the bottom).
        id_candidates = []
        for b in text_blocks:
            d = re.sub(r'\D', '', b)
            if len(d) == 14:
                id_candidates.append(d)
        if id_candidates:
            result['national_id'] = id_candidates[-1]
        if not result['national_id']:
            all_ids = re.findall(r'\b(\d{14})\b', full_text)
            if all_ids:
                result['national_id'] = all_ids[-1]

    # ── 2. Date of birth ────────────────────────────────────────────────────
    # Supports "01/05/1990", "01 / 05 / 1990", and "14 nov 2003" formats.
    _parse_dob_into(full_text, result)

    # ── 3. Gender (SEXE: M / SEXE: F pattern is common on Francophone cards) ─
    sexe_match = re.search(
        r'(?:SEXE?|GENRE|GENDER|الجنس)[:\s]*([MF])\b', full_text, re.IGNORECASE
    )
    if sexe_match:
        result['gender'] = 'male' if sexe_match.group(1).upper() == 'M' else 'female'
    else:
        for pat, val in [
            (r'\b(MALE|MASCULIN|MASC)\b', 'male'),
            (r'\b(FEMALE|F[ÉE]MININ|FEM)\b', 'female'),
            (r'\bذكر\b', 'male'),
            (r'\bأنثى\b', 'female'),
        ]:
            if re.search(pat, full_text, re.IGNORECASE):
                result['gender'] = val
                break

    # ── 4. Names: Surname → First name → Surname at birth (skip 3rd) ────────
    #
    # Strategy A: labeled fields (French or Arabic).
    _NAME_RE = r'[A-Za-z\u00C0-\u024F\u0600-\u06FF][A-Za-z\u00C0-\u024F\u0600-\u06FF\s\-]{1,49}'

    nom_m = re.search(
        r'(?:^|(?<=\s))NOM\b(?!\s*DE\s*NAISS)[:\s]+(' + _NAME_RE + r')',
        full_text, re.IGNORECASE,
    )
    prenom_m = re.search(
        r'PR[EÉ]NOMS?[:\s]+(' + _NAME_RE + r')',
        full_text, re.IGNORECASE,
    )
    ar_laqab = re.search(r'اللقب[:\s]+([\u0600-\u06FF\s]{2,40})', full_text)
    ar_ism   = re.search(r'الاسم\s*الشخصي[:\s]+([\u0600-\u06FF\s]{2,40})', full_text)

    if nom_m:
        result['last_name'] = nom_m.group(1).strip().split('\n')[0]
    elif ar_laqab:
        result['last_name'] = ar_laqab.group(1).strip()

    if prenom_m:
        result['first_name'] = prenom_m.group(1).strip().split('\n')[0]
    elif ar_ism:
        result['first_name'] = ar_ism.group(1).strip()

    # Strategy B: no labels found — use OCR block order.
    # Card layout: block[0]=surname, block[1]=first name, block[2]=surname-at-birth (skip).
    if not result['last_name'] and not result['first_name']:
        name_blocks = [
            t.strip() for t in text_blocks
            if re.match(
                r'^[A-Za-z\u00C0-\u024F\u0600-\u06FF][A-Za-z\u00C0-\u024F\u0600-\u06FF\s\-]{1,49}$',
                t.strip(),
            )
            and t.strip().lower() not in _NON_NAME
            and len(t.strip()) > 1
        ]

        if len(name_blocks) >= 2:
            result['last_name']  = name_blocks[0]   # 1st = surname
            result['first_name'] = name_blocks[1]   # 2nd = first name
            # name_blocks[2] would be surname-at-birth → intentionally skipped
        elif len(name_blocks) == 1:
            parts = name_blocks[0].split()
            if len(parts) >= 2:
                result['last_name']  = parts[0]
                result['first_name'] = ' '.join(parts[1:])
            else:
                result['last_name'] = name_blocks[0]

    # ── 5. Address (optional, not always on national ID cards) ──────────────
    addr_m = re.search(
        r'(?:Address|ADRESSE?|العنوان)[:\s]+(.{5,120})',
        full_text, re.IGNORECASE,
    )
    if addr_m:
        result['address'] = addr_m.group(1).strip()

    return result
