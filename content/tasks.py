

# ===== ملف المهام: content/tasks.py =====

from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def sync_media_info(self, batch_size=50, media_type='all'):
    """مهمة مزامنة معلومات الوسائط في الخلفية"""
    try:
        call_command(
            'sync_media_info',
            batch_size=batch_size,
            type=media_type,
            verbosity=1
        )
        
        logger.info('تمت مزامنة معلومات الوسائط بنجاح')
        return {'status': 'success', 'message': 'تمت المزامنة بنجاح'}
        
    except Exception as e:
        logger.error(f'خطأ في مزامنة معلومات الوسائط: {e}')
        raise self.retry(exc=e, countdown=60, max_retries=3)


@shared_task(bind=True)  
def generate_thumbnails(self, regenerate=False):
    """مهمة إنشاء الصور المصغرة في الخلفية"""
    try:
        args = ['generate_thumbnails']
        if regenerate:
            args.append('--regenerate')
            
        call_command(*args, verbosity=1)
        
        logger.info('تم إنشاء الصور المصغرة بنجاح')
        return {'status': 'success', 'message': 'تم إنشاء الصور بنجاح'}
        
    except Exception as e:
        logger.error(f'خطأ في إنشاء الصور المصغرة: {e}')
        raise self.retry(exc=e, countdown=60, max_retries=3)


@shared_task
def cleanup_temp_files(older_than_hours=24):
    """مهمة تنظيف الملفات المؤقتة"""
    try:
        from django.core.files.storage import default_storage
        from datetime import datetime, timedelta
        import os
        
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        temp_dirs = ['temp', 'cache', 'downloads']
        
        deleted_count = 0
        
        for temp_dir in temp_dirs:
            if default_storage.exists(temp_dir):
                try:
                    files = default_storage.listdir(temp_dir)[1]
                    
                    for filename in files:
                        file_path = f'{temp_dir}/{filename}'
                        
                        try:
                            file_time = default_storage.get_modified_time(file_path)
                            
                            if file_time < cutoff_time:
                                default_storage.delete(file_path)
                                deleted_count += 1
                                
                        except Exception:
                            continue
                            
                except Exception as e:
                    logger.error(f'خطأ في تنظيف مجلد {temp_dir}: {e}')
        
        logger.info(f'تم حذف {deleted_count} ملف مؤقت')
        return {'status': 'success', 'deleted_files': deleted_count}
        
    except Exception as e:
        logger.error(f'خطأ في تنظيف الملفات المؤقتة: {e}')
        return
