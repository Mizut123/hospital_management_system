"""
Views for pharmacy management.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import F, Sum, Count, Q
from datetime import timedelta
import json

from .models import Medicine, MedicineStock, MedicineCategory, StockTransaction
from .forms import MedicineForm, MedicineStockForm, StockEditForm, StockAdjustmentForm, MedicineCategoryForm
from apps.medical_records.models import Prescription


@login_required
def prescriptions_queue(request):
    """View pending prescriptions for dispensing."""
    if not request.user.is_pharmacist:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    prescriptions = Prescription.objects.filter(
        status='pending'
    ).select_related('patient', 'doctor').prefetch_related('items__medicine').order_by('-created_at')

    # Get stats
    today = timezone.now().date()
    pending_count = prescriptions.count()
    dispensed_today = Prescription.objects.filter(
        status='dispensed',
        dispensed_at__date=today
    ).count()

    # Stock alerts count
    stock_alerts = MedicineStock.objects.filter(
        quantity__lte=F('reorder_level')
    ).count()

    return render(request, 'pharmacy/prescriptions.html', {
        'prescriptions': prescriptions,
        'pending_count': pending_count,
        'dispensed_today': dispensed_today,
        'stock_alerts': stock_alerts,
    })


@login_required
def dispense_prescription(request, pk):
    """Dispense a prescription with proper stock tracking."""
    if not request.user.is_pharmacist:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    prescription = get_object_or_404(Prescription, pk=pk)

    if request.method == 'POST':
        all_dispensed = True
        insufficient_stock = []

        for item in prescription.items.filter(is_dispensed=False):
            remaining_qty = item.quantity

            # Get available stock batches (FIFO - earliest expiry first)
            stocks = MedicineStock.objects.filter(
                medicine=item.medicine,
                quantity__gt=0,
                expiry_date__gt=timezone.now().date()
            ).order_by('expiry_date')

            total_available = stocks.aggregate(total=Sum('quantity'))['total'] or 0

            if total_available < remaining_qty:
                insufficient_stock.append({
                    'medicine': item.medicine.name,
                    'required': remaining_qty,
                    'available': total_available
                })
                all_dispensed = False
                continue

            # Dispense from multiple batches if needed
            for stock in stocks:
                if remaining_qty <= 0:
                    break

                dispense_qty = min(stock.quantity, remaining_qty)

                # Create StockTransaction record
                StockTransaction.objects.create(
                    stock=stock,
                    transaction_type='out',
                    quantity=dispense_qty,
                    reference=f'Prescription #{prescription.pk}',
                    notes=f'Dispensed to {prescription.patient.get_full_name()}',
                    performed_by=request.user
                )

                # Update stock quantity
                stock.quantity -= dispense_qty
                stock.save()

                remaining_qty -= dispense_qty

            item.is_dispensed = True
            item.save()

        if insufficient_stock:
            for item in insufficient_stock:
                messages.warning(
                    request,
                    f"Insufficient stock for {item['medicine']}: Required {item['required']}, Available {item['available']}"
                )

        if all_dispensed:
            prescription.status = 'dispensed'
            messages.success(request, f'Prescription #{prescription.pk} fully dispensed.')
        else:
            prescription.status = 'partial'
            messages.info(request, f'Prescription #{prescription.pk} partially dispensed.')

        prescription.dispensed_by = request.user
        prescription.dispensed_at = timezone.now()
        prescription.save()

        return redirect('pharmacy:prescriptions')

    # Check stock availability for display
    items_with_stock = []
    for item in prescription.items.all():
        available = MedicineStock.objects.filter(
            medicine=item.medicine,
            quantity__gt=0,
            expiry_date__gt=timezone.now().date()
        ).aggregate(total=Sum('quantity'))['total'] or 0

        items_with_stock.append({
            'item': item,
            'available_stock': available,
            'sufficient': available >= item.quantity
        })

    return render(request, 'pharmacy/dispense.html', {
        'prescription': prescription,
        'items_with_stock': items_with_stock,
    })


@login_required
def medicines_list(request):
    """List all medicines."""
    if not (request.user.is_pharmacist or request.user.is_doctor or request.user.is_admin):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    medicines = Medicine.objects.filter(is_active=True).select_related('category')
    categories = MedicineCategory.objects.all()

    category_filter = request.GET.get('category')
    search = request.GET.get('search')

    if category_filter:
        medicines = medicines.filter(category_id=category_filter)
    if search:
        medicines = medicines.filter(
            Q(name__icontains=search) | Q(generic_name__icontains=search)
        )

    # Annotate with stock info
    medicines = medicines.annotate(
        current_stock=Sum('stock_entries__quantity', filter=Q(
            stock_entries__quantity__gt=0,
            stock_entries__expiry_date__gt=timezone.now().date()
        ))
    )

    return render(request, 'pharmacy/medicines.html', {
        'medicines': medicines,
        'categories': categories,
        'current_category': category_filter,
        'search': search or '',
    })


@login_required
def add_medicine(request):
    """Add a new medicine."""
    if not request.user.is_pharmacist:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = MedicineForm(request.POST)
        if form.is_valid():
            medicine = form.save()
            messages.success(request, f'Medicine "{medicine.name}" added successfully.')
            return redirect('pharmacy:medicines')
    else:
        form = MedicineForm()

    categories = MedicineCategory.objects.all()
    return render(request, 'pharmacy/add_medicine.html', {
        'form': form,
        'categories': categories,
    })


@login_required
def edit_medicine(request, pk):
    """Edit an existing medicine."""
    if not request.user.is_pharmacist:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    medicine = get_object_or_404(Medicine, pk=pk)

    if request.method == 'POST':
        form = MedicineForm(request.POST, instance=medicine)
        if form.is_valid():
            form.save()
            messages.success(request, f'Medicine "{medicine.name}" updated successfully.')
            return redirect('pharmacy:medicines')
    else:
        form = MedicineForm(instance=medicine)

    return render(request, 'pharmacy/edit_medicine.html', {
        'form': form,
        'medicine': medicine,
    })


@login_required
def stock_management(request):
    """Manage medicine stock with statistics."""
    if not request.user.is_pharmacist:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    today = timezone.now().date()

    all_stocks = MedicineStock.objects.select_related('medicine__category')

    # Calculate statistics on the full set
    total_items  = all_stocks.count()
    in_stock     = all_stocks.filter(quantity__gt=F('reorder_level')).count()
    low_stock    = all_stocks.filter(quantity__gt=0, quantity__lte=F('reorder_level')).count()
    out_of_stock = all_stocks.filter(quantity=0).count()

    # Filters
    status_filter = request.GET.get('status', '')
    search_q      = request.GET.get('q', '').strip()

    stocks = all_stocks.order_by('expiry_date')

    if status_filter == 'low':
        stocks = stocks.filter(quantity__gt=0, quantity__lte=F('reorder_level'))
    elif status_filter == 'out':
        stocks = stocks.filter(quantity=0)
    elif status_filter == 'expiring':
        stocks = stocks.filter(
            expiry_date__lte=today + timedelta(days=30),
            expiry_date__gt=today
        )

    if search_q:
        stocks = stocks.filter(
            Q(medicine__name__icontains=search_q) |
            Q(medicine__generic_name__icontains=search_q) |
            Q(batch_number__icontains=search_q)
        )

    # Chart data for mini analytics
    stock_chart_labels = json.dumps(['In Stock', 'Low Stock', 'Out of Stock'])
    stock_chart_data   = json.dumps([in_stock, low_stock, out_of_stock])

    return render(request, 'pharmacy/stock.html', {
        'stocks': stocks,
        'stock_items': stocks,
        'total_items': total_items,
        'in_stock': in_stock,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'today': today,
        'status_filter': status_filter,
        'search_q': search_q,
        'stock_chart_labels': stock_chart_labels,
        'stock_chart_data': stock_chart_data,
    })


@login_required
def add_stock(request):
    """Add new stock entry."""
    if not request.user.is_pharmacist:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = MedicineStockForm(request.POST)
        if form.is_valid():
            stock = form.save()

            # Create StockTransaction record for incoming stock
            StockTransaction.objects.create(
                stock=stock,
                transaction_type='in',
                quantity=stock.quantity,
                reference=f'Initial stock - Batch {stock.batch_number}',
                notes=f'Received from {stock.supplier}' if stock.supplier else 'Stock entry',
                performed_by=request.user
            )

            messages.success(request, f'Stock added for {stock.medicine.name}.')
            return redirect('pharmacy:stock')
    else:
        form = MedicineStockForm()

    medicines = Medicine.objects.filter(is_active=True).order_by('name')
    return render(request, 'pharmacy/add_stock.html', {
        'form': form,
        'medicines': medicines,
    })


@login_required
def edit_stock(request, pk):
    """Edit stock entry."""
    if not request.user.is_pharmacist:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    stock = get_object_or_404(MedicineStock, pk=pk)
    old_quantity = stock.quantity

    if request.method == 'POST':
        form = StockEditForm(request.POST, instance=stock)
        if form.is_valid():
            updated_stock = form.save()

            # Log adjustment if quantity changed
            qty_diff = updated_stock.quantity - old_quantity
            if qty_diff != 0:
                StockTransaction.objects.create(
                    stock=updated_stock,
                    transaction_type='adjustment',
                    quantity=abs(qty_diff),
                    reference='Manual edit',
                    notes=f'Quantity {"increased" if qty_diff > 0 else "decreased"} by {abs(qty_diff)}',
                    performed_by=request.user
                )

            messages.success(request, f'Stock updated for {stock.medicine.name}.')
            return redirect('pharmacy:stock')
    else:
        form = StockEditForm(instance=stock)

    return render(request, 'pharmacy/edit_stock.html', {
        'form': form,
        'stock': stock,
    })


@login_required
def adjust_stock(request, pk):
    """Adjust stock quantity with reason."""
    if not request.user.is_pharmacist:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    stock = get_object_or_404(MedicineStock, pk=pk)

    if request.method == 'POST':
        adjustment_type = request.POST.get('adjustment_type', 'add')
        reason          = request.POST.get('reason', '').strip()
        try:
            quantity = int(request.POST.get('quantity', 0))
        except (ValueError, TypeError):
            quantity = 0

        if quantity <= 0:
            messages.error(request, 'Please enter a valid quantity greater than zero.')
        elif not reason:
            messages.error(request, 'Please provide a reason for the adjustment.')
        elif adjustment_type == 'remove' and quantity > stock.quantity:
            messages.error(request, f'Cannot remove {quantity} items — only {stock.quantity} available.')
        else:
            if adjustment_type == 'add':
                stock.quantity += quantity
                transaction_type = 'in'
            else:
                stock.quantity -= quantity
                transaction_type = 'out'

            stock.save()

            StockTransaction.objects.create(
                stock=stock,
                transaction_type=transaction_type,
                quantity=quantity,
                reference='Stock adjustment',
                notes=reason,
                performed_by=request.user
            )

            messages.success(request, f'Stock {"added to" if adjustment_type == "add" else "removed from"} {stock.medicine.name}: {quantity} units.')
            return redirect('pharmacy:stock')
    recent_transactions = StockTransaction.objects.filter(
        stock=stock
    ).order_by('-created_at')[:8]

    return render(request, 'pharmacy/adjust_stock.html', {
        'stock': stock,
        'recent_transactions': recent_transactions,
    })


@login_required
def stock_alerts(request):
    """View stock alerts (low stock and expiring)."""
    if not request.user.is_pharmacist:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    today = timezone.now().date()
    thirty_days = today + timedelta(days=30)

    # Out of stock
    out_of_stock = MedicineStock.objects.filter(
        quantity=0
    ).select_related('medicine')

    # Low stock (above 0 but below reorder level)
    low_stock = MedicineStock.objects.filter(
        quantity__gt=0,
        quantity__lte=F('reorder_level')
    ).select_related('medicine')

    # Expiring soon (within 30 days)
    expiring_soon = MedicineStock.objects.filter(
        expiry_date__lte=thirty_days,
        expiry_date__gt=today,
        quantity__gt=0
    ).select_related('medicine')

    # Expired
    expired = MedicineStock.objects.filter(
        expiry_date__lte=today
    ).select_related('medicine')

    return render(request, 'pharmacy/alerts.html', {
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'expiring_soon': expiring_soon,
        'expired': expired,
        'out_of_stock_count': out_of_stock.count(),
        'low_stock_count': low_stock.count(),
        'expiring_soon_count': expiring_soon.count(),
    })


@login_required
def stock_transactions(request, pk=None):
    """View stock transactions history."""
    if not request.user.is_pharmacist:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    if pk:
        stock = get_object_or_404(MedicineStock, pk=pk)
        transactions = StockTransaction.objects.filter(stock=stock).order_by('-created_at')
        return render(request, 'pharmacy/transactions.html', {
            'transactions': transactions,
            'stock': stock,
        })

    # All transactions
    transactions = StockTransaction.objects.select_related(
        'stock__medicine', 'performed_by'
    ).order_by('-created_at')[:100]

    return render(request, 'pharmacy/transactions.html', {
        'transactions': transactions,
    })


# API Endpoints for real-time stock checking

@login_required
def check_stock_api(request, medicine_id):
    """API endpoint for checking medicine stock availability."""
    try:
        medicine = Medicine.objects.get(pk=medicine_id)

        # Get total available stock (not expired)
        stock_data = MedicineStock.objects.filter(
            medicine=medicine,
            quantity__gt=0,
            expiry_date__gt=timezone.now().date()
        ).aggregate(
            total_qty=Sum('quantity'),
            batch_count=Count('id')
        )

        available = stock_data['total_qty'] or 0
        batches = stock_data['batch_count'] or 0

        # Determine status
        if available == 0:
            status = 'out_of_stock'
        elif available <= 10:
            status = 'low_stock'
        else:
            status = 'in_stock'

        return JsonResponse({
            'success': True,
            'medicine_id': medicine_id,
            'medicine_name': medicine.name,
            'available_stock': available,
            'batch_count': batches,
            'requires_prescription': medicine.requires_prescription,
            'status': status
        })
    except Medicine.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Medicine not found'
        }, status=404)


@login_required
def medicine_search_api(request):
    """API endpoint for searching medicines (used in prescription forms)."""
    query = request.GET.get('q', '')

    if len(query) < 2:
        return JsonResponse({'results': []})

    medicines = Medicine.objects.filter(
        Q(name__icontains=query) | Q(generic_name__icontains=query),
        is_active=True
    ).annotate(
        available_stock=Sum('stock_entries__quantity', filter=Q(
            stock_entries__quantity__gt=0,
            stock_entries__expiry_date__gt=timezone.now().date()
        ))
    )[:20]

    results = [{
        'id': m.id,
        'name': m.name,
        'generic_name': m.generic_name,
        'strength': m.strength,
        'dosage_form': m.get_dosage_form_display(),
        'available_stock': m.available_stock or 0,
        'requires_prescription': m.requires_prescription,
    } for m in medicines]

    return JsonResponse({'results': results})


@login_required
def stock_forecast(request):
    """ML-powered stock demand forecast for pharmacy."""
    if not (request.user.is_pharmacist or request.user.is_admin):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    try:
        from apps.ai_services.services import get_ml_stock_forecast
        forecasts = get_ml_stock_forecast()
    except Exception:
        forecasts = []

    # Top 10 by predicted demand for chart
    chart_data = sorted(forecasts, key=lambda f: f.get('predicted_demand', 0), reverse=True)[:10]

    return render(request, 'pharmacy/forecast.html', {
        'forecasts': forecasts,
        'chart_labels': json.dumps([f['medicine_name'] for f in chart_data]),
        'chart_demand': json.dumps([round(f.get('predicted_demand', 0), 1) for f in chart_data]),
        'chart_stock':  json.dumps([f.get('current_stock', 0) for f in chart_data]),
    })


@login_required
def pharmacy_analytics(request):
    """Visual analytics dashboard for pharmacy."""
    if not (request.user.is_pharmacist or request.user.is_admin):
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')

    today = timezone.now().date()
    month_ago = today - timedelta(days=30)
    ninety_ago = today - timedelta(days=90)

    # Top 15 most dispensed medicines (by stock-out transactions)
    top_dispensed = StockTransaction.objects.filter(
        transaction_type='out', created_at__date__gte=month_ago
    ).values('stock__medicine__name').annotate(
        total=Sum('quantity')
    ).order_by('-total')[:15]

    # Daily dispensing volume (last 30 days)
    daily_dispense = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        qty = StockTransaction.objects.filter(
            transaction_type='out', created_at__date=day
        ).aggregate(total=Sum('quantity'))['total'] or 0
        daily_dispense.append({'date': day.strftime('%d %b'), 'qty': qty})

    # Stock health counts
    in_stock   = MedicineStock.objects.filter(quantity__gt=F('reorder_level')).count()
    low_stock  = MedicineStock.objects.filter(quantity__gt=0, quantity__lte=F('reorder_level')).count()
    out_stock  = MedicineStock.objects.filter(quantity=0).count()

    # Category-wise dispensing
    cat_dispense = StockTransaction.objects.filter(
        transaction_type='out', created_at__date__gte=month_ago
    ).values('stock__medicine__category__name').annotate(
        total=Sum('quantity')
    ).order_by('-total')[:8]

    # Expiry countdown buckets
    exp_30 = MedicineStock.objects.filter(expiry_date__gt=today, expiry_date__lte=today + timedelta(days=30), quantity__gt=0).count()
    exp_60 = MedicineStock.objects.filter(expiry_date__gt=today + timedelta(days=30), expiry_date__lte=today + timedelta(days=60), quantity__gt=0).count()
    exp_90 = MedicineStock.objects.filter(expiry_date__gt=today + timedelta(days=60), expiry_date__lte=today + timedelta(days=90), quantity__gt=0).count()

    # AI demand forecasts for insight panel
    try:
        from apps.ai_services.services import get_ml_stock_forecast
        forecasts = get_ml_stock_forecast()
    except Exception:
        forecasts = []

    critical_meds = [f for f in forecasts if f.get('risk_level') in ('critical', 'high')][:5]

    ai_insights = []
    total_low_out = low_stock + out_stock
    if total_low_out > 0:
        ai_insights.append({
            'type': 'warning',
            'text': f'{total_low_out} medicine batch{"es" if total_low_out != 1 else ""} are at or below reorder level — consider restocking.',
        })
    if exp_30 > 0:
        ai_insights.append({
            'type': 'danger',
            'text': f'{exp_30} batch{"es" if exp_30 != 1 else ""} expire within 30 days. Review and dispose of expired stock promptly.',
        })
    for f in critical_meds:
        ai_insights.append({
            'type': 'critical' if f.get('risk_level') == 'critical' else 'high',
            'text': f'{f["medicine_name"]}: predicted demand {round(f.get("predicted_demand", 0))} units in 30 days — only {f.get("current_stock", 0)} in stock.',
        })
    if not ai_insights:
        ai_insights.append({'type': 'ok', 'text': 'All stock levels are healthy. No immediate action required.'})

    return render(request, 'pharmacy/analytics.html', {
        'top_dispensed': list(top_dispensed),
        'top_labels':   json.dumps([d['stock__medicine__name'] or 'Unknown' for d in top_dispensed]),
        'top_values':   json.dumps([d['total'] for d in top_dispensed]),
        'daily_labels': json.dumps([d['date'] for d in daily_dispense]),
        'daily_values': json.dumps([d['qty'] for d in daily_dispense]),
        'in_stock':  in_stock,
        'low_stock': low_stock,
        'out_stock': out_stock,
        'cat_labels': json.dumps([c['stock__medicine__category__name'] or 'Unknown' for c in cat_dispense]),
        'cat_values': json.dumps([c['total'] for c in cat_dispense]),
        'exp_30': exp_30, 'exp_60': exp_60, 'exp_90': exp_90,
        'today': today,
        'ai_insights': ai_insights,
        'critical_meds': critical_meds,
    })
