# core/urls.py

from django.urls import path
from django.utils.translation import gettext_lazy as _
from . import views

app_name = 'core'

urlpatterns = [
    # الصفحة الرئيسية
    path('', views.HomeView.as_view(), name='home'),
    
    # الصفحات الثابتة
    path(_('about/'), views.AboutView.as_view(), name='about'),
    path(_('contact/'), views.ContactView.as_view(), name='contact'),
    path(_('privacy/'), views.PrivacyView.as_view(), name='privacy'),
    path(_('terms/'), views.TermsView.as_view(), name='terms'),
    
    # البحث
    path(_('search/'), views.SearchView.as_view(), name='search'),
    
    # النشرة الإخبارية
    path(_('newsletter/subscribe/'), views.NewsletterSubscribeView.as_view(), name='newsletter_subscribe'),
    path(_('newsletter/unsubscribe/'), views.NewsletterUnsubscribeView.as_view(), name='newsletter_unsubscribe'),
    
    # صفحة النتائج بعد العمليات
    path(_('success/'), views.SuccessView.as_view(), name='success'),
    
    # تغيير اللغة
    path(_('language/'), views.LanguageView.as_view(), name='language'),
    
    # صفحات الأخطاء (للاختبار في وضع التطوير)
    path('404/', views.custom_404, name='404'),
    path('500/', views.custom_500, name='500'),
]
