from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):

    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'user_type', 'is_verified', 'is_staff'
    )

    list_filter = ('user_type', 'is_verified', 'is_staff', 'is_superuser')

    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': (
                'user_type',
                'phone_number',
                'profile_picture',
                'is_verified'
            )
        }),
    )

    # 🔥 REQUIRED if you added custom fields or UUID primary key
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'email',
                'password1',
                'password2',
                'user_type',
                'phone_number',
                'profile_picture',
                'is_verified',
            ),
        }),
    )

    search_fields = ('username', 'email')
    ordering = ('email',)
