
# Register your models here.

# blog/admin.py - إدارة المدونة

from django.contrib import admin
from .models import Post
from django.utils.translation import gettext_lazy as _

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'is_published', 'is_featured', 'views_count', 'created_at']
    list_filter = ['is_published', 'is_featured', 'categories', 'created_at']
    list_editable = ['is_published', 'is_featured']
    search_fields = ['title', 'content', 'meta_keywords']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['categories']
    date_hierarchy = 'created_at'
    
    fieldsets = [
        (_('المحتوى الأساسي'), {
            'fields': ('title', 'slug', 'author', 'content', 'excerpt', 'featured_image')
        }),
        (_('التصنيف والعلامات'), {
            'fields': ('categories', 'tags')
        }),
        (_('إعدادات النشر'), {
            'fields': ('is_published', 'is_featured', 'allow_comments', 'published_at')
        }),
        (_('إعدادات SEO'), {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
    ]
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
        super().save_model(request, obj, form, change)

