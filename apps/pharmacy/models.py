"""
Pharmacy Models - Medicine database and stock management.
"""
from django.db import models
from django.conf import settings


class MedicineCategory(models.Model):
    """Categories for medicines."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Medicine Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Medicine(models.Model):
    """Medicine database."""

    DOSAGE_FORMS = [
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('syrup', 'Syrup'),
        ('injection', 'Injection'),
        ('cream', 'Cream/Ointment'),
        ('drops', 'Drops'),
        ('inhaler', 'Inhaler'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200, blank=True)
    category = models.ForeignKey(MedicineCategory, on_delete=models.SET_NULL, null=True, blank=True)
    dosage_form = models.CharField(max_length=20, choices=DOSAGE_FORMS)
    strength = models.CharField(max_length=50, help_text='e.g., 500mg, 10ml')
    manufacturer = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    contraindications = models.TextField(blank=True, help_text='Conditions where medicine should not be used')
    side_effects = models.TextField(blank=True)
    storage_instructions = models.CharField(max_length=200, blank=True)
    requires_prescription = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.strength})"

    @property
    def total_stock(self):
        return self.stock_entries.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0


class MedicineStock(models.Model):
    """Stock entries for medicines."""

    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='stock_entries')
    batch_number = models.CharField(max_length=50)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    expiry_date = models.DateField()
    received_date = models.DateField()
    supplier = models.CharField(max_length=200, blank=True)
    reorder_level = models.IntegerField(default=10, help_text='Minimum quantity before reorder alert')
    predicted_demand = models.IntegerField(null=True, blank=True, help_text='AI-predicted demand')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['expiry_date']

    def __str__(self):
        return f"{self.medicine.name} - Batch {self.batch_number}"

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level

    @property
    def is_expired(self):
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()


class StockTransaction(models.Model):
    """Track stock movements."""

    TRANSACTION_TYPES = [
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('adjustment', 'Adjustment'),
        ('expired', 'Expired'),
    ]

    stock = models.ForeignKey(MedicineStock, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    reference = models.CharField(max_length=100, blank=True, help_text='Prescription ID or reference')
    notes = models.TextField(blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.stock.medicine.name} ({self.quantity})"
