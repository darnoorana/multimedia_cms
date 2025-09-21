
# Register your models here.
# core/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponse
import csv

from .models import (
    SiteSettings, Category, Newsletter, 
    ContactMessage, Advertisement
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = [
        (_('معلومات الموقع الأساسية'), {
            'fields': ('site_name', 'site_description', 'site_logo', 'site_favicon')
        }),
        (_('معلومات الاتصال'), {
            'fields': ('contact_email', 'contact_phone', 'contact_whatsapp')
        }),
        (_('إعدادات SEO'), {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        (_('وسائل التواصل الاجتماعي'), {
            'fields': (
                'facebook_url', 'twitter_url', 'youtube_url', 
                'instagram_url', 'telegram_url', 'soundcloud_url', 'tiktok_url'
            ),
            'classes': ('collapse',)
        }),
        (_('إعدادات API'), {
            'fields': ('youtube_api_key', 'soundcloud_client_id', 'telegram_bot_token'),
            'classes': ('collapse',)
        }),
        (_('النشرة الإخبارية'), {
            'fields': ('newsletter_enabled', 'newsletter_from_email'),
            'classes': ('collapse',)
        }),
        (_('RSS Feed'), {
            'fields': ('rss_enabled', 'rss_title', 'rss_description'),
            'classes': ('collapse',)
        }),
    ]
    
    def has_add_permission(self, request):
        """السماح بإنشاء إعدادات واحدة فقط"""
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """منع حذف الإعدادات"""
        return False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'order', 'playlist_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    list_editable = ['is_active', 'order']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = [
        (_('معلومات أساسية'), {
            'fields': ('name', 'slug', 'description', 'image')
        }),
        (_('إعدادات SEO'), {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        (_('إعدادات العرض'), {
            'fields': ('order', 'is_active')
        }),
    ]
    
    def playlist_count(self, obj):
        """عدد قوائم التشغيل في التصنيف"""
        count = obj.playlist_set.filter(is_published=True).count()
        return format_html(
            '<span class="badge badge-primary">{}</span>',
            count
        )
    playlist_count.short_description = _('عدد القوائم')


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ['email', 'is_active', 'subscribed_at']
    list_filter = ['is_active', 'subscribed_at']
    search_fields = ['email']
    date_hierarchy = 'subscribed_at'
    actions = ['export_emails', 'activate_subscribers', 'deactivate_subscribers']
    
    def export_emails(self, request, queryset):
        """تصدير قائمة البريد الإلكتروني"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="newsletter_subscribers.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Email', 'Status', 'Subscribed Date'])
        
        for subscriber in queryset:
            writer.writerow([
                subscriber.email,
                'Active' if subscriber.is_active else 'Inactive',
                subscriber.subscribed_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    export_emails.short_description = _('تصدير قائمة البريد الإلكتروني')
    
    def activate_subscribers(self, request, queryset):
        """تفعيل المشتركين"""
        updated = queryset.update(is_active=True)
        self.message_user(request, _('تم تفعيل {} مشترك').format(updated))
    activate_subscribers.short_description = _('تفعيل المشتركين المحددين')
    
    def deactivate_subscribers(self, request, queryset):
        """إلغاء تفعيل المشتركين"""
        updated = queryset.update(is_active=False)
        self.message_user(request, _('تم إلغاء تفعيل {} مشترك').format(updated))
    deactivate_subscribers.short_description = _('إلغاء تفعيل المشتركين المحددين')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'is_read', 'is_replied', 'created_at']
    list_filter = ['is_read', 'is_replied', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    actions = ['mark_as_read', 'mark_as_replied']
    
    fieldsets = [
        (_('معلومات المرسل'), {
            'fields': ('name', 'email', 'subject')
        }),
        (_('الرسالة'), {
            'fields': ('message',)
        }),
        (_('حالة الرسالة'), {
            'fields': ('is_read', 'is_replied', 'created_at')
        }),
    ]
    
    def mark_as_read(self, request, queryset):
        """تحديد كمقروءة"""
        updated = queryset.update(is_read=True)
        self.message_user(request, _('تم تحديد {} رسالة كمقروءة').format(updated))
    mark_as_read.short_description = _('تحديد كمقروءة')
    
    def mark_as_replied(self, request, queryset):
        """تحديد كمجاب عليها"""
        updated = queryset.update(is_replied=True, is_read=True)
        self.message_user(request, _('تم تحديد {} رسالة كمجاب عليها').format(updated))
    mark_as_replied.short_description = _('تحديد كمجاب عليها')


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'type', 'placement', 'is_active', 'order',
        'start_date', 'end_date', 'views_count', 'clicks_count'
    ]
    list_filter = ['type', 'placement', 'is_active', 'start_date', 'end_date']
    search_fields = ['title', 'text_content']
    list_editable = ['is_active', 'order']
    date_hierarchy = 'created_at'
    
    fieldsets = [
        (_('معلومات الإعلان'), {
            'fields': ('title', 'type', 'placement')
        }),
        (_('محتوى الإعلان'), {
            'fields': ('image', 'text_content', 'html_content', 'link_url', 'link_text')
        }),
        (_('إعدادات العرض'), {
            'fields': ('is_active', 'start_date', 'end_date', 'order')
        }),
        (_('إحصائيات'), {
            'fields': ('views_count', 'clicks_count'),
            'classes': ('collapse',)
        }),
    ]
    
    readonly_fields = ['views_count', 'clicks_count']


# تخصيص لوحة الإدارة
admin.site.site_header = _('إدارة منصة المحتوى المتعدد الوسائط - د. علي بشير أحمد')
admin.site.site_title = _('لوحة الإدارة')
admin.site.index_title = _('مرحباً بك في لوحة إدارة الموقع')
