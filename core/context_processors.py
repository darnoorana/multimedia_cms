

# core/context_processors.py - تحديث

from .models import SiteSettings, Advertisement, Category
from content.models import Playlist

def site_settings(request):
    """إضافة إعدادات الموقع إلى جميع القوالب"""
    return {
        'site_settings': SiteSettings.get_settings(),
    }

def navigation_data(request):
    """إضافة بيانات التنقل إلى جميع القوالب"""
    return {
        'nav_categories': Category.objects.filter(is_active=True).order_by('order', 'name')[:8],
        'nav_recent_playlists': Playlist.objects.filter(is_published=True).order_by('-created_at')[:5],
    }

def ads_context(request):
    """إضافة الإعلانات إلى السياق"""
    from django.utils import timezone
    from django.db.models import Q
    
    now = timezone.now()
    
    # إعلانات مفعلة وضمن الفترة الزمنية المحددة
    ads_query = Advertisement.objects.filter(
        is_active=True
    ).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=now)
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=now)
    )
    
    return {
        'header_ads': ads_query.filter(placement='header').order_by('order'),
        'sidebar_ads': ads_query.filter(placement='sidebar').order_by('order'),
        'footer_ads': ads_query.filter(placement='footer').order_by('order'),
        'content_top_ads': ads_query.filter(placement='content_top').order_by('order'),
        'content_bottom_ads': ads_query.filter(placement='content_bottom').order_by('order'),
        'between_posts_ads': ads_query.filter(placement='between_posts').order_by('order'),
    }
