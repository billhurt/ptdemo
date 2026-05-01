from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'trainer', 'session_date', 'session_time', 'status', 'created_at')
    list_filter = ('status', 'trainer', 'session_date')
    search_fields = ('name', 'email')
    ordering = ('session_date', 'session_time')
    readonly_fields = ('stripe_session_id', 'created_at')