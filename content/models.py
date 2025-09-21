
# Create your models here.
# content/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify
from core.models import Category
import re

class Playlist(models.Model):
    """قوائم التشغيل الرئيسية"""
    title = models.CharField(_('العنوان'), max_length=200)
    slug = models.SlugField(_('الرابط المختصر'), unique=True, blank=True)
    description = models.TextField(_('الوصف'), blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name=_('التصنيف'))
    thumbnail = models.ImageField(_('الصورة المصغرة'), upload_to='playlists/', blank=True)
    
    # إعدادات SEO
    meta_title = models.CharField(_('عنوان Meta'), max_length=60, blank=True)
    meta_description = models.TextField(_('وصف Meta'), max_length=160, blank=True)
    meta_keywords = models.TextField(_('كلمات مفتاحية'), blank=True)
    
    # الإعدادات
    is_featured = models.BooleanField(_('مميزة'), default=False)
    is_published = models.BooleanField(_('منشورة'), default=True)
    allow_comments = models.BooleanField(_('السماح بالتعليقات'), default=True)
    order = models.PositiveIntegerField(_('الترتيب'), default=0)
    
    # إحصائيات
    views_count = models.PositiveIntegerField(_('عدد المشاهدات'), default=0)
    
    # التواريخ
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('أنشأ بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('قائمة تشغيل')
        verbose_name_plural = _('قوائم التشغيل')
        ordering = ['-is_featured', 'order', '-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('content:playlist_detail', kwargs={'slug': self.slug})
    
    @property
    def total_items(self):
        return self.playlistitem_set.filter(is_published=True).count()


class PlaylistItem(models.Model):
    """عناصر قائمة التشغيل"""
    CONTENT_TYPE_CHOICES = [
        ('youtube', _('فيديو يوتيوب')),
        ('soundcloud', _('صوت ساوندكلاود')),
        ('mixed', _('مختلط (فيديو + صوت)')),
        ('text', _('نص فقط')),
    ]
    
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, verbose_name=_('قائمة التشغيل'))
    title = models.CharField(_('العنوان'), max_length=200)
    slug = models.SlugField(_('الرابط المختصر'), blank=True)
    content_type = models.CharField(_('نوع المحتوى'), max_length=20, choices=CONTENT_TYPE_CHOICES)
    
    # روابط الوسائط
    youtube_url = models.URLField(_('رابط يوتيوب'), blank=True, help_text=_('مثال: https://www.youtube.com/watch?v=VIDEO_ID'))
    soundcloud_url = models.URLField(_('رابط ساوندكلاود'), blank=True, help_text=_('مثال: https://soundcloud.com/user/track'))
    
    # معرفات الوسائط (يتم استخراجها تلقائياً)
    youtube_video_id = models.CharField(_('معرف فيديو يوتيوب'), max_length=50, blank=True)
    soundcloud_track_id = models.CharField(_('معرف مقطع ساوندكلاود'), max_length=50, blank=True)
    
    # المحتوى النصي
    content_text = models.TextField(_('النص'), blank=True)
    
    # الصور
    thumbnail = models.ImageField(_('الصورة المصغرة'), upload_to='playlist_items/', blank=True)
    
    # إعدادات SEO
    meta_title = models.CharField(_('عنوان Meta'), max_length=60, blank=True)
    meta_description = models.TextField(_('وصف Meta'), max_length=160, blank=True)
    
    # الإعدادات
    is_published = models.BooleanField(_('منشور'), default=True)
    allow_comments = models.BooleanField(_('السماح بالتعليقات'), default=True)
    order = models.PositiveIntegerField(_('الترتيب'), default=0)
    
    # إحصائيات
    views_count = models.PositiveIntegerField(_('عدد المشاهدات'), default=0)
    youtube_downloads = models.PositiveIntegerField(_('تحميلات يوتيوب'), default=0)
    soundcloud_downloads = models.PositiveIntegerField(_('تحميلات ساوندكلاود'), default=0)
    text_copies = models.PositiveIntegerField(_('نسخ النص'), default=0)
    shares_count = models.PositiveIntegerField(_('المشاركات'), default=0)
    
    # التواريخ
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('عنصر قائمة التشغيل')
        verbose_name_plural = _('عناصر قوائم التشغيل')
        ordering = ['playlist', 'order', 'created_at']
        unique_together = ['playlist', 'slug']
    
    def __str__(self):
        return f'{self.playlist.title} - {self.title}'
    
    def save(self, *args, **kwargs):
        # إنشاء slug تلقائياً
        if not self.slug:
            self.slug = slugify(self.title)
        
        # استخراج معرفات الوسائط
        if self.youtube_url:
            self.youtube_video_id = self.extract_youtube_id()
        if self.soundcloud_url:
            self.soundcloud_track_id = self.extract_soundcloud_id()
            
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('content:item_detail', kwargs={
            'playlist_slug': self.playlist.slug,
            'item_slug': self.slug
        })
    
    def extract_youtube_id(self):
        """استخراج معرف الفيديو من رابط يوتيوب"""
        if not self.youtube_url:
            return ''
        
        # أنماط مختلفة لروابط يوتيوب
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^&\n?#]+)',
            r'(?:https?://)?(?:www\.)?youtu\.be/([^&\n?#]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([^&\n?#]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.youtube_url)
            if match:
                return match.group(1)
        return ''
    
    def extract_soundcloud_id(self):
        """استخراج معرف المقطع من رابط ساوندكلاود"""
        if not self.soundcloud_url:
            return ''
        
        # يمكن تحسين هذا لاحقاً باستخدام SoundCloud API
        # حالياً نحفظ الرابط كامل كمعرف
        return self.soundcloud_url.split('/')[-1] if self.soundcloud_url else ''
    
    @property
    def youtube_embed_url(self):
        """رابط التضمين ليوتيوب"""
        if self.youtube_video_id:
            return f'https://www.youtube.com/embed/{self.youtube_video_id}'
        return ''
    
    @property
    def has_video(self):
        """التحقق من وجود فيديو"""
        return bool(self.youtube_url and self.youtube_video_id)
    
    @property
    def has_audio(self):
        """التحقق من وجود صوت"""
        return bool(self.soundcloud_url)
    
    @property
    def has_text(self):
        """التحقق من وجود نص"""
        return bool(self.content_text.strip())


class Comment(models.Model):
    """نظام التعليقات"""
    playlist_item = models.ForeignKey(PlaylistItem, on_delete=models.CASCADE, verbose_name=_('العنصر'))
    author_name = models.CharField(_('اسم الكاتب'), max_length=100)
    author_email = models.EmailField(_('بريد الكاتب'))
    author_website = models.URLField(_('موقع الكاتب'), blank=True)
    
    content = models.TextField(_('المحتوى'))
    
    # إعدادات الإشراف
    is_approved = models.BooleanField(_('معتمد'), default=False)
    is_spam = models.BooleanField(_('مزعج'), default=False)
    
    # معلومات تقنية
    ip_address = models.GenericIPAddressField(_('عنوان IP'), null=True, blank=True)
    user_agent = models.TextField(_('وكيل المستخدم'), blank=True)
    
    # التواريخ
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('تعليق')
        verbose_name_plural = _('التعليقات')
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.author_name} - {self.playlist_item.title[:50]}...'


class Tag(models.Model):
    """علامات المحتوى"""
    name = models.CharField(_('الاسم'), max_length=50, unique=True)
    slug = models.SlugField(_('الرابط المختصر'), unique=True, blank=True)
    description = models.TextField(_('الوصف'), blank=True)
    
    # إحصائيات
    usage_count = models.PositiveIntegerField(_('عدد الاستخدامات'), default=0)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('علامة')
        verbose_name_plural = _('العلامات')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class PlaylistItemTag(models.Model):
    """ربط العلامات بعناصر قوائم التشغيل"""
    playlist_item = models.ForeignKey(PlaylistItem, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['playlist_item', 'tag']
        verbose_name = _('علامة العنصر')
        verbose_name_plural = _('علامات العناصر')
