# content/management/commands/sync_media_info.py

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from content.models import PlaylistItem
from content.utils.media_utils import youtube_handler, soundcloud_handler
import time
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'مزامنة معلومات الوسائط من YouTube و SoundCloud'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--playlist-id',
            type=int,
            help='معرف قائمة تشغيل محددة للمزامنة'
        )
        
        parser.add_argument(
            '--item-id',
            type=int,
            help='معرف عنصر محدد للمزامنة'
        )
        
        parser.add_argument(
            '--type',
            choices=['youtube', 'soundcloud', 'all'],
            default='all',
            help='نوع الوسائط للمزامنة'
        )
        
        parser.add_argument(
            '--update-thumbnails',
            action='store_true',
            help='تحديث الصور المصغرة'
        )
        
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='عدد العناصر في كل دفعة'
        )
        
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='التأخير بين الطلبات (بالثواني)'
        )
    
    def handle(self, *args, **options):
        self.verbosity = options['verbosity']
        self.delay = options['delay']
        self.update_thumbnails = options['update_thumbnails']
        
        # الحصول على العناصر للمزامنة
        items = self.get_items_to_sync(options)
        
        if not items.exists():
            self.stdout.write(
                self.style.WARNING('لا توجد عناصر للمزامنة')
            )
            return
        
        total_items = items.count()
        self.stdout.write(
            self.style.SUCCESS(f'بدء مزامنة {total_items} عنصر...')
        )
        
        # معالجة العناصر في دفعات
        batch_size = options['batch_size']
        updated_count = 0
        error_count = 0
        
        for i in range(0, total_items, batch_size):
            batch = items[i:i + batch_size]
            
            for item in batch:
                try:
                    updated = self.sync_item(item, options['type'])
                    if updated:
                        updated_count += 1
                    
                    # تأخير لتجنب rate limiting
                    if self.delay > 0:
                        time.sleep(self.delay)
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f'خطأ في مزامنة العنصر {item.id}: {e}')
                    
                    if self.verbosity >= 2:
                        self.stdout.write(
                            self.style.ERROR(f'خطأ في {item.title}: {e}')
                        )
            
            # عرض التقدم
            processed = min(i + batch_size, total_items)
            self.stdout.write(
                f'تم معالجة {processed}/{total_items} عنصر...'
            )
        
        # النتائج النهائية
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(f'تم تحديث {updated_count} عنصر بنجاح')
        )
        
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f'فشل في تحديث {error_count} عنصر')
            )
        
        self.stdout.write(
            f'إجمالي العناصر المعالجة: {total_items}'
        )
    
    def get_items_to_sync(self, options):
        """الحصول على العناصر المراد مزامنتها"""
        queryset = PlaylistItem.objects.all()
        
        # فلترة حسب قائمة التشغيل
        if options['playlist_id']:
            queryset = queryset.filter(playlist_id=options['playlist_id'])
        
        # فلترة حسب العنصر المحدد
        if options['item_id']:
            queryset = queryset.filter(id=options['item_id'])
        
        # فلترة حسب نوع الوسائط
        media_type = options['type']
        if media_type == 'youtube':
            queryset = queryset.exclude(youtube_url='')
        elif media_type == 'soundcloud':
            queryset = queryset.exclude(soundcloud_url='')
        else:  # all
            from django.db.models import Q
            queryset = queryset.filter(
                Q(youtube_url__isnull=False, youtube_url__gt='') |
                Q(soundcloud_url__isnull=False, soundcloud_url__gt='')
            )
        
        return queryset.select_related('playlist')
    
    def sync_item(self, item, media_type='all'):
        """مزامنة عنصر واحد"""
        updated = False
        
        # مزامنة YouTube
        if (media_type in ['youtube', 'all']) and item.youtube_url:
            if self.sync_youtube_item(item):
                updated = True
        
        # مزامنة SoundCloud
        if (media_type in ['soundcloud', 'all']) and item.soundcloud_url:
            if self.sync_soundcloud_item(item):
                updated = True
        
        if updated:
            item.save()
            
            if self.verbosity >= 2:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ تم تحديث: {item.title}')
                )
        
        return updated
    
    def sync_youtube_item(self, item):
        """مزامنة عنصر YouTube"""
        try:
            if not item.youtube_video_id:
                # استخراج معرف الفيديو إذا لم يكن موجوداً
                video_id = youtube_handler.extract_video_id(item.youtube_url)
                if video_id:
                    item.youtube_video_id = video_id
                else:
                    return False
            
            # الحصول على معلومات الفيديو
            info = youtube_handler.get_video_info(item.youtube_video_id)
            
            if not info:
                if self.verbosity >= 2:
                    self.stdout.write(
                        self.style.WARNING(f'لا يمكن الحصول على معلومات YouTube لـ: {item.title}')
                    )
                return False
            
            updated = False
            
            # تحديث المعلومات إذا كانت فارغة أو قديمة
            if not item.title or item.title.startswith('فيديو YouTube'):
                item.title = info['title']
                updated = True
            
            if not item.content_text and info.get('description'):
                item.content_text = info['description'][:1000]  # الحد الأقصى
                updated = True
            
            # تحديث أو تحميل الصورة المصغرة
            if self.update_thumbnails and (not item.thumbnail or not item.thumbnail.name):
                thumbnail_path = youtube_handler.download_thumbnail(
                    item.youtube_video_id, 
                    f'youtube_{item.youtube_video_id}'
                )
                
                if thumbnail_path:
                    item.thumbnail = thumbnail_path
                    updated = True
            
            return updated
            
        except Exception as e:
            logger.error(f'خطأ في مزامنة YouTube للعنصر {item.id}: {e}')
            return False
    
    def sync_soundcloud_item(self, item):
        """مزامنة عنصر SoundCloud"""
        try:
            # الحصول على معلومات المقطع
            info = soundcloud_handler.extract_track_info(item.soundcloud_url)
            
            if not info:
                if self.verbosity >= 2:
                    self.stdout.write(
                        self.style.WARNING(f'لا يمكن الحصول على معلومات SoundCloud لـ: {item.title}')
                    )
                return False
            
            updated = False
            
            # تحديث المعلومات
            if not item.title or 'مقطع SoundCloud' in item.title:
                item.title = info['title']
                updated = True
            
            if not item.content_text and info.get('description'):
                item.content_text = info['description'][:1000]
                updated = True
            
            if not item.soundcloud_track_id and info.get('id'):
                item.soundcloud_track_id = str(info['id'])
                updated = True
            
            # تحديث الصورة المصغرة
            if self.update_thumbnails and (not item.thumbnail or not item.thumbnail.name):
                if info.get('artwork_url'):
                    artwork_path = soundcloud_handler.download_artwork(
                        info['artwork_url'],
                        f'soundcloud_{info.get("id", item.id)}'
                    )
                    
                    if artwork_path:
                        item.thumbnail = artwork_path
                        updated = True
            
            return updated
            
        except Exception as e:
            logger.error(f'خطأ في مزامنة SoundCloud للعنصر {item.id}: {e}')
            return False


