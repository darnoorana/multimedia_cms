# core/backup_system.py

import os
import json
import zipfile
import shutil
import tempfile
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.core import serializers
from django.apps import apps
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


class BackupManager:
    """مدير النسخ الاحتياطي والاستعادة"""
    
    def __init__(self):
        self.backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
        self.ensure_backup_directory()
    
    def ensure_backup_directory(self):
        """التأكد من وجود مجلد النسخ الاحتياطي"""
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # مجلدات فرعية
        subdirs = ['database', 'media', 'full', 'scheduled']
        for subdir in subdirs:
            os.makedirs(os.path.join(self.backup_dir, subdir), exist_ok=True)
    
    def create_full_backup(self, include_media=True, include_uploads=True):
        """إنشاء نسخة احتياطية كاملة"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'full_backup_{timestamp}'
        temp_dir = tempfile.mkdtemp()
        
        try:
            backup_info = {
                'backup_name': backup_name,
                'created_at': datetime.now().isoformat(),
                'backup_type': 'full',
                'include_media': include_media,
                'include_uploads': include_uploads,
                'django_version': self.get_django_version(),
                'database_engine': settings.DATABASES['default']['ENGINE']
            }
            
            # نسخ احتياطية لقاعدة البيانات
            db_backup_path = self.backup_database(temp_dir)
            backup_info['database_backup'] = os.path.basename(db_backup_path)
            
            # نسخ احتياطية للوسائط
            if include_media:
                media_backup_path = self.backup_media_files(temp_dir, include_uploads)
                backup_info['media_backup'] = os.path.basename(media_backup_path) if media_backup_path else None
            
            # نسخ احتياطية للإعدادات
            settings_backup_path = self.backup_settings(temp_dir)
            backup_info['settings_backup'] = os.path.basename(settings_backup_path)
            
            # حفظ معلومات النسخة الاحتياطية
            info_file = os.path.join(temp_dir, 'backup_info.json')
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, ensure_ascii=False, indent=2)
            
            # ضغط النسخة الاحتياطية
            backup_zip_path = os.path.join(self.backup_dir, 'full', f'{backup_name}.zip')
            self.create_zip_archive(temp_dir, backup_zip_path)
            
            # تنظيف الملفات المؤقتة
            shutil.rmtree(temp_dir)
            
            # تسجيل النسخة الاحتياطية
            self.log_backup(backup_info, backup_zip_path)
            
            logger.info(f'تم إنشاء نسخة احتياطية كاملة: {backup_name}')
            
            return {
                'success': True,
                'backup_name': backup_name,
                'backup_path': backup_zip_path,
                'backup_size': os.path.getsize(backup_zip_path),
                'backup_info': backup_info
            }
            
        except Exception as e:
            logger.error(f'خطأ في إنشاء النسخة الاحتياطية: {e}')
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def backup_database(self, temp_dir):
        """نسخ احتياطية لقاعدة البيانات"""
        db_backup_dir = os.path.join(temp_dir, 'database')
        os.makedirs(db_backup_dir, exist_ok=True)
        
        # الحصول على جميع النماذج
        models_to_backup = []
        
        for model in apps.get_models():
            if model._meta.app_label not in ['sessions', 'admin', 'contenttypes']:
                models_to_backup.append(model)
        
        # تسلسل البيانات
        backup_data = {}
        
        for model in models_to_backup:
            model_name = f"{model._meta.app_label}.{model._meta.model_name}"
            
            try:
                queryset = model.objects.all()
                serialized_data = serializers.serialize('json', queryset)
                backup_data[model_name] = json.loads(serialized_data)
                
                logger.info(f'تم نسخ {len(backup_data[model_name])} سrecorded من {model_name}')
                
            except Exception as e:
                logger.error(f'خطأ في نسخ النموذج {model_name}: {e}')
                backup_data[model_name] = []
        
        # حفظ البيانات
        db_file = os.path.join(db_backup_dir, 'database_dump.json')
        with open(db_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        # إنشاء فهرس البيانات
        index_file = os.path.join(db_backup_dir, 'database_index.json')
        database_index = {
            'created_at': datetime.now().isoformat(),
            'total_models': len(backup_data),
            'total_records': sum(len(data) for data in backup_data.values()),
            'models': {
                model_name: len(data) 
                for model_name, data in backup_data.items()
            }
        }
        
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(database_index, f, ensure_ascii=False, indent=2)
        
        return db_file
    
    def backup_media_files(self, temp_dir, include_uploads=True):
        """نسخ احتياطية للوسائط"""
        media_backup_dir = os.path.join(temp_dir, 'media')
        os.makedirs(media_backup_dir, exist_ok=True)
        
        # مجلدات الوسائط للنسخ
        media_dirs = []
        
        if include_uploads:
            media_dirs.extend([
                'uploads',
                'youtube_thumbnails', 
                'soundcloud_artworks',
                'generated'
            ])
        
        # إضافة مجلدات أساسية
        media_dirs.extend([
            'site',  # شعارات الموقع
            'categories',  # صور التصنيفات
            'playlists',  # صور قوائم التشغيل
        ])
        
        backed_up_files = []
        total_size = 0
        
        for media_dir in media_dirs:
            source_dir = os.path.join(settings.MEDIA_ROOT, media_dir)
            
            if os.path.exists(source_dir):
                target_dir = os.path.join(media_backup_dir, media_dir)
                
                try:
                    shutil.copytree(source_dir, target_dir)
                    
                    # حساب حجم المجلد
                    dir_size = self.get_directory_size(target_dir)
                    total_size += dir_size
                    
                    backed_up_files.append({
                        'directory': media_dir,
                        'files_count': self.count_files_in_directory(target_dir),
                        'size': dir_size
                    })
                    
                    logger.info(f'تم نسخ مجلد الوسائط: {media_dir}')
                    
                except Exception as e:
                    logger.error(f'خطأ في نسخ مجلد {media_dir}: {e}')
        
        # إنشاء فهرس الوسائط
        media_index = {
            'created_at': datetime.now().isoformat(),
            'total_directories': len(backed_up_files),
            'total_files': sum(item['files_count'] for item in backed_up_files),
            'total_size': total_size,
            'directories': backed_up_files
        }
        
        index_file = os.path.join(media_backup_dir, 'media_index.json')
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(media_index, f, ensure_ascii=False, indent=2)
        
        return media_backup_dir if backed_up_files else None
    
    def backup_settings(self, temp_dir):
        """نسخ احتياطية للإعدادات"""
        settings_backup_dir = os.path.join(temp_dir, 'settings')
        os.makedirs(settings_backup_dir, exist_ok=True)
        
        # إعدادات Django
        django_settings = {
            'SECRET_KEY': '***HIDDEN***',  # لا نحفظ المفتاح السري
            'DEBUG': settings.DEBUG,
            'ALLOWED_HOSTS': settings.ALLOWED_HOSTS,
            'DATABASES': {
                'default': {
                    'ENGINE': settings.DATABASES['default']['ENGINE'],
                    'NAME': settings.DATABASES['default']['NAME']
                }
            },
            'INSTALLED_APPS': settings.INSTALLED_APPS,
            'MIDDLEWARE': settings.MIDDLEWARE,
            'TIME_ZONE': settings.TIME_ZONE,
            'LANGUAGE_CODE': settings.LANGUAGE_CODE,
            'STATIC_URL': settings.STATIC_URL,
            'MEDIA_URL': settings.MEDIA_URL
        }
        
        settings_file = os.path.join(settings_backup_dir, 'django_settings.json')
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(django_settings, f, ensure_ascii=False, indent=2)
        
        # إعدادات الموقع من قاعدة البيانات
        try:
            from core.models import SiteSettings
            site_settings = SiteSettings.get_settings()
            
            site_config = {
                'site_name': site_settings.site_name,
                'site_description': site_settings.site_description,
                'contact_email': site_settings.contact_email,
                'contact_phone': site_settings.contact_phone,
                'meta_keywords': site_settings.meta_keywords,
                'newsletter_enabled': site_settings.newsletter_enabled,
                'rss_enabled': site_settings.rss_enabled,
                # لا نحفظ مفاتيح API لأسباب أمنية
                'social_media': {
                    'facebook_url': site_settings.facebook_url,
                    'twitter_url': site_settings.twitter_url,
                    'youtube_url': site_settings.youtube_url,
                    'instagram_url': site_settings.instagram_url,
                    'telegram_url': site_settings.telegram_url,
                    'soundcloud_url': site_settings.soundcloud_url,
                    'tiktok_url': site_settings.tiktok_url
                }
            }
            
            site_settings_file = os.path.join(settings_backup_dir, 'site_settings.json')
            with open(site_settings_file, 'w', encoding='utf-8') as f:
                json.dump(site_config, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f'خطأ في نسخ إعدادات الموقع: {e}')
        
        return settings_file
    
    def create_zip_archive(self, source_dir, output_path):
        """إنشاء أرشيف مضغوط"""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arc_name)
    
    def restore_from_backup(self, backup_path, restore_media=True, restore_database=True):
        """استعادة من نسخة احتياطية"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # استخراج النسخة الاحتياطية
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # قراءة معلومات النسخة الاحتياطية
            info_file = os.path.join(temp_dir, 'backup_info.json')
            if not os.path.exists(info_file):
                raise Exception('ملف معلومات النسخة الاحتياطية غير موجود')
            
            with open(info_file, 'r', encoding='utf-8') as f:
                backup_info = json.load(f)
            
            logger.info(f'بدء استعادة النسخة الاحتياطية: {backup_info["backup_name"]}')
            
            # استعادة قاعدة البيانات
            if restore_database:
                db_dir = os.path.join(temp_dir, 'database')
                if os.path.exists(db_dir):
                    self.restore_database(db_dir)
                else:
                    logger.warning('مجلد قاعدة البيانات غير موجود في النسخة الاحتياطية')
            
            # استعادة الوسائط
            if restore_media:
                media_dir = os.path.join(temp_dir, 'media')
                if os.path.exists(media_dir):
                    self.restore_media_files(media_dir)
                else:
                    logger.warning('مجلد الوسائط غير موجود في النسخة الاحتياطية')
            
            # استعادة الإعدادات
            settings_dir = os.path.join(temp_dir, 'settings')
            if os.path.exists(settings_dir):
                self.restore_settings(settings_dir)
            
            # تنظيف الملفات المؤقتة
            shutil.rmtree(temp_dir)
            
            logger.info('تمت الاستعادة بنجاح')
            
            return {
                'success': True,
                'backup_info': backup_info,
                'message': 'تمت الاستعادة بنجاح'
            }
            
        except Exception as e:
            logger.error(f'خطأ في الاستعادة: {e}')
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def restore_database(self, db_dir):
        """استعادة قاعدة البيانات"""
        db_file = os.path.join(db_dir, 'database_dump.json')
        
        if not os.path.exists(db_file):
            raise Exception('ملف قاعدة البيانات غير موجود')
        
        with open(db_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        # استعادة البيانات مع transaction
        with transaction.atomic():
            # تنظيف قاعدة البيانات الحالية (اختياري وخطر)
            # يمكن إضافة خيار للمستخدم
            
            for model_name, records in backup_data.items():
                if not records:
                    continue
                
                try:
                    app_label, model_class_name = model_name.split('.')
                    model_class = apps.get_model(app_label, model_class_name)
                    
                    # تحويل البيانات من تنسيق التسلسل
                    objects_to_create = []
                    for record_data in records:
                        # استخراج البيانات من تنسيق Django serializer
                        field_data = record_data['fields']
                        pk = record_data['pk']
                        
                        # إنشاء الكائن
                        obj = model_class(pk=pk, **field_data)
                        objects_to_create.append(obj)
                    
                    # حفظ مجمع للكائنات
                    if objects_to_create:
                        model_class.objects.bulk_create(
                            objects_to_create, 
                            ignore_conflicts=True
                        )
                        
                        logger.info(f'تم استعادة {len(objects_to_create)} record من {model_name}')
                
                except Exception as e:
                    logger.error(f'خطأ في استعادة النموذج {model_name}: {e}')
                    # نواصل مع النماذج الأخرى
    
    def restore_media_files(self, media_dir):
        """استعادة ملفات الوسائط"""
        # قراءة فهرس الوسائط
        index_file = os.path.join(media_dir, 'media_index.json')
        
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                media_index = json.load(f)
            
            logger.info(f'بدء استعادة {media_index["total_files"]} ملف وسائط')
        
        # نسخ ملفات الوسائط
        for item in os.listdir(media_dir):
            if item == 'media_index.json':
                continue
                
            source_path = os.path.join(media_dir, item)
            target_path = os.path.join(settings.MEDIA_ROOT, item)
            
            try:
                if os.path.isdir(source_path):
                    # حذف المجلد الهدف إذا كان موجوداً
                    if os.path.exists(target_path):
                        shutil.rmtree(target_path)
                    
                    shutil.copytree(source_path, target_path)
                    logger.info(f'تم استعادة مجلد الوسائط: {item}')
                else:
                    shutil.copy2(source_path, target_path)
                    logger.info(f'تم استعادة ملف الوسائط: {item}')
                    
            except Exception as e:
                logger.error(f'خطأ في استعادة {item}: {e}')
    
    def restore_settings(self, settings_dir):
        """استعادة الإعدادات"""
        site_settings_file = os.path.join(settings_dir, 'site_settings.json')
        
        if os.path.exists(site_settings_file):
            try:
                with open(site_settings_file, 'r', encoding='utf-8') as f:
                    site_config = json.load(f)
                
                # تحديث إعدادات الموقع
                from core.models import SiteSettings
                site_settings = SiteSettings.get_settings()
                
                # تحديث الحقول
                for key, value in site_config.items():
                    if key == 'social_media':
                        # تحديث روابط وسائل التواصل
                        for social_key, social_value in value.items():
                            setattr(site_settings, social_key, social_value)
                    else:
                        setattr(site_settings, key, value)
                
                site_settings.save()
                logger.info('تم استعادة إعدادات الموقع')
                
            except Exception as e:
                logger.error(f'خطأ في استعادة إعدادات الموقع: {e}')
    
    def list_backups(self):
        """قائمة النسخ الاحتياطية المتاحة"""
        backups = []
        
        for backup_type in ['full', 'database', 'media']:
            backup_type_dir = os.path.join(self.backup_dir, backup_type)
            
            if os.path.exists(backup_type_dir):
                for backup_file in os.listdir(backup_type_dir):
                    if backup_file.endswith('.zip'):
                        backup_path = os.path.join(backup_type_dir, backup_file)
                        backup_stat = os.stat(backup_path)
                        
                        backups.append({
                            'name': backup_file,
                            'type': backup_type,
                            'path': backup_path,
                            'size': backup_stat.st_size,
                            'created_at': datetime.fromtimestamp(backup_stat.st_ctime),
                            'modified_at': datetime.fromtimestamp(backup_stat.st_mtime)
                        })
        
        # ترتيب حسب تاريخ الإنشاء
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        
        return backups
    
    def delete_backup(self, backup_path):
        """حذف نسخة احتياطية"""
        try:
            if os.path.exists(backup_path):
                os.remove(backup_path)
                logger.info(f'تم حذف النسخة الاحتياطية: {backup_path}')
                return True
            else:
                logger.error(f'النسخة الاحتياطية غير موجودة: {backup_path}')
                return False
        except Exception as e:
            logger.error(f'خطأ في حذف النسخة الاحتياطية: {e}')
            return False
    
    def cleanup_old_backups(self, keep_days=30, keep_count=10):
        """تنظيف النسخ الاحتياطية القديمة"""
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        backups = self.list_backups()
        
        deleted_count = 0
        kept_recent = 0
        
        for backup in backups:
            # الاحتفاظ بالنسخ الحديثة
            if kept_recent < keep_count:
                kept_recent += 1
                continue
            
            # حذف النسخ القديمة
            if backup['created_at'] < cutoff_date:
                if self.delete_backup(backup['path']):
                    deleted_count += 1
        
        logger.info(f'تم حذف {deleted_count} نسخة احتياطية قديمة')
        return deleted_count
    
    def log_backup(self, backup_info, backup_path):
        """تسجيل النسخة الاحتياطية"""
        log_file = os.path.join(self.backup_dir, 'backup_log.json')
        
        log_entry = {
            **backup_info,
            'backup_path': backup_path,
            'file_size': os.path.getsize(backup_path)
        }
        
        # قراءة السجل الحالي
        log_data = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
            except:
                log_data = []
        
        # إضافة السجل الجديد
        log_data.append(log_entry)
        
        # الاحتفاظ بآخر 100 سجل فقط
        log_data = log_data[-100:]
        
        # حفظ السجل
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
    
    def get_django_version(self):
        """الحصول على إصدار Django"""
        import django
        return django.get_version()
    
    def get_directory_size(self, directory):
        """حساب حجم المجلد"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size
    
    def count_files_in_directory(self, directory):
        """عدد الملفات في المجلد"""
        file_count = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            file_count += len(filenames)
        return file_count


# === Management Commands ===

class BackupCommand(BaseCommand):
    help = 'إنشاء نسخة احتياطية من النظام'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            choices=['full', 'database', 'media'],
            default='full',
            help='نوع النسخة الاحتياطية'
        )
        
        parser.add_argument(
            '--no-media',
            action='store_true',
            help='استبعاد ملفات الوسائط'
        )
        
        parser.add_argument(
            '--no-uploads',
            action='store_true',
            help='استبعاد ملفات الرفع'
        )
    
    def handle(self, *args, **options):
        backup_manager = BackupManager()
        
        self.stdout.write('بدء إنشاء النسخة الاحتياطية...')
        
        backup_type = options['type']
        include_media = not options['no_media']
        include_uploads = not options['no_uploads']
        
        if backup_type == 'full':
            result = backup_manager.create_full_backup(include_media, include_uploads)
        elif backup_type == 'database':
            # يمكن إضافة نسخة احتياطية لقاعدة البيانات فقط
            result = backup_manager.create_database_only_backup()
        elif backup_type == 'media':
            # يمكن إضافة نسخة احتياطية للوسائط فقط
            result = backup_manager.create_media_only_backup(include_uploads)
        
        if result['success']:
            self.stdout.write(
                self.style.SUCCESS(f'تم إنشاء النسخة الاحتياطية: {result["backup_name"]}')
            )
            self.stdout.write(f'المسار: {result["backup_path"]}')
            self.stdout.write(f'الحجم: {self.format_size(result["backup_size"])}')
        else:
            self.stdout.write(
                self.style.ERROR(f'فشل في إنشاء النسخة الاحتياطية: {result["error"]}')
            )
    
    def format_size(self, size_bytes):
        """تنسيق حجم الملف"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


class RestoreCommand(BaseCommand):
    help = 'استعادة من نسخة احتياطية'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'backup_path',
            help='مسار النسخة الاحتياطية'
        )
        
        parser.add_argument(
            '--no-database',
            action='store_true',
            help='عدم استعادة قاعدة البيانات'
        )
        
        parser.add_argument(
            '--no-media',
            action='store_true',
            help='عدم استعادة ملفات الوسائط'
        )
        
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='تأكيد الاستعادة بدون سؤال'
        )
    
    def handle(self, *args, **options):
        backup_path = options['backup_path']
        
        if not os.path.exists(backup_path):
            self.stdout.write(
                self.style.ERROR(f'النسخة الاحتياطية غير موجودة: {backup_path}')
            )
            return
        
        if not options['confirm']:
            confirm = input('هل أنت متأكد من الاستعادة؟ (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('تم إلغاء الاستعادة')
                return
        
        backup_manager = BackupManager()
        
        self.stdout.write('بدء الاستعادة...')
        
        restore_database = not options['no_database']
        restore_media = not options['no_media']
        
        result = backup_manager.restore_from_backup(
            backup_path, 
            restore_media, 
            restore_database
        )
        
        if result['success']:
            self.stdout.write(
                self.style.SUCCESS('تمت الاستعادة بنجاح!')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'فشل في الاستعادة: {result["error"]}')
            )


class CleanupBackupsCommand(BaseCommand):
    help = 'تنظيف النسخ الاحتياطية القديمة'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='حذف النسخ الأقدم من هذا العدد من الأيام'
        )
        
        parser.add_argument(
            '--keep',
            type=int,
            default=10,
            help='الاحتفاظ بهذا العدد من النسخ الحديثة'
        )
    
    def handle(self, *args, **options):
        backup_manager = BackupManager()
        
        keep_days = options['days']
        keep_count = options['keep']
        
        self.stdout.write(f'تنظيف النسخ الأقدم من {keep_days} يوم...')
        self.stdout.write(f'الاحتفاظ بـ {keep_count} نسخة حديثة...')
        
        deleted_count = backup_manager.cleanup_old_backups(keep_days, keep_count)
        
        self.stdout.write(
            self.style.SUCCESS(f'تم حذف {deleted_count} نسخة احتياطية قديمة')
        )
