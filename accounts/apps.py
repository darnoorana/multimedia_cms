

# accounts/apps.py

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = _('الحسابات')
    
    def ready(self):
        from django.db.models.signals import post_save
        from django.contrib.auth.models import User
        from .models import UserProfile
        
        def create_user_profile(sender, instance, created, **kwargs):
            if created:
                UserProfile.objects.create(user=instance)
        
        post_save.connect(create_user_profile, sender=User)
