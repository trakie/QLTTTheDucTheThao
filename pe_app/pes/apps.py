from django.apps import AppConfig

class PesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pes'  # Đảm bảo tên app đúng

    def ready(self):
        # Kích hoạt signals khi app được load
        from . import signals