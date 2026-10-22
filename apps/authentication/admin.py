from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    fk_name = 'user'
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ['role', 'department', 'phone_number', 'is_active', 'is_approved']
    readonly_fields = ['is_approved']

class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'profile__role', 'profile__is_approved']
    search_fields = ['username', 'email', 'first_name', 'last_name']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            UserProfile.objects.update_or_create(
                user=obj,
                defaults={'role': 'admin' if obj.is_superuser else 'unassigned',
                          'is_active': obj.is_active, 'is_approved': True},
            )
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(profile__deleted_at__isnull=True)

    def has_delete_permission(self, request, obj=None):
        if obj and (obj.pk == request.user.pk or obj.is_superuser):
            return False
        return super().has_delete_permission(request, obj)

    def delete_model(self, request, obj):
        if not self.has_delete_permission(request, obj):
            return
        profile, _ = UserProfile.all_objects.get_or_create(user=obj)
        profile.delete(deleted_by=request.user)

    def delete_queryset(self, request, queryset):
        for user in queryset:
            self.delete_model(request, user)

# Re-register User admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'department', 'phone_number', 'is_active', 'is_approved']
    list_filter = ['role', 'department', 'is_active', 'is_approved']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    list_editable = ['role', 'is_active', 'is_approved']
    fields = ['user', 'role', 'department', 'phone_number', 'is_active', 'is_approved']
    readonly_fields = ['user']

    def has_delete_permission(self, request, obj=None):
        if obj and (obj.user_id == request.user.pk or obj.user.is_superuser):
            return False
        return super().has_delete_permission(request, obj)

    def delete_model(self, request, obj):
        if self.has_delete_permission(request, obj):
            obj.delete(deleted_by=request.user)

    def delete_queryset(self, request, queryset):
        for profile in queryset:
            self.delete_model(request, profile)
