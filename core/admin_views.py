# core/admin_views.py

from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from datetime import timedelta, datetime
import json

from content.models import Playlist, PlaylistItem, Comment
from core.models import SiteSettings, Newsletter, ContactMessage, Advertisement
from blog.models import Post
from projects.models import Project
from django.contrib.auth.models import User


@method_decorator([login_required, staff_member_required], name='dispatch')
class AdminDashboardView(TemplateView):
    """لوحة التحكم الرئيسية"""
    template_name = 'admin/dashboard/main.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # الإحصائيات العامة
        context['stats'] = self.get_general_stats()
        
        # الرسوم البيانية
        context['charts_data'] = self.get_charts_data()
        
        # النشاط الأخير
        context['recent_activity'] = self.get_recent_activity()
        
        # التنبيهات والمهام
        context['alerts'] = self.get_alerts()
        
        # معلومات النظام
        context['system_info'] = self.get_system_info()
        
        return context
    
    def get_general_stats(self):
        """الحصول على الإحصائيات العامة"""
        now = timezone.now()
        last_30_days = now - timedelta(days=30)
        
        # إحصائيات المحتوى
        total_playlists = Playlist.objects.count()
        published_playlists = Playlist.objects.filter(is_published=True).count()
        total_items = PlaylistItem.objects.count()
        published_items = PlaylistItem.objects.filter(is_published=True).count()
        
        # إحصائيات التفاعل
        total_views = PlaylistItem.objects.aggregate(
            total=Sum('views_count')
        )['total'] or 0
        
        total_downloads = PlaylistItem.objects.aggregate(
            youtube=Sum('youtube_downloads'),
            soundcloud=Sum('soundcloud_downloads')
        )
        
        # إحصائيات المستخدمين
        total_users = User.objects.count()
        newsletter_subscribers = Newsletter.objects.filter(is_active=True).count()
        
        # التعليقات
        total_comments = Comment.objects.count()
        pending_comments = Comment.objects.filter(is_approved=False, is_spam=False).count()
        
        # رسائل التواصل
        unread_messages = ContactMessage.objects.filter(is_read=False).count()
        
        # النمو الشهري
        monthly_growth = self.calculate_monthly_growth()
        
        return {
            'content': {
                'total_playlists': total_playlists,
                'published_playlists': published_playlists,
                'total_items': total_items,
                'published_items': published_items,
                'publish_rate': round((published_items / total_items * 100) if total_items > 0 else 0, 1)
            },
            'engagement': {
                'total_views': total_views,
                'total_youtube_downloads': total_downloads['youtube'] or 0,
                'total_soundcloud_downloads': total_downloads['soundcloud'] or 0,
                'avg_views_per_item': round(total_views / published_items if published_items > 0 else 0, 1)
            },
            'community': {
                'total_users': total_users,
                'newsletter_subscribers': newsletter_subscribers,
                'total_comments': total_comments,
                'pending_comments': pending_comments,
                'unread_messages': unread_messages
            },
            'growth': monthly_growth
        }
    
    def calculate_monthly_growth(self):
        """حساب النمو الشهري"""
        now = timezone.now()
        current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month = (current_month - timedelta(days=1)).replace(day=1)
        
        # محتوى جديد هذا الشهر
        current_content = PlaylistItem.objects.filter(
            created_at__gte=current_month
        ).count()
        
        last_month_content = PlaylistItem.objects.filter(
            created_at__gte=last_month,
            created_at__lt=current_month
        ).count()
        
        content_growth = self.calculate_percentage_change(last_month_content, current_content)
        
        # مشتركين جدد
        current_subscribers = Newsletter.objects.filter(
            subscribed_at__gte=current_month
        ).count()
        
        last_month_subscribers = Newsletter.objects.filter(
            subscribed_at__gte=last_month,
            subscribed_at__lt=current_month
        ).count()
        
        subscriber_growth = self.calculate_percentage_change(last_month_subscribers, current_subscribers)
        
        return {
            'content_growth': content_growth,
            'subscriber_growth': subscriber_growth
        }
    
    def calculate_percentage_change(self, old_value, new_value):
        """حساب النسبة المئوية للتغيير"""
        if old_value == 0:
            return 100 if new_value > 0 else 0
        
        change = ((new_value - old_value) / old_value) * 100
        return round(change, 1)
    
    def get_charts_data(self):
        """الحصول على بيانات الرسوم البيانية"""
        return {
            'views_chart': self.get_views_chart_data(),
            'content_chart': self.get_content_chart_data(),
            'engagement_chart': self.get_engagement_chart_data(),
            'categories_chart': self.get_categories_chart_data()
        }
    
    def get_views_chart_data(self):
        """بيانات رسم المشاهدات (آخر 30 يوم)"""
        now = timezone.now()
        days_data = []
        
        for i in range(30):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            # هنا يمكن إضافة tracking للمشاهدات اليومية
            # حالياً سنستخدم بيانات عشوائية للعرض
            views = PlaylistItem.objects.filter(
                created_at__range=[day_start, day_end]
            ).aggregate(total=Sum('views_count'))['total'] or 0
            
            days_data.append({
                'date': day.strftime('%Y-%m-%d'),
                'views': views,
                'label': day.strftime('%d/%m')
            })
        
        return list(reversed(days_data))
    
    def get_content_chart_data(self):
        """بيانات رسم المحتوى المنشور"""
        content_types = PlaylistItem.objects.values('content_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return [
            {
                'type': item['content_type'],
                'count': item['count'],
                'label': dict(PlaylistItem.CONTENT_TYPE_CHOICES).get(item['content_type'], item['content_type'])
            }
            for item in content_types
        ]
    
    def get_engagement_chart_data(self):
        """بيانات رسم التفاعل"""
        engagement_data = PlaylistItem.objects.aggregate(
            views=Sum('views_count'),
            youtube_downloads=Sum('youtube_downloads'),
            soundcloud_downloads=Sum('soundcloud_downloads'),
            text_copies=Sum('text_copies'),
            shares=Sum('shares_count')
        )
        
        return [
            {'label': 'المشاهدات', 'value': engagement_data['views'] or 0},
            {'label': 'تحميلات يوتيوب', 'value': engagement_data['youtube_downloads'] or 0},
            {'label': 'تحميلات ساوند كلاود', 'value': engagement_data['soundcloud_downloads'] or 0},
            {'label': 'نسخ النص', 'value': engagement_data['text_copies'] or 0},
            {'label': 'المشاركات', 'value': engagement_data['shares'] or 0}
        ]
    
    def get_categories_chart_data(self):
        """بيانات رسم التصنيفات"""
        from core.models import Category
        
        categories_data = Category.objects.annotate(
            playlist_count=Count('playlist', filter=Q(playlist__is_published=True))
        ).filter(playlist_count__gt=0).order_by('-playlist_count')
        
        return [
            {
                'name': category.name,
                'count': category.playlist_count,
                'color': self.get_category_color(category.id)
            }
            for category in categories_data[:10]  # أفضل 10 تصنيفات
        ]
    
    def get_category_color(self, category_id):
        """الحصول على لون التصنيف"""
        colors = [
            '#007bff', '#28a745', '#dc3545', '#ffc107', '#17a2b8',
            '#6f42c1', '#e83e8c', '#fd7e14', '#20c997', '#6c757d'
        ]
        return colors[category_id % len(colors)]
    
    def get_recent_activity(self):
        """النشاط الأخير"""
        activities = []
        
        # آخر قوائم التشغيل
        recent_playlists = Playlist.objects.select_related('created_by').order_by('-created_at')[:5]
        for playlist in recent_playlists:
            activities.append({
                'type': 'playlist_created',
                'title': f'تم إنشاء قائمة تشغيل جديدة: {playlist.title}',
                'user': playlist.created_by.get_full_name() or playlist.created_by.username,
                'time': playlist.created_at,
                'url': f'/admin/content/playlist/{playlist.id}/change/',
                'icon': 'bi-collection-play',
                'color': 'primary'
            })
        
        # آخر التعليقات
        recent_comments = Comment.objects.select_related('playlist_item').order_by('-created_at')[:5]
        for comment in recent_comments:
            activities.append({
                'type': 'comment_added',
                'title': f'تعليق جديد على: {comment.playlist_item.title}',
                'user': comment.author_name,
                'time': comment.created_at,
                'url': f'/admin/content/comment/{comment.id}/change/',
                'icon': 'bi-chat-dots',
                'color': 'info'
            })
        
        # آخر الرسائل
        recent_messages = ContactMessage.objects.order_by('-created_at')[:3]
        for message in recent_messages:
            activities.append({
                'type': 'message_received',
                'title': f'رسالة جديدة: {message.subject}',
                'user': message.name,
                'time': message.created_at,
                'url': f'/admin/core/contactmessage/{message.id}/change/',
                'icon': 'bi-envelope',
                'color': 'warning' if not message.is_read else 'success'
            })
        
        # ترتيب حسب الوقت
        activities.sort(key=lambda x: x['time'], reverse=True)
        
        return activities[:15]
    
    def get_alerts(self):
        """التنبيهات والمهام"""
        alerts = []
        
        # تعليقات تحتاج موافقة
        pending_comments = Comment.objects.filter(is_approved=False, is_spam=False).count()
        if pending_comments > 0:
            alerts.append({
                'type': 'warning',
                'title': f'{pending_comments} تعليق في انتظار الموافقة',
                'action': '/admin/content/comment/?is_approved__exact=0&is_spam__exact=0',
                'icon': 'bi-chat-dots'
            })
        
        # رسائل غير مقروءة
        unread_messages = ContactMessage.objects.filter(is_read=False).count()
        if unread_messages > 0:
            alerts.append({
                'type': 'info',
                'title': f'{unread_messages} رسالة غير مقروءة',
                'action': '/admin/core/contactmessage/?is_read__exact=0',
                'icon': 'bi-envelope'
            })
        
        # محتوى غير منشور
        unpublished_items = PlaylistItem.objects.filter(is_published=False).count()
        if unpublished_items > 0:
            alerts.append({
                'type': 'secondary',
                'title': f'{unpublished_items} عنصر غير منشور',
                'action': '/admin/content/playlistitem/?is_published__exact=0',
                'icon': 'bi-eye-slash'
            })
        
        # فحص التحديثات المطلوبة
        outdated_items = PlaylistItem.objects.filter(
            updated_at__lt=timezone.now() - timedelta(days=30),
            youtube_url__isnull=False
        ).exclude(youtube_url='').count()
        
        if outdated_items > 0:
            alerts.append({
                'type': 'primary',
                'title': f'{outdated_items} عنصر يحتاج تحديث معلومات',
                'action': '/admin/content/sync-media/',
                'icon': 'bi-arrow-repeat'
            })
        
        return alerts
    
    def get_system_info(self):
        """معلومات النظام"""
        import django
        import sys
        from django.conf import settings
        
        return {
            'django_version': django.get_version(),
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'debug_mode': settings.DEBUG,
            'database': settings.DATABASES['default']['ENGINE'].split('.')[-1],
            'media_url': settings.MEDIA_URL,
            'static_url': settings.STATIC_URL,
            'timezone': str(timezone.get_current_timezone()),
            'server_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        }


@method_decorator([login_required, staff_member_required], name='dispatch')
class AdminAnalyticsView(TemplateView):
    """صفحة التحليلات المتقدمة"""
    template_name = 'admin/dashboard/analytics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # فترة التحليل
        period = self.request.GET.get('period', '30')  # أيام
        start_date = timezone.now() - timedelta(days=int(period))
        
        context['period'] = period
        context['analytics_data'] = self.get_analytics_data(start_date)
        context['top_content'] = self.get_top_content(start_date)
        context['user_behavior'] = self.get_user_behavior(start_date)
        
        return context
    
    def get_analytics_data(self, start_date):
        """بيانات التحليلات المفصلة"""
        # هنا يمكن ربط Google Analytics أو نظام تحليلات مخصص
        return {
            'page_views': self.calculate_page_views(start_date),
            'bounce_rate': self.calculate_bounce_rate(start_date),
            'session_duration': self.calculate_session_duration(start_date),
            'conversion_rate': self.calculate_conversion_rate(start_date)
        }
    
    def calculate_page_views(self, start_date):
        """حساب مشاهدات الصفحة"""
        # تطبيق بسيط، يمكن تحسينه بنظام tracking متقدم
        return PlaylistItem.objects.filter(
            created_at__gte=start_date
        ).aggregate(total=Sum('views_count'))['total'] or 0
    
    def calculate_bounce_rate(self, start_date):
        """حساب معدل الارتداد"""
        # محاكاة - في الواقع يحتاج نظام tracking
        return 45.2  # نسبة مئوية
    
    def calculate_session_duration(self, start_date):
        """حساب متوسط مدة الجلسة"""
        # محاكاة
        return "2:34"  # دقائق:ثواني
    
    def calculate_conversion_rate(self, start_date):
        """حساب معدل التحويل"""
        total_visitors = 1000  # محاكاة
        subscribers = Newsletter.objects.filter(
            subscribed_at__gte=start_date
        ).count()
        
        if total_visitors > 0:
            return round((subscribers / total_visitors) * 100, 2)
        return 0
    
    def get_top_content(self, start_date):
        """أفضل المحتوى أداءً"""
        top_items = PlaylistItem.objects.filter(
            created_at__gte=start_date,
            is_published=True
        ).order_by('-views_count')[:10]
        
        return [
            {
                'title': item.title,
                'views': item.views_count,
                'downloads': item.youtube_downloads + item.soundcloud_downloads,
                'shares': item.shares_count,
                'engagement_rate': self.calculate_engagement_rate(item)
            }
            for item in top_items
        ]
    
    def calculate_engagement_rate(self, item):
        """حساب معدل التفاعل"""
        total_interactions = (
            item.youtube_downloads + 
            item.soundcloud_downloads + 
            item.text_copies + 
            item.shares_count
        )
        
        if item.views_count > 0:
            return round((total_interactions / item.views_count) * 100, 2)
        return 0
    
    def get_user_behavior(self, start_date):
        """سلوك المستخدمين"""
        return {
            'most_active_hours': self.get_most_active_hours(),
            'popular_content_types': self.get_popular_content_types(),
            'user_flow': self.get_user_flow(),
            'device_breakdown': self.get_device_breakdown()
        }
    
    def get_most_active_hours(self):
        """أكثر الساعات نشاطاً"""
        # محاكاة - في الواقع يحتاج tracking
        return [
            {'hour': i, 'activity': abs(50 + (i-12)**2 - i*2)} 
            for i in range(24)
        ]
    
    def get_popular_content_types(self):
        """أنواع المحتوى الأكثر شعبية"""
        return PlaylistItem.objects.values('content_type').annotate(
            views=Sum('views_count')
        ).order_by('-views')
    
    def get_user_flow(self):
        """تدفق المستخدمين"""
        # محاكاة - يحتاج نظام tracking متقدم
        return {
            'entry_pages': [
                {'page': 'الرئيسية', 'percentage': 45},
                {'page': 'قوائم التشغيل', 'percentage': 30},
                {'page': 'البحث', 'percentage': 25}
            ],
            'exit_pages': [
                {'page': 'عرض العنصر', 'percentage': 40},
                {'page': 'قائمة التشغيل', 'percentage': 35},
                {'page': 'الرئيسية', 'percentage': 25}
            ]
        }
    
    def get_device_breakdown(self):
        """تقسيم الأجهزة"""
        # محاكاة
        return [
            {'device': 'الجوال', 'percentage': 65},
            {'device': 'سطح المكتب', 'percentage': 25},
            {'device': 'التابلت', 'percentage': 10}
        ]


@staff_member_required
def admin_ajax_stats(request):
    """إحصائيات AJAX للوحة التحكم"""
    if request.method == 'GET':
        stat_type = request.GET.get('type')
        
        if stat_type == 'real_time':
            # إحصائيات مباشرة (محاكاة)
            return JsonResponse({
                'online_users': 23,
                'active_sessions': 45,
                'current_views': 12,
                'server_load': 65
            })
        
        elif stat_type == 'quick_stats':
            # إحصائيات سريعة
            return JsonResponse({
                'today_views': PlaylistItem.objects.aggregate(
                    total=Sum('views_count')
                )['total'] or 0,
                'today_downloads': PlaylistItem.objects.aggregate(
                    youtube=Sum('youtube_downloads'),
                    soundcloud=Sum('soundcloud_downloads')
                ),
                'pending_comments': Comment.objects.filter(
                    is_approved=False, is_spam=False
                ).count(),
                'unread_messages': ContactMessage.objects.filter(
                    is_read=False
                ).count()
            })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


# إضافة URLs للوحة التحكم في core/urls.py
admin_dashboard_urls = [
    # لوحة التحكم الرئيسية
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    
    # التحليلات المتقدمة
    path('admin-analytics/', AdminAnalyticsView.as_view(), name='admin_analytics'),
    
    # AJAX للإحصائيات
    path('admin-ajax-stats/', admin_ajax_stats, name='admin_ajax_stats'),
]
