
# Create your views here.
# content/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse, Http404, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse
import json

from .models import (
    Playlist, PlaylistItem, Tag, Comment,
    PlaylistItemTag
)
from core.models import Category


class PlaylistListView(ListView):
    """عرض قوائم التشغيل"""
    model = Playlist
    template_name = 'content/playlist_list.html'
    context_object_name = 'playlists'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Playlist.objects.filter(
            is_published=True
        ).select_related('category', 'created_by').prefetch_related(
            'playlistitem_set'
        ).order_by('-is_featured', '-created_at')
        
        # فلترة بالتصنيف
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # البحث
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # الترتيب
        sort_by = self.request.GET.get('sort', 'recent')
        if sort_by == 'popular':
            queryset = queryset.order_by('-views_count')
        elif sort_by == 'title':
            queryset = queryset.order_by('title')
        elif sort_by == 'oldest':
            queryset = queryset.order_by('created_at')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('قوائم التشغيل')
        context['categories'] = Category.objects.filter(is_active=True).order_by('order', 'name')
        context['current_category'] = self.request.GET.get('category', '')
        context['current_sort'] = self.request.GET.get('sort', 'recent')
        context['search_query'] = self.request.GET.get('q', '')
        
        context['breadcrumb'] = [
            {'title': _('الرئيسية'), 'url': reverse('core:home')},
            {'title': _('قوائم التشغيل'), 'url': None}
        ]
        
        return context


