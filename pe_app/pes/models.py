from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class UserProfile(AbstractUser):
    AVATAR_CHOICES = (
        ('default', 'Mặc định'),
        ('custom', 'Tùy chỉnh'),
    )
    ROLES = (
        ('admin', 'Quản trị viên'),
        ('trainer', 'Huấn luyện viên'),
        ('staff', 'Nhân viên lễ tân'),
        ('member', 'Hội viên'),
    )

    avatar = models.ImageField(upload_to='avatars/', default='default.png')
    avatar_type = models.CharField(max_length=10, choices=AVATAR_CHOICES, default='default')
    role = models.CharField(max_length=10, choices=ROLES, default='member')
    phone = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"

    def save(self, *args, **kwargs):
        # Lấy trạng thái role trước khi lưu (nếu user đã tồn tại)
        old_role = None
        if self.pk:
            old_role = UserProfile.objects.get(pk=self.pk).role

        # Lưu user trước
        super().save(*args, **kwargs)

        # Logic xử lý Trainer
        if self.role == 'trainer':
            # Tạo Trainer nếu chưa tồn tại
            if not hasattr(self, 'trainer'):
                Trainer.objects.create(user=self)
        else:
            # Xóa Trainer nếu tồn tại
            if hasattr(self, 'trainer'):
                self.trainer.delete()


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


class Class(models.Model):
    CLASS_TYPES = (
        ('yoga', 'Yoga'),
        ('gym', 'Gym'),
        ('swim', 'Bơi lội'),
        ('dance', 'Dance'),
    )

    name = models.CharField(max_length=100)
    class_type = models.CharField(max_length=10, choices=CLASS_TYPES)
    schedule = models.JSONField()  # Stores days and times
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True)
    capacity = models.PositiveIntegerField()
    description = models.TextField()

    def __str__(self):
        return f"{self.get_class_type_display()} - {self.name}"


class Enrollment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Chờ xử lý'),
        ('active', 'Đang tham gia'),
        ('completed', 'Hoàn thành'),
    )

    member = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    class_enrolled = models.ForeignKey(Class, on_delete=models.CASCADE)
    enrollment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    class Meta:
        unique_together = ('member', 'class_enrolled')

    def __str__(self):
        return f"{self.member.username} - {self.class_enrolled.name}"


class Payment(models.Model):
    PAYMENT_METHODS = (
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
    membership = models.ForeignKey(Membership, on_delete=models.SET_NULL, null=True, blank=True)

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


class Schedule(models.Model):
    trainer = models.ForeignKey(Trainer, on_delete=models.CASCADE)
    member = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    schedule_date = models.DateTimeField()
    notes = models.TextField()

    class Meta:
        ordering = ['schedule_date']

    def __str__(self):
        return f"{self.trainer} - {self.member} - {self.schedule_date}"
