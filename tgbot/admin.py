from django.contrib import admin
from .models import *


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["user_id", "name", "status", "last_active"]
    list_filter = ["status", "is_active", "last_active", "date_registered"]
    search_fields = ["user_id", "name"]
