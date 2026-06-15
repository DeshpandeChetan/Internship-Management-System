# from django.apps import AppConfig


# class AppsConfig(AppConfig):
#     name = 'apps'


# apps.py
from django.apps import AppConfig


class AppsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps'
    
    def ready(self):
        # Import signals
        import apps.signals