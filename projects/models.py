

# projects/models.py - نماذج المشاريع

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify

class Project(models.Model):
    """المشاريع"""
    STATUS_CHOICES = [
        ('planning', _('تخطيط')),
        ('active', _('نشط')),
        ('completed', _('مكتمل')),
        ('paused', _('متوقف مؤقتاً')),
        ('cancelled', _('ملغى')),
    ]
    
    title = models.CharField(_('العنوان'), max_length=200)
    slug = models.SlugField(_('الرابط المختصر'), unique=True, blank=True)
    description = models.TextField(_('الوصف'))
    short_description = models.TextField(_('الوصف المختصر'), max_length=300)
    image = models.ImageField(_('الصورة'), upload_to='projects/', blank=True)
    
    # حالة المشروع
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='planning')
    progress = models.PositiveIntegerField(_('نسبة الإنجاز'), default=0, help_text=_('من 0 إلى 100'))
    
    # التواريخ
    start_date = models.DateField(_('تاريخ البداية'), null=True, blank=True)
    end_date = models.DateField(_('تاريخ النهاية'), null=True, blank=True)
    
    # إعدادات النشر
    is_published = models.BooleanField(_('منشور'), default=True)
    is_featured = models.BooleanField(_('مميز'), default=False)
    allow_participation = models.BooleanField(_('السماح بالمشاركة'), default=True)
    
    # إحصائيات
    participants_count = models.PositiveIntegerField(_('عدد المشاركين'), default=0)
    views_count = models.PositiveIntegerField(_('عدد المشاهدات'), default=0)
    
    # إعدادات إضافية
    external_link = models.URLField(_('رابط خارجي'), blank=True)
    contact_email = models.EmailField(_('بريد التواصل'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('مشروع')
        verbose_name_plural = _('المشاريع')
        ordering = ['-is_featured', '-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('projects:project_detail', kwargs={'slug': self.slug})
    
    @property
    def status_display(self):
        return self.get_status_display()


class ProjectParticipant(models.Model):
    """مشاركو المشاريع"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_('المشروع'))
    name = models.CharField(_('الاسم'), max_length=100)
    email = models.EmailField(_('البريد الإلكتروني'))
    phone = models.CharField(_('الهاتف'), max_length=20, blank=True)
    message = models.TextField(_('رسالة'), blank=True)
    
    is_approved = models.BooleanField(_('معتمد'), default=False)
    joined_at = models.DateTimeField(_('تاريخ الانضمام'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('مشارك')
        verbose_name_plural = _('المشاركون')
        unique_together = ['project', 'email']
    
    def __str__(self):
        return f'{self.name} - {self.project.title}'

