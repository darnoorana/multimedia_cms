
# Register your models here.
# content/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
import csv
import io

from .models import (
    Playlist, PlaylistItem, Tag, Comment, PlaylistItemTag
)


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'category', 'is_featured', 'is_published', 
        'items_count', 'views_count', 'created_at'
    ]
    list_filter = [
        'is_featured', 'is_published', 'category', 
        'allow_comments', 'created_at'
    ]
    list_editable = ['is_featured', 'is_published']
    search_fields = ['title', 'description', 'meta_keywords']
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'created_at'
    actions = [
        'make_featured', 'remove_featured', 
        'publish_playlists', 'unpublish_playlists',
        'export_playlists'
    ]
    
    fieldsets = [
        (_('معلومات أساسية'), {
            'fields': ('title', 'slug', 'category', 'description', 'thumbnail')
        }),
        (_('إعدادات SEO'), {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        (_('إعدادات العرض'), {
            'fields': ('is_featured', 'is_published', 'allow_comments', 'order')
        }),
        (_('معلومات إضافية'), {
            'fields': ('created_by', 'views_count'),
            'classes': ('collapse',)
        }),
    ]
    
    readonly_fields = ['views_count']
    
    def save_model(self, request, obj, form, change):
        if not change:  # إنشاء جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def items_count(self, obj):
        """عدد العناصر في القائمة"""
        count = obj.playlistitem_set.filter(is_published=True).count()
        url = reverse('admin:content_playlistitem_changelist') + f'?playlist__id__exact={obj.id}'
        return format_html(
            '<a href="{}" class="button">{} عنصر</a>',
            url, count
        )
    items_count.short_description = _('عدد العناصر')
    
    def make_featured(self, request, queryset):
        """جعل القوائم مميزة"""
        updated = queryset.update(is_featured=True)
        self.message_user(request, _('تم جعل {} قائمة مميزة').format(updated))
    make_featured.short_description = _('جعل مميزة')
    
    def remove_featured(self, request, queryset):
        """إزالة التمييز"""
        updated = queryset.update(is_featured=False)
        self.message_user(request, _('تم إزالة التمييز من {} قائمة').format(updated))
    remove_featured.short_description = _('إزالة التمييز')
    
    def publish_playlists(self, request, queryset):
        """نشر القوائم"""
        updated = queryset.update(is_published=True)
        self.message_user(request, _('تم نشر {} قائمة').format(updated))
    publish_playlists.short_description = _('نشر القوائم')
    
    def unpublish_playlists(self, request, queryset):
        """إلغاء نشر القوائم"""
        updated = queryset.update(is_published=False)
        self.message_user(request, _('تم إلغاء نشر {} قائمة').format(updated))
    unpublish_playlists.short_description = _('إلغاء النشر')
    
    def export_playlists(self, request, queryset):
        """تصدير القوائم إلى CSV"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="playlists.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Title', 'Category', 'Description', 'Is Featured', 
            'Is Published', 'Views', 'Items Count', 'Created Date'
        ])
        
        for playlist in queryset:
            writer.writerow([
                playlist.title,
                playlist.category.name,
                playlist.description,
                'Yes' if playlist.is_featured else 'No',
                'Yes' if playlist.is_published else 'No',
                playlist.views_count,
                playlist.total_items,
                playlist.created_at.strftime('%Y-%m-%d')
            ])
        
        return response
    export_playlists.short_description = _('تصدير إلى CSV')


class PlaylistItemTagInline(admin.TabularInline):
    model = PlaylistItemTag
    extra = 1
    autocomplete_fields = ['tag']


@admin.register(PlaylistItem)
class PlaylistItemAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'playlist', 'content_type', 'is_published',
        'views_count', 'downloads_stats', 'created_at'
    ]
    list_filter = [
        'content_type', 'is_published', 'allow_comments',
        'playlist__category', 'created_at'
    ]
    list_editable = ['is_published']
    search_fields = [
        'title', 'content_text', 'youtube_url', 
        'soundcloud_url', 'playlist__title'
    ]
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'created_at'
    actions = [
        'publish_items', 'unpublish_items', 
        'bulk_import_csv', 'export_items'
    ]
    inlines = [PlaylistItemTagInline]
    
    fieldsets = [
        (_('معلومات أساسية'), {
            'fields': ('playlist', 'title', 'slug', 'content_type', 'thumbnail')
        }),
        (_('الوسائط'), {
            'fields': ('youtube_url', 'soundcloud_url'),
            'classes': ('collapse',)
        }),
        (_('المحتوى النصي'), {
            'fields': ('content_text',),
            'classes': ('collapse',)
        }),
        (_('إعدادات SEO'), {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        (_('إعدادات العرض'), {
            'fields': ('is_published', 'allow_comments', 'order')
        }),
        (_('إحصائيات'), {
            'fields': (
                'views_count', 'youtube_downloads', 'soundcloud_downloads',
                'text_copies', 'shares_count'
            ),
            'classes': ('collapse',)
        }),
    ]
    
    readonly_fields = [
        'views_count', 'youtube_downloads', 'soundcloud_downloads',
        'text_copies', 'shares_count', 'youtube_video_id', 'soundcloud_track_id'
    ]
    
    def get_urls(self):
        """إضافة URLs مخصصة للإدارة"""
        urls = super().get_urls()
        custom_urls = [
            path('bulk-import/', self.admin_site.admin_view(self.bulk_import_view), name='content_playlistitem_bulk_import'),
        ]
        return custom_urls + urls
    
    def downloads_stats(self, obj):
        """إحصائيات التحميل"""
        youtube = obj.youtube_downloads
        soundcloud = obj.soundcloud_downloads
        return format_html(
            '<span title="تحميلات يوتيوب"><i class="fab fa-youtube"></i> {}</span><br>'
            '<span title="تحميلات ساوند كلاود"><i class="fab fa-soundcloud"></i> {}</span>',
            youtube, soundcloud
        )
    downloads_stats.short_description = _('التحميلات')
    
    def publish_items(self, request, queryset):
        """نشر العناصر"""
        updated = queryset.update(is_published=True)
        self.message_user(request, _('تم نشر {} عنصر').format(updated))
    publish_items.short_description = _('نشر العناصر')
    
    def unpublish_items(self, request, queryset):
        """إلغاء نشر العناصر"""
        updated = queryset.update(is_published=False)
        self.message_user(request, _('تم إلغاء نشر {} عنصر').format(updated))
    unpublish_items.short_description = _('إلغاء النشر')
    
    def export_items(self, request, queryset):
        """تصدير العناصر إلى CSV"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="playlist_items.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Playlist', 'Title', 'Content Type', 'YouTube URL', 'SoundCloud URL',
            'Content Text', 'Is Published', 'Views', 'Created Date'
        ])
        
        for item in queryset:
            writer.writerow([
                item.playlist.title,
                item.title,
                item.get_content_type_display(),
                item.youtube_url or '',
                item.soundcloud_url or '',
                (item.content_text[:100] + '...') if item.content_text and len(item.content_text) > 100 else (item.content_text or ''),
                'Yes' if item.is_published else 'No',
                item.views_count,
                item.created_at.strftime('%Y-%m-%d')
            ])
        
        return response
    export_items.short_description = _('تصدير إلى CSV')
    
    def bulk_import_csv(self, request, queryset):
        """استيراد متعدد من CSV"""
        messages.info(request, _('استخدم رابط "استيراد متعدد" في أعلى الصفحة'))
    bulk_import_csv.short_description = _('استيراد من CSV')
    
    def bulk_import_view(self, request):
        """صفحة الاستيراد المتعدد"""
        if request.method == 'POST':
            csv_file = request.FILES.get('csv_file')
            playlist_id = request.POST.get('playlist')
            
            if not csv_file:
                messages.error(request, _('يرجى اختيار ملف CSV'))
                return redirect('admin:content_playlistitem_bulk_import')
            
            if not csv_file.name.endswith('.csv'):
                messages.error(request, _('يرجى اختيار ملف CSV صحيح'))
                return redirect('admin:content_playlistitem_bulk_import')
            
            try:
                playlist = Playlist.objects.get(pk=playlist_id)
                
                # قراءة الملف
                decoded_file = csv_file.read().decode('utf-8')
                csv_data = csv.reader(io.StringIO(decoded_file))
                
                # تخطي الهيدر
                next(csv_data, None)
                
                created_count = 0
                errors = []
                
                for row_num, row in enumerate(csv_data, start=2):
                    try:
                        if len(row) < 4:  # الحد الأدنى: title, content_type, youtube_url, soundcloud_url
                            continue
                        
                        title = row[0].strip()
                        content_type = row[1].strip()
                        youtube_url = row[2].strip() if len(row) > 2 else ''
                        soundcloud_url = row[3].strip() if len(row) > 3 else ''
                        content_text = row[4].strip() if len(row) > 4 else ''
                        
                        if not title:
                            continue
                        
                        # إنشاء العنصر
                        PlaylistItem.objects.create(
                            playlist=playlist,
                            title=title,
                            content_type=content_type,
                            youtube_url=youtube_url,
                            soundcloud_url=soundcloud_url,
                            content_text=content_text,
                            is_published=True
                        )
                        created_count += 1
                        
                    except Exception as e:
                        errors.append(f'الصف {row_num}: {str(e)}')
                
                if created_count > 0:
                    messages.success(request, _('تم إنشاء {} عنصر بنجاح').format(created_count))
                
                if errors:
                    messages.warning(request, _('أخطاء في الصفوف التالية: {}').format(', '.join(errors[:5])))
                
                return redirect('admin:content_playlistitem_changelist')
                
            except Playlist.DoesNotExist:
                messages.error(request, _('قائمة التشغيل غير موجودة'))
            except Exception as e:
                messages.error(request, _('حدث خطأ أثناء الاستيراد: {}').format(str(e)))
        
        # عرض النموذج
        playlists = Playlist.objects.all().order_by('title')
        
        context = {
            'title': _('استيراد عناصر من CSV'),
            'playlists': playlists,
            'csv_example': [
                ['العنوان', 'نوع المحتوى', 'رابط يوتيوب', 'رابط ساوند كلاود', 'النص'],
                ['مثال فيديو', 'youtube', 'https://youtube.com/watch?v=abc123', '', 'وصف الفيديو'],
                ['مثال صوتي', 'soundcloud', '', 'https://soundcloud.com/user/track', 'وصف الصوت'],
                ['مثال مختلط', 'mixed', 'https://youtube.com/watch?v=def456', 'https://soundcloud.com/user/track2', 'المحتوى النصي'],
            ],
            'opts': self.model._meta,
        }
        
        return render(request, 'admin/content/bulk_import.html', context)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'usage_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['usage_count']
    actions = ['update_usage_count']
    
    def update_usage_count(self, request, queryset):
        """تحديث عداد الاستخدام"""
        for tag in queryset:
            count = PlaylistItemTag.objects.filter(tag=tag).count()
            tag.usage_count = count
            tag.save()
        
        self.message_user(request, _('تم تحديث عداد الاستخدام للعلامات المحددة'))
    update_usage_count.short_description = _('تحديث عداد الاستخدام')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = [
        'author_name', 'playlist_item', 'is_approved', 
        'is_spam', 'created_at'
    ]
    list_filter = [
        'is_approved', 'is_spam', 'created_at',
        'playlist_item__playlist__category'
    ]
    list_editable = ['is_approved', 'is_spam']
    search_fields = [
        'author_name', 'author_email', 'content',
        'playlist_item__title'
    ]
    date_hierarchy = 'created_at'
    actions = [
        'approve_comments', 'unapprove_comments',
        'mark_as_spam', 'mark_as_not_spam'
    ]
    
    fieldsets = [
        (_('معلومات الكاتب'), {
            'fields': ('author_name', 'author_email', 'author_website')
        }),
        (_('المحتوى'), {
            'fields': ('playlist_item', 'content')
        }),
        (_('الإشراف'), {
            'fields': ('is_approved', 'is_spam')
        }),
        (_('معلومات تقنية'), {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    ]
    
    readonly_fields = ['ip_address', 'user_agent']
    
    def approve_comments(self, request, queryset):
        """الموافقة على التعليقات"""
        updated = queryset.update(is_approved=True, is_spam=False)
        self.message_user(request, _('تم الموافقة على {} تعليق').format(updated))
    approve_comments.short_description = _('الموافقة على التعليقات')
    
    def unapprove_comments(self, request, queryset):
        """إلغاء الموافقة على التعليقات"""
        updated = queryset.update(is_approved=False)
        self.message_user(request, _('تم إلغاء الموافقة على {} تعليق').format(updated))
    unapprove_comments.short_description = _('إلغاء الموافقة')
    
    def mark_as_spam(self, request, queryset):
        """تحديد كمزعج"""
        updated = queryset.update(is_spam=True, is_approved=False)
        self.message_user(request, _('تم تحديد {} تعليق كمزعج').format(updated))
    mark_as_spam.short_description = _('تحديد كمزعج')
    
    def mark_as_not_spam(self, request, queryset):
        """إزالة علامة المزعج"""
        updated = queryset.update(is_spam=False)
        self.message_user(request, _('تم إزالة علامة المزعج من {} تعليق').format(updated))
    mark_as_not_spam.short_description = _('ليس مزعج')


# تحسين واجهة الإدارة
admin.site.site_header = _('إدارة منصة المحتوى المتعدد الوسائط')
admin.site.site_title = _('لوحة الإدارة')
admin.site.index_title = _('مرحباً بك في لوحة إدارة الموقع')