class CategoryPlaylistsView(ListView):
    """عرض قوائم التشغيل حسب التصنيف"""
    model = Playlist
    template_name = 'content/category_playlists.html'
    context_object_name = 'playlists'
    paginate_by = 12
    
    def get_queryset(self):
        self.category = get_object_or_404(
            Category, 
            slug=self.kwargs['category_slug'], 
            is_active=True
        )
        
        return Playlist.objects.filter(
            category=self.category,
            is_published=True
        ).select_related('created_by').prefetch_related(
            'playlistitem_set'
        ).order_by('-is_featured', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['page_title'] = self.category.name
        context['meta_description'] = self.category.meta_description or self.category.description
        
        context['breadcrumb'] = [
            {'title': _('الرئيسية'), 'url': reverse('core:home')},
            {'title': _('قوائم التشغيل'), 'url': reverse('content:playlist_list')},
            {'title': self.category.name, 'url': None}
        ]
        
        return context


class PlaylistDetailView(DetailView):
    """عرض تفاصيل قائمة التشغيل"""
    model = Playlist
    template_name = 'content/playlist_detail.html'
    context_object_name = 'playlist'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_object(self):
        obj = get_object_or_404(
            Playlist.objects.select_related('category', 'created_by'),
            slug=self.kwargs['slug'],
            is_published=True
        )
        
        # زيادة عدد المشاهدات
        Playlist.objects.filter(pk=obj.pk).update(
            views_count=F('views_count') + 1
        )
        
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # عناصر قائمة التشغيل
        playlist_items = PlaylistItem.objects.filter(
            playlist=self.object,
            is_published=True
        ).order_by('order', 'created_at')
        
        # الصفحات
        paginator = Paginator(playlist_items, 10)
        page_number = self.request.GET.get('page', 1)
        context['playlist_items'] = paginator.get_page(page_number)
        
        # التصنيفات والعلامات
        context['tags'] = Tag.objects.filter(
            playlistitemtag__playlist_item__playlist=self.object
        ).distinct()
        
        # قوائم تشغيل مقترحة
        context['related_playlists'] = Playlist.objects.filter(
            category=self.object.category,
            is_published=True
        ).exclude(pk=self.object.pk)[:4]
        
        # البيانات الوصفية
        context['page_title'] = self.object.title
        context['meta_description'] = self.object.meta_description or self.object.description
        context['meta_keywords'] = self.object.meta_keywords
        
        context['breadcrumb'] = [
            {'title': _('الرئيسية'), 'url': reverse('core:home')},
            {'title': _('قوائم التشغيل'), 'url': reverse('content:playlist_list')},
            {'title': self.object.category.name, 'url': reverse('content:category_playlists', kwargs={'category_slug': self.object.category.slug})},
            {'title': self.object.title, 'url': None}
        ]
        
        return context


class PlaylistItemDetailView(DetailView):
    """عرض تفاصيل عنصر قائمة التشغيل"""
    model = PlaylistItem
    template_name = 'content/playlist_item_detail.html'
    context_object_name = 'item'
    
    def get_object(self):
        playlist = get_object_or_404(
            Playlist,
            slug=self.kwargs['playlist_slug'],
            is_published=True
        )
        
        obj = get_object_or_404(
            PlaylistItem.objects.select_related('playlist', 'playlist__category'),
            playlist=playlist,
            slug=self.kwargs['item_slug'],
            is_published=True
        )
        
        # زيادة عدد المشاهدات
        PlaylistItem.objects.filter(pk=obj.pk).update(
            views_count=F('views_count') + 1
        )
        
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # العناصر السابقة واللاحقة
        playlist_items = PlaylistItem.objects.filter(
            playlist=self.object.playlist,
            is_published=True
        ).order_by('order', 'created_at')
        
        current_index = list(playlist_items).index(self.object)
        
        context['previous_item'] = playlist_items[current_index - 1] if current_index > 0 else None
        context['next_item'] = playlist_items[current_index + 1] if current_index < len(playlist_items) - 1 else None
        
        # التعليقات
        if self.object.allow_comments:
            comments = Comment.objects.filter(
                playlist_item=self.object,
                is_approved=True
            ).order_by('-created_at')
            
            paginator = Paginator(comments, 10)
            page_number = self.request.GET.get('page', 1)
            context['comments'] = paginator.get_page(page_number)
        
        # العلامات
        context['tags'] = Tag.objects.filter(
            playlistitemtag__playlist_item=self.object
        )
        
        # عناصر مقترحة من نفس القائمة
        context['related_items'] = PlaylistItem.objects.filter(
            playlist=self.object.playlist,
            is_published=True
        ).exclude(pk=self.object.pk).order_by('?')[:4]
        
        # البيانات الوصفية
        context['page_title'] = f"{self.object.title} - {self.object.playlist.title}"
        context['meta_description'] = self.object.meta_description or (self.object.content_text[:160] if self.object.content_text else self.object.playlist.description)
        
        context['breadcrumb'] = [
            {'title': _('الرئيسية'), 'url': reverse('core:home')},
            {'title': _('قوائم التشغيل'), 'url': reverse('content:playlist_list')},
            {'title': self.object.playlist.category.name, 'url': reverse('content:category_playlists', kwargs={'category_slug': self.object.playlist.category.slug})},
            {'title': self.object.playlist.title, 'url': reverse('content:playlist_detail', kwargs={'slug': self.object.playlist.slug})},
            {'title': self.object.title, 'url': None}
        ]
        
        return context


class TagView(ListView):
    """عرض العناصر حسب العلامة"""
    model = PlaylistItem
    template_name = 'content/tag_items.html'
    context_object_name = 'items'
    paginate_by = 12
    
    def get_queryset(self):
        self.tag = get_object_or_404(Tag, slug=self.kwargs['tag_slug'])
        
        return PlaylistItem.objects.filter(
            playlistitemtag__tag=self.tag,
            is_published=True,
            playlist__is_published=True
        ).select_related('playlist', 'playlist__category').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tag'] = self.tag
        context['page_title'] = f"العلامة: {self.tag.name}"
        
        context['breadcrumb'] = [
            {'title': _('الرئيسية'), 'url': reverse('core:home')},
            {'title': _('العلامات'), 'url': reverse('content:tag_list')},
            {'title': self.tag.name, 'url': None}
        ]
        
        return context


class TagListView(ListView):
    """عرض جميع العلامات"""
    model = Tag
    template_name = 'content/tag_list.html'
    context_object_name = 'tags'
    paginate_by = 50
    
    def get_queryset(self):
        return Tag.objects.filter(
            usage_count__gt=0
        ).order_by('-usage_count', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('العلامات')
        
        context['breadcrumb'] = [
            {'title': _('الرئيسية'), 'url': reverse('core:home')},
            {'title': _('العلامات'), 'url': None}
        ]
        
        return context


# AJAX Views للتفاعل
class IncrementViewAjax(TemplateView):
    """زيادة عدد المشاهدات عبر AJAX"""
    
    def post(self, request, item_id):
        try:
            item = get_object_or_404(PlaylistItem, pk=item_id)
            PlaylistItem.objects.filter(pk=item_id).update(
                views_count=F('views_count') + 1
            )
            
            return JsonResponse({
                'success': True,
                'views_count': item.views_count + 1
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


class YoutubeDownloadView(TemplateView):
    """تسجيل تحميل من يوتيوب"""
    
    def post(self, request, item_id):
        try:
            item = get_object_or_404(PlaylistItem, pk=item_id)
            
            if not item.youtube_url:
                return JsonResponse({
                    'success': False,
                    'error': _('لا يوجد رابط يوتيوب لهذا العنصر')
                }, status=400)
            
            # تسجيل التحميل
            PlaylistItem.objects.filter(pk=item_id).update(
                youtube_downloads=F('youtube_downloads') + 1
            )
            
            # إنشاء رابط التحميل (يمكن تطويره لاحقاً باستخدام مكتبة youtube-dl)
            download_url = f"https://youtube.com/watch?v={item.youtube_video_id}"
            
            return JsonResponse({
                'success': True,
                'download_url': download_url,
                'message': _('يتم توجيهك لصفحة التحميل...')
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


class SoundcloudDownloadView(TemplateView):
    """تسجيل تحميل من ساوند كلاود"""
    
    def post(self, request, item_id):
        try:
            item = get_object_or_404(PlaylistItem, pk=item_id)
            
            if not item.soundcloud_url:
                return JsonResponse({
                    'success': False,
                    'error': _('لا يوجد رابط ساوند كلاود لهذا العنصر')
                }, status=400)
            
            # تسجيل التحميل
            PlaylistItem.objects.filter(pk=item_id).update(
                soundcloud_downloads=F('soundcloud_downloads') + 1
            )
            
            return JsonResponse({
                'success': True,
                'download_url': item.soundcloud_url,
                'message': _('يتم توجيهك لصفحة التحميل...')
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


class CopyTextView(TemplateView):
    """تسجيل نسخ النص"""
    
    def post(self, request, item_id):
        try:
            item = get_object_or_404(PlaylistItem, pk=item_id)
            
            if not item.content_text:
                return JsonResponse({
                    'success': False,
                    'error': _('لا يوجد نص لنسخه في هذا العنصر')
                }, status=400)
            
            # تسجيل النسخ
            PlaylistItem.objects.filter(pk=item_id).update(
                text_copies=F('text_copies') + 1
            )
            
            return JsonResponse({
                'success': True,
                'text': item.content_text,
                'message': _('تم نسخ النص بنجاح')
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


class ShareView(TemplateView):
    """تسجيل المشاركة"""
    
    def post(self, request, item_id):
        try:
            item = get_object_or_404(PlaylistItem, pk=item_id)
            
            # تسجيل المشاركة
            PlaylistItem.objects.filter(pk=item_id).update(
                shares_count=F('shares_count') + 1
            )
            
            share_data = {
                'title': item.title,
                'description': item.content_text[:200] if item.content_text else item.playlist.description[:200],
                'url': request.build_absolute_uri(item.get_absolute_url()),
                'image': item.thumbnail.url if item.thumbnail else (item.playlist.thumbnail.url if item.playlist.thumbnail else '')
            }
            
            return JsonResponse({
                'success': True,
                'share_data': share_data,
                'message': _('تم تسجيل المشاركة')
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


class AddCommentView(TemplateView):
    """إضافة تعليق"""
    
    def post(self, request, item_id):
        try:
            item = get_object_or_404(PlaylistItem, pk=item_id)
            
            if not item.allow_comments:
                return JsonResponse({
                    'success': False,
                    'error': _('التعليقات مغلقة لهذا العنصر')
                }, status=400)
            
            # استخراج البيانات
            author_name = request.POST.get('name', '').strip()
            author_email = request.POST.get('email', '').strip()
            author_website = request.POST.get('website', '').strip()
            content = request.POST.get('content', '').strip()
            
            if not all([author_name, author_email, content]):
                return JsonResponse({
                    'success': False,
                    'error': _('يرجى ملء جميع الحقول المطلوبة')
                }, status=400)
            
            # إنشاء التعليق
            comment = Comment.objects.create(
                playlist_item=item,
                author_name=author_name,
                author_email=author_email,
                author_website=author_website,
                content=content,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
            
            return JsonResponse({
                'success': True,
                'message': _('تم إرسال التعليق بنجاح. سيظهر بعد المراجعة.')
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    def get_client_ip(self, request):
        """الحصول على عنوان IP الخاص بالعميل"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@method_decorator(login_required, name='dispatch')
class DeleteCommentView(TemplateView):
    """حذف تعليق (للمشرفين فقط)"""
    
    def post(self, request, comment_id):
        try:
            if not request.user.is_staff:
                return JsonResponse({
                    'success': False,
                    'error': _('غير مصرح لك بحذف التعليقات')
                }, status=403)
            
            comment = get_object_or_404(Comment, pk=comment_id)
            comment.delete()
            
            return JsonResponse({
                'success': True,
                'message': _('تم حذف التعليق بنجاح')
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


class ToggleLikeAjax(TemplateView):
    """تبديل الإعجاب (يمكن تطويره لاحقاً)"""
    
    def post(self, request, item_id):
        # هذا placeholder للميزة المستقبلية
        return JsonResponse({
            'success': False,
            'error': _('هذه الميزة غير متوفرة حالياً')
        }, status=501)
