from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserProfile, Trainer, Membership
from django.utils import timezone

@receiver(post_save, sender=UserProfile)
def handle_role_changes(sender, instance, **kwargs):
    # Xử lý Trainer
    if instance.role == 'trainer':
        if not hasattr(instance, 'trainer'):
            Trainer.objects.create(user=instance)
    else:
        if hasattr(instance, 'trainer'):
            instance.trainer.delete()

    # Xử lý Membership
    if instance.role == 'member':
        if not hasattr(instance, 'membership'):
            # Tạo Membership với giá trị mặc định (tuỳ chỉnh theo yêu cầu)
            Membership.objects.create(
                member=instance,
                end_date=timezone.now() + timezone.timedelta(days=30),  # Ví dụ: 30 ngày sau
                fee=0  # Giá trị mặc định
            )
    else:
        if hasattr(instance, 'membership'):
            instance.membership.delete()