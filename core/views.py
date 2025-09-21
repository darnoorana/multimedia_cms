
# Create your views here.
# core/views.py

from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import translation
from django.conf import settings

from .models import SiteSettings, Newsletter, ContactMessage
from content.models import Playlist, PlaylistItem, Category
from blog.models import Post
from projects.models import Project


class HomeView(TemplateView):
    """الصفحة الرئيسية"""
    template_name = 'core/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # المحتوى المميز للصفحة الرئيسية
        context['featured_playlists'] = Playlist.objects.filter(
            is_published=True, 
            is_featured=True
        ).select_related('category').order_by('-created_at')[:6]
        
        context['recent_playlists'] = Playlist.objects.filter(
            is_published=True
        ).select_related('category').order_by('-created_at')[:8]
        
        context['categories'] = Category.objects.filter(
            is_active=True
        ).order_by('order', 'name')[:6]
        
        # آخر منشورات المدونة
        context['recent_posts'] = Post.objects.filter(
            is_published=True
        ).select_related('author').order_by('-created_at')[:4]
        
        # المشاريع المميزة
        context['featured_projects'] = Project.objects.filter(
            is_published=True,
            is_featured=True
        ).order_by('-created_at')[:3]
        
        return context


class AboutView(TemplateView):
    """صفحة من نحن"""
    template_name = 'core/about.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('من نحن')
        context['breadcrumb'] = [
            {'title': _('الرئيسية'), 'url': '/'},
            {'title': _('من نحن'), 'url': None}
        ]
        return context


class ContactView(TemplateView):
    """صفحة اتصل بنا"""
    template_name = 'core/contact.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('اتصل بنا')
        context['breadcrumb'] = [
            {'title': _('الرئيسية'), 'url': '/'},
            {'title': _('اتصل بنا'), 'url': None}
        ]
        return context
    
    def post(self, request):
        """معالجة إرسال رسالة الاتصال"""
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        
        if not all([name, email, subject, message]):
            messages.error(request, _('يرجى ملء جميع الحقول المطلوبة'))
            return render(request, self.template_name, self.get_context_data())
        
        try:
            ContactMessage.objects.create(
                name=name,
                email=email,
                subject=subject,
                message=message
            )
            messages.success(request, _('تم إرسال رسالتك بنجاح. سنتواصل معك قريباً'))
            return redirect('core:contact')
            
        except Exception as e:
            messages.error(request, _('حدث خطأ أثناء إرسال الرسالة. يرجى المحاولة مرة أخرى'))
            return render(request, self.template_name, self.get_context_data())


class SearchView(ListView):
    """صفحة البحث"""
    template_name = 'core/search.html'
    context_object_name = 'results'
    paginate_by = 12
    
    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        if not query:
            return []
        
        # البحث في قوائم التشغيل
        playlists = Playlist.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query),
            is_published=True
        ).select_related('category')
        
        # البحث في عناصر قوائم التشغيل
        playlist_items = PlaylistItem.objects.filter(
            Q(title__icontains=query) |
            Q(content_text__icontains=query),
            is_published=True,
            playlist__is_published=True
        ).select_related('playlist', 'playlist__category')
        
        # البحث في منشورات المدونة
        blog_posts = Post.objects.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(excerpt__icontains=query),
            is_published=True
        ).select_related('author')
        
        # دمج النتائج
        results = []
        for playlist in playlists:
            results.append({
                'type': 'playlist',
                'object': playlist,
                'title': playlist.title,
                'description': playlist.description,
                'url': playlist.get_absolute_url(),
                'date': playlist.created_at,
            })
        
        for item in playlist_items:
            results.append({
                'type': 'playlist_item',
                'object': item,
                'title': item.title,
                'description': item.content_text[:200] + '...' if item.content_text else '',
                'url': item.get_absolute_url(),
                'date': item.created_at,
            })
        
        for post in blog_posts:
            results.append({
                'type': 'blog_post',
                'object': post,
                'title': post.title,
                'description': post.excerpt or (post.content[:200] + '...'),
                'url': post.get_absolute_url(),
                'date': post.created_at,
            })
        
        # ترتيب النتائج حسب التاريخ
        results.sort(key=lambda x: x['date'], reverse=True)
        
        return results
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        context['query'] = query
        context['page_title'] = _('نتائج البحث')
        context['breadcrumb'] = [
            {'title': _('الرئيسية'), 'url': '/'},
            {'title': _('البحث'), 'url': None}
        ]
        context['total_results'] = len(self.get_queryset()) if query else 0
        return context


