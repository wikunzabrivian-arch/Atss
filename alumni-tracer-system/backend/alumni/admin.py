from django.contrib import admin
from .models import AlumniProfile, Event, Notice

@admin.register(AlumniProfile)
class AlumniProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id', 'program', 'year_graduated', 'current_employer')
    list_filter = ('program', 'year_graduated')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'student_id')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'location', 'created_by', 'created_at')
    list_filter = ('date', 'created_at')
    search_fields = ('title', 'description', 'location')

@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'content')

