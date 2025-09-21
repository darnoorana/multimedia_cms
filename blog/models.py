# blog/models.py - نماذج المدونة

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify
from core.models import Category

class Post(models.Model):
    """مقالات المدونة"""
    title = models.CharField(_('العنوان'), max_length=200)
    slug = models.SlugField(_('الرابط المختصر'), unique=True, blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('الكاتب'))
    content = models.TextField(_('المحتوى'))
    excerpt = models.TextField(_('المقطع'), max_length=300, blank=True)
    featured_image = models.ImageField(_('الصورة المميزة'), upload_to='blog/images/', blank=True)
    
    # إعدادات النشر
    is_published = models.BooleanField(_('منشور'), default=False)
    is_featured = models.BooleanField(_('مميز'), default=False)
    allow_comments = models.BooleanField(_('السماح بالتعليقات'), default=True)
    
    # إعدادات SEO
    meta_title = models.CharField(_('عنوان Meta'), max_length=60, blank=True)
    meta_description = models.TextField(_('وصف Meta'), max_length=160, blank=True)
    meta_keywords = models.TextField(_('كلمات مفتاحية'), blank=True)
    
    # التصنيفات والعلامات
    categories = models.ManyToManyField(Category, verbose_name=_('التصنيفات'), blank=True)
    tags = models.CharField(_('العلامات'), max_length=200, blank=True, help_text=_('افصل بفواصل'))
    
    # إحصائيات
    views_count = models.PositiveIntegerField(_('عدد المشاهدات'), default=0)
    
    # التواريخ
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    published_at = models.DateTimeField(_('تاريخ النشر'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('مقال')
        verbose_name_plural = _('المقالات')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if not self.excerpt and self.content:
            self.excerpt = self.content[:200] + '...' if len(self.content) > 200 else self.content
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('blog:post_detail', kwargs={'slug': self.slug})

