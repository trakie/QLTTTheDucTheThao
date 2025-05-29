from .models import Class, ClassSchedule, Trainer, Payment
from django.db.models import Prefetch


def get_all_classes():
    return Class.objects.select_related('trainer').prefetch_related(
        Prefetch(
            'schedules',
            queryset=ClassSchedule.objects.select_related('schedule')
        )
    )


def get_all_trainers():
    return Trainer.objects.select_related('user').prefetch_related('classes').all()


def get_all_payment():
    return Payment.objects.select_related('user').prefetch_related('enrollment').all()