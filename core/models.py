
# Create your models here.
# core/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import URLValidator
from django.contrib.auth.models import User

class SiteSettings(models.Model):
    """إعدادات الموقع العامة"""
    site_name = models.CharField(_('اسم الموقع'), max_length=200, default='منصة المحتوى المتعدد الوسائط')
    site_description = models.TextField(_('وصف الموقع'), blank=True)
    site_logo = models.ImageField(_('شعار الموقع'), upload_to='site/', blank=True)
    site_favicon = models.ImageField(_('أيقونة الموقع'), upload_to='site/', blank=True)
    
    # معلومات الاتصال
    contact_email = models.EmailField(_('بريد الاتصال'), blank=True)
    contact_phone = models.CharField(_('هاتف الاتصال'), max_length=20, blank=True)
    contact_whatsapp = models.CharField(_('واتساب'), max_length=20, default='0097335370499')
    
    # إعدادات SEO
    meta_title = models.CharField(_('عنوان Meta'), max_length=60, blank=True)
    meta_description = models.TextField(_('وصف Meta'), max_length=160, blank=True)
    meta_keywords = models.TextField(_('كلمات مفتاحية'), blank=True)
    
    # إعدادات وسائل التواصل الاجتماعي
    facebook_url = models.URLField(_('فيسبوك'), blank=True, default='https://facebook.com/alibasheerahmed2')
    twitter_url = models.URLField(_('تويتر'), blank=True, default='https://twitter.com/alibasheer09')
    youtube_url = models.URLField(_('يوتيوب'), blank=True, default='https://www.youtube.com/@alibasheer')
    instagram_url = models.URLField(_('انستجرام'), blank=True, default='https://instagram.com/alibasheerahmed2')
    telegram_url = models.URLField(_('تيليجرام'), blank=True, default='https://t.me/alibasheerahmed')
    soundcloud_url = models.URLField(_('ساوندكلاود'), blank=True, default='https://soundcloud.com/alibasheerahmed2')
    tiktok_url = models.URLField(_('تيك توك'), blank=True, default='https://tiktok.com/@alibasheerahmed2')
    
    # إعدادات API
    youtube_api_key = models.CharField(_('مفتاح YouTube API'), max_length=100, blank=True)
    soundcloud_client_id = models.CharField(_('معرف SoundCloud'), max_length=100, blank=True)
    telegram_bot_token = models.CharField(_('رمز Telegram Bot'), max_length=100, blank=True)
    
    # إعدادات النشرة الإخبارية
    newsletter_enabled = models.BooleanField(_('تفعيل النشرة الإخبارية'), default=True)
    newsletter_from_email = models.EmailField(_('بريد النشرة'), blank=True)
    
    # إعدادات RSS
    rss_enabled = models.BooleanField(_('تفعيل RSS'), default=True)
    rss_title = models.CharField(_('عنوان RSS'), max_length=100, blank=True)
    rss_description = models.TextField(_('وصف RSS'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('إعدادات الموقع')
        verbose_name_plural = _('إعدادات الموقع')
    
    def __str__(self):
        return self.site_name
    
    @classmethod
    def get_settings(cls):
        """الحصول على إعدادات الموقع (إنشاء واحدة جديدة إذا لم تكن موجودة)"""
        settings, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'site_name': 'منصة المحتوى المتعدد الوسائط - د. علي بشير أحمد',
                'site_description': 'منصة شاملة للمحتوى التعليمي والترفيهي متعدد الوسائط',
                'meta_title': 'د. علي بشير أحمد - منصة المحتوى المتعدد الوسائط',
                'meta_description': 'منصة تعليمية وترفيهية شاملة تحتوي على فيديوهات ومقاطع صوتية ومقالات متنوعة',
            }
        )
        return settings