class NewsletterSubscribeView(TemplateView):
    """الاشتراك في النشرة الإخبارية"""
    
    def post(self, request):
        email = request.POST.get('email', '').strip().lower()
        
        if not email:
            messages.error(request, _('يرجى إدخال بريد إلكتروني صحيح'))
            return redirect(request.META.get('HTTP_REFERER', 'core:home'))
        
        try:
            newsletter, created = Newsletter.objects.get_or_create(email=email)
            if created:
                messages.success(request, _('تم اشتراكك في النشرة الإخبارية بنجاح'))
            else:
                if newsletter.is_active:
                    messages.info(request, _('أنت مشترك بالفعل في النشرة الإخبارية'))
                else:
                    newsletter.is_active = True
                    newsletter.save()
                    messages.success(request, _('تم تفعيل اشتراكك في النشرة الإخبارية'))
                    
        except Exception as e:
            messages.error(request, _('حدث خطأ أثناء الاشتراك. يرجى المحاولة مرة أخرى'))
        
        return redirect(request.META.get('HTTP_REFERER', 'core:home'))


class NewsletterUnsubscribeView(TemplateView):
    """إلغاء الاشتراك في النشرة الإخبارية"""
    template_name = 'core/newsletter_unsubscribe.html'
    
    def get(self, request):
        email = request.GET.get('email', '').strip()
        
        if email:
            try:
                newsletter = Newsletter.objects.get(email=email, is_active=True)
                newsletter.is_active = False
                newsletter.save()
                messages.success(request, _('تم إلغاء اشتراكك في النشرة الإخبارية'))
            except Newsletter.DoesNotExist:
                messages.error(request, _('البريد الإلكتروني غير مشترك في النشرة'))
        
        return render(request, self.template_name)


class LanguageView(TemplateView):
    """تغيير لغة الموقع"""
    
    def get(self, request):
        language = request.GET.get('lang', 'ar')
        
        if language in dict(settings.LANGUAGES):
            translation.activate(language)
            request.session[translation.LANGUAGE_SESSION_KEY] = language
        
        return redirect(request.META.get('HTTP_REFERER', 'core:home'))


class SuccessView(TemplateView):
    """صفحة النجاح العامة"""
    template_name = 'core/success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['message'] = self.request.GET.get('message', _('تمت العملية بنجاح'))
        return context


class PrivacyView(TemplateView):
    """صفحة سياسة الخصوصية"""
    template_name = 'core/privacy.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('سياسة الخصوصية')
        context['breadcrumb'] = [
            {'title': _('الرئيسية'), 'url': '/'},
            {'title': _('سياسة الخصوصية'), 'url': None}
        ]
        return context


class TermsView(TemplateView):
    """صفحة شروط الاستخدام"""
    template_name = 'core/terms.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('شروط الاستخدام')
        context['breadcrumb'] = [
            {'title': _('الرئيسية'), 'url': '/'},
            {'title': _('شروط الاستخدام'), 'url': None}
        ]
        return context


# صفحات الأخطاء المخصصة
def custom_404(request, exception=None):
    """صفحة خطأ 404 مخصصة"""
    context = {
        'page_title': _('الصفحة غير موجودة'),
    }
    return render(request, 'core/404.html', context, status=404)


def custom_500(request):
    """صفحة خطأ 500 مخصصة"""
    context = {
        'page_title': _('خطأ في الخادم'),
    }
    return render(request, 'core/500.html', context, status=500)
