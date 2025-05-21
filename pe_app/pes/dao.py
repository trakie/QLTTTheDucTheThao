from .models import Class

def get_all_classes():
    return Class.objects.select_related('schedule', 'trainer').all()