class Category(models.Model):
    """تصنيفات المحتوى"""
    name = models.CharField(_('الاسم'), max_length=100)
    slug = models.SlugField(_('الرابط المختصر'), unique=True)
    description = models.TextField(_('الوصف'), blank=True)
    image = models.ImageField(_('الصورة'), upload_to='categories/', blank=True)
    
    # إعدادات SEO للتصنيف
    meta_title = models.CharField(_('عنوان Meta'), max_length=60, blank=True)
    meta_description = models.TextField(_('وصف Meta'), max_length=160, blank=True)
    
    # الترتيب والحالة
    order = models.PositiveIntegerField(_('الترتيب'), default=0)
    is_active = models.BooleanField(_('مفعل'), default=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('تصنيف')
        verbose_name_plural = _('التصنيفات')
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class Newsletter(models.Model):
    """النشرة الإخبارية"""
    email = models.EmailField(_('البريد الإلكتروني'), unique=True)
    is_active = models.BooleanField(_('مفعل'), default=True)
    subscribed_at = models.DateTimeField(_('تاريخ الاشتراك'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('مشترك النشرة')
        verbose_name_plural = _('مشتركو النشرة')
        ordering = ['-subscribed_at']
    
    def __str__(self):
        return self.email


class ContactMessage(models.Model):
    """رسائل التواصل"""
    name = models.CharField(_('الاسم'), max_length=100)
    email = models.EmailField(_('البريد الإلكتروني'))
    subject = models.CharField(_('الموضوع'), max_length=200)
    message = models.TextField(_('الرسالة'))
    is_read = models.BooleanField(_('مقروءة'), default=False)
    is_replied = models.BooleanField(_('تم الرد'), default=False)
    created_at = models.DateTimeField(_('تاريخ الإرسال'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('رسالة تواصل')
        verbose_name_plural = _('رسائل التواصل')
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.name} - {self.subject}'


class Advertisement(models.Model):
    """نظام الإعلانات"""
    PLACEMENT_CHOICES = [
        ('header', _('الرأس')),
        ('sidebar', _('الشريط الجانبي')),
        ('footer', _('التذييل')),
        ('content_top', _('أعلى المحتوى')),
        ('content_bottom', _('أسفل المحتوى')),
        ('between_posts', _('بين المنشورات')),
    ]
    
    TYPE_CHOICES = [
        ('banner', _('بانر')),
        ('text', _('نص')),
        ('html', _('HTML')),
    ]
    
    title = models.CharField(_('العنوان'), max_length=100)
    type = models.CharField(_('النوع'), max_length=20, choices=TYPE_CHOICES, default='banner')
    placement = models.CharField(_('الموضع'), max_length=20, choices=PLACEMENT_CHOICES)
    
    # محتوى الإعلان
    image = models.ImageField(_('الصورة'), upload_to='ads/', blank=True)
    text_content = models.TextField(_('المحتوى النصي'), blank=True)
    html_content = models.TextField(_('محتوى HTML'), blank=True)
    link_url = models.URLField(_('رابط الإعلان'), blank=True)
    link_text = models.CharField(_('نص الرابط'), max_length=100, blank=True)
    
    # الإعدادات
    is_active = models.BooleanField(_('مفعل'), default=True)
    start_date = models.DateTimeField(_('تاريخ البداية'), null=True, blank=True)
    end_date = models.DateTimeField(_('تاريخ النهاية'), null=True, blank=True)
    order = models.PositiveIntegerField(_('الترتيب'), default=0)
    
    # إحصائيات
    views_count = models.PositiveIntegerField(_('عدد المشاهدات'), default=0)
    clicks_count = models.PositiveIntegerField(_('عدد النقرات'), default=0)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('إعلان')
        verbose_name_plural = _('الإعلانات')
        ordering = ['placement', 'order']
    
    def __str__(self):
        return f'{self.title} - {self.get_placement_display()}'


# إشارات Django لإنشاء إعدادات افتراضية
from django.db.models.signals import post_migrate
from django.dispatch import receiver

@receiver(post_migrate)
def create_default_site_settings(sender, **kwargs):
    """إنشاء إعدادات الموقع الافتراضية بعد التهجير"""
    if sender.name == 'core':
        SiteSettings.get_settings()
