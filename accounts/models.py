
# Create your models here.


# accounts/models.py - نماذج الحسابات

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class UserProfile(models.Model):
    """الملف الشخصي للمستخدم"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_('المستخدم'))
    avatar = models.ImageField(_('الصورة الشخصية'), upload_to='avatars/', blank=True)
    bio = models.TextField(_('نبذة شخصية'), max_length=500, blank=True)
    website = models.URLField(_('الموقع الشخصي'), blank=True)
    location = models.CharField(_('الموقع'), max_length=100, blank=True)
    
    # إعدادات الخصوصية
    show_email = models.BooleanField(_('إظهار البريد الإلكتروني'), default=False)
    allow_messages = models.BooleanField(_('السماح بالرسائل'), default=True)
    
    # إعدادات الإشعارات
    email_notifications = models.BooleanField(_('إشعارات البريد'), default=True)
    newsletter_subscription = models.BooleanField(_('الاشتراك في النشرة'), default=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('الملف الشخصي')
        verbose_name_plural = _('الملفات الشخصية')
    
    def __str__(self):
        return f'{self.user.get_full_name()} - {self.user.username}'
