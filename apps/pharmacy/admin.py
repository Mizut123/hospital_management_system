from django.contrib import admin
from .models import Medicine, MedicineCategory, MedicineStock, StockTransaction


@admin.register(MedicineCategory)
class MedicineCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'generic_name', 'category', 'dosage_form', 'strength', 'is_active')
    list_filter = ('category', 'dosage_form', 'is_active', 'requires_prescription')
    search_fields = ('name', 'generic_name', 'manufacturer')


@admin.register(MedicineStock)
class MedicineStockAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'batch_number', 'quantity', 'expiry_date', 'is_low_stock')
    list_filter = ('expiry_date', 'received_date')
    search_fields = ('medicine__name', 'batch_number')


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('stock', 'transaction_type', 'quantity', 'performed_by', 'created_at')
    list_filter = ('transaction_type', 'created_at')