# content/management/commands/generate_thumbnails.py

from django.core.management.base import BaseCommand
from django.core.files import File
from content.models import PlaylistItem
from content.utils.media_utils import media_processor
import os
import tempfile
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'إنشاء صور مصغرة للوسائط المحلية'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--regenerate',
            action='store_true',
            help='إعادة إنشاء الصور الموجودة'
        )
        
        parser.add_argument(
            '--video-timestamp',
            default='00:00:05',
            help='الوقت لاستخراج الصورة من الفيديو'
        )
    
    def handle(self, *args, **options):
        regenerate = options['regenerate']
        timestamp = options['video_timestamp']
        
        # العناصر التي تحتاج صور مصغرة
        items = PlaylistItem.objects.filter(
            content_type__in=['youtube', 'soundcloud', 'mixed']
        )
        
        if not regenerate:
            items = items.filter(thumbnail='')
        
        total_items = items.count()
        
        if total_items == 0:
            self.stdout.write(
                self.style.WARNING('لا توجد عناصر تحتاج صور مصغرة')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'بدء إنشاء {total_items} صورة مصغرة...')
        )
        
        success_count = 0
        error_count = 0
        
        for item in items:
            try:
                if self.generate_thumbnail(item, timestamp):
                    success_count += 1
                    
                    if options['verbosity'] >= 2:
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ {item.title}')
                        )
                else:
                    error_count += 1
                    
            except Exception as e:
                error_count += 1
                logger.error(f'خطأ في إنشاء صورة مصغرة للعنصر {item.id}: {e}')
        
        # النتائج
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(f'تم إنشاء {success_count} صورة مصغرة بنجاح')
        )
        
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f'فشل في إنشاء {error_count} صورة')
            )
    
    def generate_thumbnail(self, item, timestamp):
        """إنشاء صورة مصغرة لعنصر"""
        thumbnail_generated = False
        
        # إنشاء صورة مصغرة من YouTube
        if item.youtube_video_id and not thumbnail_generated:
            try:
                from content.utils.media_utils import youtube_handler
                
                thumbnail_path = youtube_handler.download_thumbnail(
                    item.youtube_video_id,
                    f'auto_youtube_{item.youtube_video_id}'
                )
                
                if thumbnail_path:
                    item.thumbnail = thumbnail_path
                    item.save()
                    thumbnail_generated = True
                    
            except Exception as e:
                logger.error(f'خطأ في تحميل صورة YouTube: {e}')
        
        # إنشاء صورة مصغرة من SoundCloud
        if item.soundcloud_url and not thumbnail_generated:
            try:
                from content.utils.media_utils import soundcloud_handler
                
                info = soundcloud_handler.extract_track_info(item.soundcloud_url)
                
                if info and info.get('artwork_url'):
                    artwork_path = soundcloud_handler.download_artwork(
                        info['artwork_url'],
                        f'auto_soundcloud_{item.id}'
                    )
                    
                    if artwork_path:
                        item.thumbnail = artwork_path
                        item.save()
                        thumbnail_generated = True
                        
            except Exception as e:
                logger.error(f'خطأ في تحميل صورة SoundCloud: {e}')
        
        return thumbnail_generated


