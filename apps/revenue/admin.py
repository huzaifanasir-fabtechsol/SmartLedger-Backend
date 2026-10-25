from django.contrib import admin
from apps.revenue.models import CarCategory, Car, Order, OrderItem, Customer, Saler, CompanyAccount, Auction, Transaction

@admin.register(CarCategory)
class CarCategoryAdmin(admin.ModelAdmin):
    list_display = ['company', 'model', 'user', 'created_at']
    search_fields = ['company']

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ['chassis_number', 'year', 'category', 'user', 'created_at']
    search_fields = ['chassis_number']
    list_filter = ['year', 'category']

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'order_number', 'transaction_type', 'customer_name', 'total_amount', 'transaction_date', 'user', 'created_at']
    search_fields = ['order_number', 'customer_name']
    list_filter = ['transaction_type', 'transaction_date']
    inlines = [OrderItemInline]

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'bank_name', 'user', 'created_at']
    search_fields = ['name', 'email', 'phone']

@admin.register(Saler)
class SalerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'bank_name', 'user', 'created_at']
    search_fields = ['name', 'email', 'phone']

@admin.register(CompanyAccount)
class CompanyAccountAdmin(admin.ModelAdmin):
    list_display = ['bank_name', 'account_number', 'account_holder', 'user', 'created_at']
    search_fields = ['bank_name', 'account_number', 'account_holder']

@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ['name', 'auction_type', 'user', 'created_at']
    search_fields = ['name', 'auction_type', 'description']
    list_filter = ['auction_type']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'company_account', 'date', 'description', 'withdraw', 'deposit', 'balance', 'user', 'created_at']
    search_fields = ['description', 'notes', 'company_account']
    list_filter = ['date', 'user', 'company_account']
