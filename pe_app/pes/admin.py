from django.contrib import admin
from django.contrib.auth.admin import UserAdmin  # <-- Sử dụng UserAdmin thay vì ModelAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from .models import UserProfile, Class, Enrollment, Membership, Trainer, Schedule


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = UserProfile
        # Loại bỏ fields không cần thiết
        exclude = ('user_permissions', 'groups', 'date_joined')


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = UserProfile
        fields = ('username', 'email')  # Các trường bắt buộc khi tạo user


class UserProfileAdmin(UserAdmin):  # <-- Kế thừa từ UserAdmin
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    # Cấu hình fields hiển thị khi THÊM user
    add_fieldsets = (
        ('Đăng ký', {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'email', 'username', 'password1', 'password2'),
        }),
    )

    # Cấu hình fields hiển thị khi CHỈNH SỬA user
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Thông tin cá nhân', {'fields': ('first_name', 'last_name', 'email')}),
        ('Thông tin thêm', {
            'fields': (
                'avatar',
                'role',
                'phone',
                'address',
                'is_active',
                'is_staff',
                'is_superuser'
            )
        }),
        ('Lịch sử', {'fields': ('last_login',)}),
    )

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'role')
    search_fields = ('username', 'email')
    ordering = ('-date_joined',)


# Đăng ký lại model với cấu hình mới
admin.site.register(UserProfile, UserProfileAdmin)

# Đăng ký các model khác
admin.site.register(Class)
admin.site.register(Enrollment)
admin.site.register(Membership)
admin.site.register(Trainer)
admin.site.register(Schedule)