# content/management/commands/cleanup_media.py

from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from content.models import PlaylistItem
import os
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'تنظيف الملفات الغير مستخدمة'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض الملفات فقط بدون حذف'
        )
        
        parser.add_argument(
            '--older-than',
            type=int,
            default=30,
            help='حذف الملفات الأقدم من عدد الأيام المحدد'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        older_than_days = options['older_than']
        
        self.stdout.write('بحث عن الملفات الغير مستخدمة...')
        
        # البحث عن الصور المصغرة الغير مستخدمة
        unused_thumbnails = self.find_unused_thumbnails()
        
        # البحث عن ملفات التحميل القديمة
        old_downloads = self.find_old_downloads(older_than_days)
        
        total_files = len(unused_thumbnails) + len(old_downloads)
        
        if total_files == 0:
            self.stdout.write(
                self.style.SUCCESS('لا توجد ملفات للتنظيف')
            )
            return
        
        self.stdout.write(
            f'تم العثور على {total_files} ملف للتنظيف:'
        )
        self.stdout.write(f'  - {len(unused_thumbnails)} صورة مصغرة غير مستخدمة')
        self.stdout.write(f'  - {len(old_downloads)} ملف تحميل قديم')
        
        if dry_run:
            self.stdout.write('\n--- الملفات التي سيتم حذفها (وضع الاختبار) ---')
            
            for file_path in unused_thumbnails:
                self.stdout.write(f'  صورة: {file_path}')
            
            for file_path in old_downloads:
                self.stdout.write(f'  تحميل: {file_path}')
                
            self.stdout.write('\nلتنفيذ الحذف الفعلي، استخدم الأمر بدون --dry-run')
            return
        
        # تنفيذ الحذف
        deleted_count = 0
        
        for file_path in unused_thumbnails + old_downloads:
            try:
                if default_storage.exists(file_path):
                    default_storage.delete(file_path)
                    deleted_count += 1
                    
            except Exception as e:
                logger.error(f'خطأ في حذف الملف {file_path}: {e}')
        
        self.stdout.write(
            self.style.SUCCESS(f'تم حذف {deleted_count} ملف بنجاح')
        )
    
    def find_unused_thumbnails(self):
        """البحث عن الصور المصغرة الغير مستخدمة"""
        unused_files = []
        
        try:
            # مسارات الصور المصغرة
            thumbnail_dirs = [
                'youtube_thumbnails',
                'soundcloud_artworks',
                'playlist_items'
            ]
            
            for dir_name in thumbnail_dirs:
                if default_storage.exists(dir_name):
                    files = default_storage.listdir(dir_name)[1]  # الملفات فقط
                    
                    for filename in files:
                        file_path = f'{dir_name}/{filename}'
                        
                        # التحقق من استخدام الملف
                        if not self.is_thumbnail_used(file_path):
                            unused_files.append(file_path)
                            
        except Exception as e:
            logger.error(f'خطأ في البحث عن الصور الغير مستخدمة: {e}')
        
        return unused_files
    
    def find_old_downloads(self, days):
        """البحث عن ملفات التحميل القديمة"""
        from datetime import datetime, timedelta
        
        old_files = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            download_dirs = ['downloads/youtube', 'downloads/soundcloud']
            
            for dir_name in download_dirs:
                if default_storage.exists(dir_name):
                    files = default_storage.listdir(dir_name)[1]
                    
                    for filename in files:
                        file_path = f'{dir_name}/{filename}'
                        
                        try:
                            # التحقق من تاريخ الملف
                            file_time = default_storage.get_modified_time(file_path)
                            
                            if file_time < cutoff_date:
                                old_files.append(file_path)
                                
                        except Exception:
                            # إذا فشل في الحصول على التاريخ، أضفه للقائمة
                            old_files.append(file_path)
                            
        except Exception as e:
            logger.error(f'خطأ في البحث عن الملفات القديمة: {e}')
        
        return old_files
    
    def is_thumbnail_used(self, file_path):
        """التحقق من استخدام الصورة المصغرة"""
        try:
            # البحث في قواعد البيانات
            filename = os.path.basename(file_path)
            
            used_in_items = PlaylistItem.objects.filter(
                thumbnail__contains=filename
            ).exists()
            
            # يمكن إضافة المزيد من الفحوصات هنا
            
            return used_in_items
            
        except Exception as e:
            logger.error(f'خطأ في فحص استخدام الملف {file_path}: {e}')
            return True  # احتياطي: لا تحذف إذا لم تتأكد
