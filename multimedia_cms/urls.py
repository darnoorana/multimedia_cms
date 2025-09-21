"""
URL configuration for multimedia_cms project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))

from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
]

"""
# multimedia_cms/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import gettext_lazy as _

# URLs غير متعددة اللغات (للـ API وملفات الوسائط)
urlpatterns = [
    # API URLs
#temp    path('api/', include('content.api_urls')),  # سيتم إنشاؤها لاحقاً
    
    # AJAX URLs
#temp    path('ajax/', include('core.ajax_urls')),  # سيتم إنشاؤها لاحقاً
    
    # Sitemap والـ RSS
#temp    path('sitemap.xml', include('core.sitemap_urls')),  # سيتم إنشاؤها لاحقاً
#temp    path('rss/', include('core.rss_urls')),  # سيتم إنشاؤها لاحقاً
]

# URLs متعددة اللغات
urlpatterns += i18n_patterns(
    # لوحة الإدارة
    path('admin/', admin.site.urls),
    
    # التطبيقات الرئيسية
    path('', include('core.urls')),  # الصفحة الرئيسية وصفحات النظام
    path(_('content/'), include('content.urls')),  # قوائم التشغيل والمحتوى
    path(_('blog/'), include('blog.urls')),  # المدونة
    path(_('projects/'), include('projects.urls')),  # المشاريع
    path(_('accounts/'), include('accounts.urls')),  # حسابات المستخدمين
    
    prefix_default_language=False,  # لا نريد /ar/ في الروابط العربية
)

# إعداد ملفات الوسائط في وضع التطوير
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# تخصيص صفحات الأخطاء
handler404 = 'core.views.custom_404'
handler500 = 'core.views.custom_500'
