from django.db import models
from django.contrib.auth.models import AbstractUser
from django.templatetags.static import static
from django.utils import timezone
from django.db.models import Q
from cloudinary.models import CloudinaryField
import cloudinary
from cloudinary.exceptions import Error as CloudinaryError
import logging


logger = logging.getLogger(__name__)


class UserProfile(AbstractUser):
    ROLES = (
        ('admin', 'Quản trị viên'),
        ('trainer', 'Huấn luyện viên'),
        ('staff', 'Nhân viên lễ tân'),
        ('member', 'Hội viên'),
    )

    avatar = CloudinaryField(
        'avatar',  # Tên resource trên Cloudinary
        folder="avatars",  # Thư mục lưu trữ
        default='image/upload/v1748023865/default_uryokl.png'  # Public ID của ảnh mặc định
    )
    role = models.CharField(max_length=10, choices=ROLES, default='member')
    phone = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"

    def save(self, *args, **kwargs):
        # Xử lý xóa ảnh cũ
        old_avatar_public_id = None
        old_role = None

        if self.pk:
            old_user = UserProfile.objects.get(pk=self.pk)
            old_avatar_public_id = old_user.avatar.public_id if old_user.avatar else None
            old_role = old_user.role

        # Lấy trạng thái role trước khi lưu (nếu user đã tồn tại)
        old_role = None
        if self.pk:
            old_user = UserProfile.objects.get(pk=self.pk)
            old_role = old_user.role

        # Lưu user trước
        super().save(*args, **kwargs)

        # Xóa ảnh cũ nếu khác ảnh mới và không phải ảnh mặc định
        if old_avatar_public_id and old_avatar_public_id != self.avatar.public_id:
            if old_avatar_public_id != 'avatars/default':
                try:
                    cloudinary.uploader.destroy(old_avatar_public_id)
                except CloudinaryError as e:
                    logger.error(f"Lỗi xóa ảnh Cloudinary: {e}")

        # Logic xử lý Trainer
        if self.role == 'trainer':
            # Tạo Trainer nếu chưa tồn tại
            if not Trainer.objects.filter(user=self).exists():
                Trainer.objects.create(user=self)
        else:
            # Xóa Trainer nếu tồn tại (sử dụng truy vấn trực tiếp)
            Trainer.objects.filter(user=self).delete()  # Sửa ở đây


class Trainer(models.Model):
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE, primary_key=True)
    specialization = models.CharField(max_length=100, blank=True, default='')
    experience = models.TextField(blank=True, default='')
    certification = models.FileField(upload_to='certifications/', null=True, blank=True)

    def __str__(self):
        return self.user.get_full_name()


class Membership(models.Model):
    member = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    fee = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.member.username} - {self.end_date}"


class Schedule(models.Model):
    DAY_CHOICES = [
        (0, 'Thứ hai'),
        (1, 'Thứ ba'),
        (2, 'Thứ tư'),
        (3, 'Thứ năm'),
        (4, 'Thứ sáu'),
        (5, 'Thứ bảy'),
        (6, 'Chủ nhật'),
    ]

    TIME_BLOCK_CHOICES = [
        ('1_morning', 'Sáng'),
        ('2_afternoon', 'Trưa'),
        ('3_evening', 'Chiều'),
    ]

    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    time_block = models.CharField(max_length=12, choices=TIME_BLOCK_CHOICES)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.get_day_of_week_display()} - {self.get_time_block_display()}"

    @property
    def display_schedule(self):
        return f"{self.get_day_of_week_display()} - {self.get_time_block_display()}"


class Class(models.Model):
    CLASS_TYPES = (
        ('yoga', 'Yoga'),
        ('gym', 'Gym'),
        ('swim', 'Bơi lội'),
        ('dance', 'Dance'),
    )

    name = models.CharField(max_length=100)
    price = models.FloatField(default=0)
    class_type = models.CharField(max_length=10, choices=CLASS_TYPES)
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True, related_name='classes')
    description = models.TextField()

    def __str__(self):
        return f"{self.get_class_type_display()} - {self.name}"

    @property
    def image_url(self):
        # Map class_type to the image file name
        images = {
            'yoga': 'pes/images/yoga.png',
            'gym': 'pes/images/gym.png',
            'swim': 'pes/images/swim.png',
            'dance': 'pes/images/dance.png',
        }
        image_path = images.get(self.class_type, 'pes/images/default_class.png')
        return static(image_path)


class ClassSchedule(models.Model):
    lop = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='schedules')
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.lop.name} - {self.schedule}"


class Enrollment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Chờ xử lý'),
        ('active', 'Đang tham gia'),
        ('completed', 'Hoàn thành'),
    )

    member = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    class_enrolled = models.ForeignKey(Class, on_delete=models.CASCADE)
    schedule_selected = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    enrollment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    payment_status = models.BooleanField(default=False)
    completion_date = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['member', 'class_enrolled'],
                condition=~Q(status='completed'),
                name='unique_active_enrollment'
            )
        ]

    def __str__(self):
        return f"{self.member.username} - {self.class_enrolled.name}"


class Payment(models.Model):
    PAYMENT_METHODS = (
        ('cash', 'Tiền mặt'),
        ('momo', 'Momo'),
        ('vnpay', 'VNPAY'),
        ('stripe', 'Stripe'),
    )

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    transaction_id = models.CharField(max_length=100)
    enrollment = models.ForeignKey(Enrollment, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.payment_method}"


class Notification(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.content[:50]}"


class Post(models.Model):
    CATEGORIES = (
        ('tips', 'Mẹo tập luyện'),
        ('nutrition', 'Dinh dưỡng'),
        ('event', 'Sự kiện'),
    )

    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    category = models.CharField(max_length=10, choices=CATEGORIES)
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.get_category_display()}"


class Progress(models.Model):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE)
    progress_date = models.DateField()
    notes = models.TextField()
    achievement = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.enrollment} - {self.progress_date}"
