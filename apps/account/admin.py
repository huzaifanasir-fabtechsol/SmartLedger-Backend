from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.account.models import User, LetterheadRecord


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ['id', 'email', 'role', 'company_website']


@admin.register(LetterheadRecord)
class LetterheadRecordAdmin(admin.ModelAdmin):
    list_display = ['original_name', 'user', 'size', 'stored_size', 'is_compressed', 'created_at']
    search_fields = ['original_name', 'description']
