

# ===== ملف إعدادات إضافي: content/apps.py =====

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ContentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'content'
    verbose_name = _('المحتوى والوسائط')
    
    def ready(self):
        """تهيئة التطبيق"""
        # استيراد الإشارات
        import content.signals
        
        # تهيئة مجلدات الوسائط
        self.create_media_directories()
        
        # تسجيل المهام الدورية
        self.register_periodic_tasks()
    
    def create_media_directories(self):
        """إنشاء مجلدات الوسائط المطلوبة"""
        import os
        from django.conf import settings
        
        media_dirs = [
            'uploads/videos',
            'uploads/audios', 
            'uploads/images',
            'uploads/videos/thumbnails',
            'uploads/audios/waveforms',
            'downloads/youtube',
            'downloads/soundcloud',
            'youtube_thumbnails',
            'soundcloud_artworks',
            'generated/waveforms',
            'generated/thumbnails'
        ]
        
        for dir_name in media_dirs:
            dir_path = os.path.join(settings.MEDIA_ROOT, dir_name)
            os.makedirs(dir_path, exist_ok=True)
    
    def register_periodic_tasks(self):
        """تسجيل المهام الدورية مع Celery"""
        try:
            from django_celery_beat.models import PeriodicTask, IntervalSchedule
            import json
            
            # مهمة تنظيف الملفات المؤقتة (يومياً)
            schedule, created = IntervalSchedule.objects.get_or_create(
                every=1,
                period=IntervalSchedule.DAYS,
            )
            
            PeriodicTask.objects.get_or_create(
                name='تنظيف الملفات المؤقتة',
                defaults={
                    'task': 'content.tasks.cleanup_temp_files',
                    'interval': schedule,
                    'kwargs': json.dumps({'older_than_hours': 24}),
                    'enabled': True
                }
            )
            
            # مهمة مزامنة معلومات الوسائط (أسبوعياً)
            weekly_schedule, created = IntervalSchedule.objects.get_or_create(
                every=7,
                period=IntervalSchedule.DAYS,
            )
            
            PeriodicTask.objects.get_or_create(
                name='مزامنة معلومات الوسائط',
                defaults={
                    'task': 'content.tasks.sync_media_info',
                    'interval': weekly_schedule,
                    'kwargs': json.dumps({'batch_size': 10}),
                    'enabled': True
                }
            )
            
        except ImportError:
            # إذا لم يكن django-celery-beat مثبتاً
            pass
        except Exception as e:
            # تجاهل الأخطاء في وضع التطوير
            import logging
            logging.getLogger(__name__).warning(f'لا يمكن تسجيل المهام الدورية: {e}')
