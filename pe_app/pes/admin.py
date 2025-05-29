import datetime

from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin  # <-- Sử dụng UserAdmin thay vì ModelAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone
from operator import itemgetter
from collections import defaultdict

from .models import (UserProfile, Class, Enrollment, Membership, Trainer,
                     Schedule, ClassSchedule, Payment, Post)


class CustomAdminSite(AdminSite):
    # Đặt tên site (xuất hiện trong tiêu đề)
    site_header = "Quản trị hệ thống"
    site_title = "Trang quản trị"
    index_title = "Bảng điều khiển"

    def get_urls(self):
        urls = super().get_urls()
        # Thêm URL mới vào đầu danh sách
        custom_urls = [
            path(
                'statistics/',
                self.admin_view(self.statistics_view),
                name='statistics'
            ),
        ]
        return custom_urls + urls

    def statistics_view(self, request):
        period = request.GET.get('period', 'month')
        now = timezone.localtime(timezone.now())

        # Tính toán khoảng thời gian dựa trên lựa chọn
        if period == 'week':
            start_date = now - datetime.timedelta(days=now.weekday())
        elif period == 'year':
            start_date = datetime.datetime(now.year, 1, 1, tzinfo=now.tzinfo)
        else:  # month
            start_date = datetime.datetime(now.year, now.month, 1, tzinfo=now.tzinfo)

        # 1. Thống kê doanh thu từng lớp
        payments = Payment.objects.filter(
            payment_date__gte=start_date,
            enrollment__isnull=False,
            enrollment__payment_status=True
        ).select_related('enrollment__class_enrolled')

        # Tạo dictionary để nhóm doanh thu theo lớp
        revenue_by_class = defaultdict(float)
        for payment in payments:
            class_name = payment.enrollment.class_enrolled.name
            revenue_by_class[class_name] += float(payment.amount)

        # Chuyển thành danh sách và sắp xếp
        revenue_list = []
        total_revenue = sum(revenue_by_class.values()) or 1  # Tránh chia cho 0
        for idx, (class_name, revenue) in enumerate(
                sorted(revenue_by_class.items(), key=itemgetter(1), reverse=True), start=1
        ):
            percent = (revenue / total_revenue) * 100
            revenue_list.append({
                'stt': idx,
                'class_name': class_name,
                'revenue': revenue,
                'percent': round(percent, 2)
            })

        # 2. Thống kê số lượng học viên đăng ký
        enrollments = Enrollment.objects.filter(
            enrollment_date__gte=start_date,
            payment_status=True
        ).select_related('class_enrolled')

        # Tạo dictionary để nhóm số lượng học viên theo lớp
        enrollments_by_class = defaultdict(int)
        for enrollment in enrollments:
            class_name = enrollment.class_enrolled.name
            enrollments_by_class[class_name] += 1

        # Chuyển thành danh sách và sắp xếp
        enrollment_list = []
        total_enrollments = sum(enrollments_by_class.values()) or 1
        for idx, (class_name, count) in enumerate(
                sorted(enrollments_by_class.items(), key=itemgetter(1), reverse=True), start=1
        ):
            percent = (count / total_enrollments) * 100
            enrollment_list.append({
                'stt': idx,
                'class_name': class_name,
                'enrollments': count,
                'percent': round(percent, 2)
            })

        # Tính tổng doanh thu
        total_revenue = sum(item['revenue'] for item in revenue_list) if revenue_list else 0

        # Tính tổng số học viên
        total_enrollments = sum(item['enrollments'] for item in enrollment_list) if enrollment_list else 0

        context = {
            'user_count': Membership.objects.count(),
            'class_count': Class.objects.count(),
            'total_revenue': total_revenue,
            'total_enrollments': total_enrollments,
            'revenue_list': revenue_list,
            'enrollment_list': enrollment_list,
            'period': period,
            'period_options': [
                {'value': 'week', 'label': 'Tuần'},
                {'value': 'month', 'label': 'Tháng'},
                {'value': 'year', 'label': 'Năm'},
            ],
            **self.each_context(request),
        }
        return TemplateResponse(request, 'pes/admin/statistics.html', context)

    def get_app_list(self, request, app_label=None):
        """
        Trả về danh sách ứng dụng với mục Thống kê được thêm vào
        """
        app_list = super().get_app_list(request, app_label)

        # Chỉ thêm mục Thống kê khi ở trang chủ admin (không trong app cụ thể)
        if app_label is None:
            # Tạo mục Thống kê
            stats_app = {
                'name': '📊 Thống kê',
                'app_label': 'statistics',
                'app_url': '/admin/statistics/',
                'has_module_perms': request.user.is_staff,
                'models': [
                    {
                        'name': 'Thống kê',
                        'object_name': 'statistics',
                        'admin_url': '/admin/statistics/',
                        'view_only': True,
                    }
                ],
            }

            # Chèn vào đầu danh sách
            app_list.insert(0, stats_app)

        return app_list


# Tạo instance admin site tùy chỉnh
custom_admin_site = CustomAdminSite(name='myadmin')

# Thay thế admin site mặc định
admin.site = custom_admin_site


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
custom_admin_site.register(UserProfile, UserProfileAdmin)

# Đăng ký các model khác
custom_admin_site.register(Class)
custom_admin_site.register(Enrollment)
custom_admin_site.register(Membership)
custom_admin_site.register(Trainer)
custom_admin_site.register(Schedule)
custom_admin_site.register(ClassSchedule)
custom_admin_site.register(Payment)
custom_admin_site.register(Post)
