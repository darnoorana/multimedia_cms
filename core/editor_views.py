# core/editor_views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import json
import os
import uuid
from PIL import Image
import mimetypes

from content.models import PlaylistItem
from core.models import SiteSettings


@method_decorator([login_required, staff_member_required], name='dispatch')
class MediaBrowserView(TemplateView):
    """متصفح الوسائط للمحرر"""
    template_name = 'admin/editor/media_browser.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        media_type = self.request.GET.get('type', 'all')  # all, image, video, audio, document
        page = int(self.request.GET.get('page', 1))
        per_page = 20
        
        # الحصول على الملفات
        media_files = self.get_media_files(media_type)
        
        # التصفح
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        paginated_files = media_files[start_index:end_index]
        
        # معلومات التصفح
        has_previous = page > 1
        has_next = end_index < len(media_files)
        
        context.update({
            'media_files': paginated_files,
            'media_type': media_type,
            'current_page': page,
            'has_previous': has_previous,
            'has_next': has_next,
            'previous_page': page - 1 if has_previous else None,
            'next_page': page + 1 if has_next else None,
            'total_files': len(media_files)
        })
        
        return context
    
    def get_media_files(self, media_type):
        """الحصول على ملفات الوسائط"""
        media_dirs = {
            'image': ['uploads/images', 'youtube_thumbnails', 'soundcloud_artworks'],
            'video': ['uploads/videos'],
            'audio': ['uploads/audios'],
            'document': ['uploads/documents']
        }
        
        files = []
        
        if media_type == 'all':
            search_dirs = []
            for dirs_list in media_dirs.values():
                search_dirs.extend(dirs_list)
        else:
            search_dirs = media_dirs.get(media_type, [])
        
        for directory in search_dirs:
            if default_storage.exists(directory):
                try:
                    dir_files = default_storage.listdir(directory)[1]  # الملفات فقط
                    
                    for filename in dir_files:
                        file_path = f'{directory}/{filename}'
                        
                        file_info = self.get_file_info(file_path, filename)
                        if file_info and (media_type == 'all' or self.matches_type(file_info['type'], media_type)):
                            files.append(file_info)
                            
                except Exception as e:
            return None
    
    def get_file_category(self, mime_type):
        """تحديد فئة الملف"""
        if not mime_type:
            return 'document'
        
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('video/'):
            return 'video'
        elif mime_type.startswith('audio/'):
            return 'audio'
        else:
            return 'document'
    
    def matches_type(self, file_type, requested_type):
        """التحقق من تطابق نوع الملف"""
        if requested_type == 'all':
            return True
        return file_type == requested_type
    
    def generate_thumbnail(self, file_path, file_url):
        """إنشاء صورة مصغرة"""
        try:
            # البحث عن صورة مصغرة موجودة
            thumbnail_dir = 'thumbnails'
            thumbnail_filename = f"thumb_{os.path.basename(file_path)}"
            thumbnail_path = f"{thumbnail_dir}/{thumbnail_filename}"
            
            if default_storage.exists(thumbnail_path):
                return default_storage.url(thumbnail_path)
            
            # إنشاء صورة مصغرة جديدة
            with default_storage.open(file_path, 'rb') as f:
                image = Image.open(f)
                image.thumbnail((200, 200), Image.Resampling.LANCZOS)
                
                # حفظ الصورة المصغرة
                from io import BytesIO
                thumb_io = BytesIO()
                image.save(thumb_io, format='JPEG', quality=85)
                thumb_content = ContentFile(thumb_io.getvalue())
                
                saved_path = default_storage.save(thumbnail_path, thumb_content)
                return default_storage.url(saved_path)
            
        except Exception as e:
            # في حالة فشل إنشاء الصورة المصغرة، استخدم الصورة الأصلية
            return file_url
    
    def format_file_size(self, size_bytes):
        """تنسيق حجم الملف"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


@csrf_exempt
@staff_member_required
def upload_editor_media(request):
    """رفع ملف للمحرر"""
    if request.method != 'POST':
        return JsonResponse({'error': 'طريقة غير مدعومة'}, status=405)
    
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return JsonResponse({'error': 'لم يتم اختيار ملف'}, status=400)
    
    try:
        # التحقق من نوع الملف
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'video/mp4', 'video/webm', 'video/ogg',
            'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/m4a',
            'application/pdf', 'text/plain', 'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
        
        if uploaded_file.content_type not in allowed_types:
            return JsonResponse({'error': 'نوع الملف غير مدعوم'}, status=400)
        
        # التحقق من حجم الملف
        max_size = 10 * 1024 * 1024  # 10 MB
        if uploaded_file.size > max_size:
            return JsonResponse({'error': 'حجم الملف كبير جداً'}, status=400)
        
        # تحديد مجلد الحفظ
        file_category = get_file_category_from_mime(uploaded_file.content_type)
        upload_dir = f'uploads/{file_category}s'
        
        # إنشاء اسم ملف فريد
        file_extension = os.path.splitext(uploaded_file.name)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = f"{upload_dir}/{unique_filename}"
        
        # حفظ الملف
        saved_path = default_storage.save(file_path, uploaded_file)
        file_url = default_storage.url(saved_path)
        
        # إنشاء صورة مصغرة للصور
        thumbnail_url = file_url
        if file_category == 'image':
            try:
                thumbnail_url = generate_image_thumbnail(saved_path)
            except:
                thumbnail_url = file_url
        
        return JsonResponse({
            'success': True,
            'file_url': file_url,
            'thumbnail_url': thumbnail_url,
            'filename': uploaded_file.name,
            'file_size': uploaded_file.size,
            'file_type': file_category
        })
        
    except Exception as e:
        return JsonResponse({'error': f'خطأ في رفع الملف: {str(e)}'}, status=500)


def get_file_category_from_mime(mime_type):
    """الحصول على فئة الملف من MIME type"""
    if mime_type.startswith('image/'):
        return 'image'
    elif mime_type.startswith('video/'):
        return 'video'
    elif mime_type.startswith('audio/'):
        return 'audio'
    else:
        return 'document'


def generate_image_thumbnail(image_path):
    """إنشاء صورة مصغرة للصورة"""
    try:
        thumbnail_dir = 'thumbnails'
        thumbnail_filename = f"thumb_{os.path.basename(image_path)}"
        thumbnail_path = f"{thumbnail_dir}/{thumbnail_filename}"
        
        with default_storage.open(image_path, 'rb') as f:
            image = Image.open(f)
            image.thumbnail((200, 200), Image.Resampling.LANCZOS)
            
            from io import BytesIO
            thumb_io = BytesIO()
            image.save(thumb_io, format='JPEG', quality=85)
            thumb_content = ContentFile(thumb_io.getvalue())
            
            saved_path = default_storage.save(thumbnail_path, thumb_content)
            return default_storage.url(saved_path)
    except:
        return default_storage.url(image_path)


@csrf_exempt
@staff_member_required
def delete_editor_media(request):
    """حذف ملف من المحرر"""
    if request.method != 'POST':
        return JsonResponse({'error': 'طريقة غير مدعومة'}, status=405)
    
    try:
        data = json.loads(request.body)
        file_path = data.get('file_path')
        
        if not file_path:
            return JsonResponse({'error': 'مسار الملف مطلوب'}, status=400)
        
        # التحقق من وجود الملف
        if not default_storage.exists(file_path):
            return JsonResponse({'error': 'الملف غير موجود'}, status=404)
        
        # حذف الملف
        default_storage.delete(file_path)
        
        # حذف الصورة المصغرة إن وجدت
        thumbnail_path = f"thumbnails/thumb_{os.path.basename(file_path)}"
        if default_storage.exists(thumbnail_path):
            default_storage.delete(thumbnail_path)
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'error': f'خطأ في حذف الملف: {str(e)}'}, status=500)


@staff_member_required
def editor_link_checker(request):
    """فحص صحة الروابط"""
    if request.method != 'POST':
        return JsonResponse({'error': 'طريقة غير مدعومة'}, status=405)
    
    try:
        data = json.loads(request.body)
        url = data.get('url')
        
        if not url:
            return JsonResponse({'error': 'الرابط مطلوب'}, status=400)
        
        import requests
        from urllib.parse import urlparse
        
        # التحقق من صيغة الرابط
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return JsonResponse({'error': 'صيغة الرابط غير صحيحة'}, status=400)
        
        # فحص الرابط
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            
            return JsonResponse({
                'success': True,
                'status_code': response.status_code,
                'content_type': response.headers.get('content-type', ''),
                'content_length': response.headers.get('content-length', ''),
                'final_url': response.url,
                'is_accessible': response.status_code == 200
            })
            
        except requests.RequestException as e:
            return JsonResponse({
                'success': False,
                'error': f'لا يمكن الوصول للرابط: {str(e)}'
            })
            
    except Exception as e:
        return JsonResponse({'error': f'خطأ في فحص الرابط: {str(e)}'}, status=500)


# ===== JavaScript للمحرر المتقدم =====

WYSIWYG_EDITOR_JS = '''
/* static/js/wysiwyg-editor.js - محرر WYSIWYG المتقدم */

class AdvancedWYSIWYGEditor {
    constructor(textareaId, options = {}) {
        this.textareaId = textareaId;
        this.textarea = document.getElementById(textareaId);
        this.options = {
            height: '400px',
            plugins: ['advlist', 'autolink', 'lists', 'link', 'image', 'charmap', 'preview', 
                     'anchor', 'searchreplace', 'visualblocks', 'code', 'fullscreen',
                     'insertdatetime', 'media', 'table', 'help', 'wordcount', 'directionality'],
            toolbar: `undo redo | bold italic underline strikethrough | fontfamily fontsize blocks | 
                     alignleft aligncenter alignright alignjustify | outdent indent |  numlist bullist | 
                     forecolor backcolor removeformat | pagebreak | charmap emoticons | fullscreen preview save | 
                     insertfile image media template link anchor codesample | ltr rtl | code`,
            menubar: 'file edit view insert format tools table help',
            content_style: 'body { font-family: Tajawal, Arial, sans-serif; font-size: 14px; direction: rtl; }',
            directionality: 'rtl',
            language: 'ar',
            branding: false,
            ...options
        };
        
        this.init();
    }

    init() {
        // تحميل TinyMCE إذا لم يكن محملاً
        if (typeof tinymce === 'undefined') {
            this.loadTinyMCE().then(() => {
                this.initializeEditor();
            });
        } else {
            this.initializeEditor();
        }
    }

    loadTinyMCE() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.tiny.cloud/1/no-api-key/tinymce/6/tinymce.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    initializeEditor() {
        const editorOptions = {
            selector: `#${this.textareaId}`,
            ...this.options,
            setup: (editor) => {
                this.setupCustomButtons(editor);
                this.setupCustomPlugins(editor);
            },
            file_picker_callback: (callback, value, meta) => {
                this.openMediaBrowser(callback, value, meta);
            },
            images_upload_handler: (blobInfo, progress) => {
                return this.uploadImage(blobInfo, progress);
            },
            save_onsavecallback: () => {
                this.saveContent();
            }
        };

        tinymce.init(editorOptions);
    }

    setupCustomButtons(editor) {
        // زر متصفح الوسائط
        editor.ui.registry.addButton('custommedia', {
            text: 'وسائط',
            icon: 'image',
            onAction: () => {
                this.openMediaBrowser((url, meta) => {
                    if (meta.filetype === 'image') {
                        editor.insertContent(`<img src="${url}" alt="${meta.alt || ''}" />`);
                    } else if (meta.filetype === 'media') {
                        editor.insertContent(`<video controls><source src="${url}" /></video>`);
                    }
                });
            }
        });

        // زر إدراج YouTube
        editor.ui.registry.addButton('youtube', {
            text: 'يوتيوب',
            icon: 'embed',
            onAction: () => {
                this.insertYouTubeVideo(editor);
            }
        });

        // زر إدراج SoundCloud
        editor.ui.registry.addButton('soundcloud', {
            text: 'ساوند كلاود',
            icon: 'embed',
            onAction: () => {
                this.insertSoundCloudTrack(editor);
            }
        });

        // زر فحص الروابط
        editor.ui.registry.addButton('linkchecker', {
            text: 'فحص الروابط',
            icon: 'link',
            onAction: () => {
                this.checkLinks(editor);
            }
        });
    }

    setupCustomPlugins(editor) {
        // إضافة مكونات إضافية مخصصة
        editor.on('init', () => {
            console.log('محرر WYSIWYG جاهز');
        });

        // حفظ تلقائي
        editor.on('input', () => {
            clearTimeout(this.autoSaveTimeout);
            this.autoSaveTimeout = setTimeout(() => {
                this.autoSave(editor);
            }, 30000); // حفظ تلقائي كل 30 ثانية
        });
    }

    openMediaBrowser(callback, value, meta) {
        // فتح متصفح الوسائط
        const mediaType = meta.filetype || 'all';
        const browserUrl = `/admin/editor/media-browser/?type=${mediaType}`;
        
        const modal = document.createElement('div');
        modal.className = 'media-browser-modal';
        modal.innerHTML = `
            <div class="modal-overlay" onclick="this.parentElement.remove()">
                <div class="modal-content" onclick="event.stopPropagation()">
                    <div class="modal-header">
                        <h5>اختر ملف وسائط</h5>
                        <button class="btn-close" onclick="this.closest('.media-browser-modal').remove()">
                            <i class="bi bi-x"></i>
                        </button>
                    </div>
                    <div class="modal-body">
                        <iframe src="${browserUrl}" style="width: 100%; height: 500px; border: none;"></iframe>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // استماع لاختيار الملف
        window.addEventListener('message', function(event) {
            if (event.data.type === 'media-selected') {
                callback(event.data.url, {
                    alt: event.data.filename,
                    filetype: event.data.file_type
                });
                modal.remove();
            }
        }, { once: true });
    }

    async uploadImage(blobInfo, progress) {
        const formData = new FormData();
        formData.append('file', blobInfo.blob(), blobInfo.filename());
        
        try {
            const response = await fetch('/admin/editor/upload/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                return result.file_url;
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            throw new Error(`خطأ في رفع الصورة: ${error.message}`);
        }
    }

    insertYouTubeVideo(editor) {
        const url = prompt('أدخل رابط فيديو YouTube:');
        if (url) {
            const videoId = this.extractYouTubeId(url);
            if (videoId) {
                const embedCode = `
                    <div class="youtube-embed">
                        <iframe width="560" height="315" 
                                src="https://www.youtube.com/embed/${videoId}" 
                                frameborder="0" 
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                                allowfullscreen>
                        </iframe>
                    </div>
                `;
                editor.insertContent(embedCode);
            } else {
                alert('رابط YouTube غير صحيح');
            }
        }
    }

    insertSoundCloudTrack(editor) {
        const url = prompt('أدخل رابط مقطع SoundCloud:');
        if (url) {
            const encodedUrl = encodeURIComponent(url);
            const embedCode = `
                <div class="soundcloud-embed">
                    <iframe width="100%" height="166" 
                            scrolling="no" 
                            frameborder="no" 
                            allow="autoplay" 
                            src="https://w.soundcloud.com/player/?url=${encodedUrl}&color=%23ff5500&auto_play=false&hide_related=false&show_comments=true&show_user=true&show_reposts=false&show_teaser=true">
                    </iframe>
                </div>
            `;
            editor.insertContent(embedCode);
        }
    }

    async checkLinks(editor) {
        const content = editor.getContent();
        const links = content.match(/<a[^>]+href=["']([^"']+)["'][^>]*>/g);
        
        if (!links || links.length === 0) {
            alert('لا توجد روابط للفحص');
            return;
        }

        const linkUrls = links.map(link => {
            const match = link.match(/href=["']([^"']+)["']/);
            return match ? match[1] : null;
        }).filter(url => url);

        console.log('فحص الروابط:', linkUrls);
        
        // هنا يمكن إضافة منطق فحص الروابط
        for (const url of linkUrls) {
            try {
                const response = await fetch('/admin/editor/check-link/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify({ url })
                });
                
                const result = await response.json();
                console.log(`رابط ${url}: ${result.is_accessible ? 'يعمل' : 'لا يعمل'}`);
            } catch (error) {
                console.error(`خطأ في فحص الرابط ${url}:`, error);
            }
        }
    }

    extractYouTubeId(url) {
        const patterns = [
            /(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([^&\n?#]+)/,
            /(?:https?:\/\/)?(?:www\.)?youtu\.be\/([^&\n?#]+)/,
            /(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([^&\n?#]+)/
        ];
        
        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match) return match[1];
        }
        
        return null;
    }

    saveContent() {
        // حفظ المحتوى
        const form = this.textarea.closest('form');
        if (form) {
            const formData = new FormData(form);
            
            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            }).then(response => {
                if (response.ok) {
                    this.showNotification('تم حفظ المحتوى بنجاح', 'success');
                } else {
                    this.showNotification('خطأ في حفظ المحتوى', 'error');
                }
            });
        }
    }

    autoSave(editor) {
        const content = editor.getContent();
        
        // حفظ في localStorage كنسخة احتياطية
        localStorage.setItem(`editor_backup_${this.textareaId}`, content);
        
        console.log('تم الحفظ التلقائي');
        this.showNotification('تم الحفظ التلقائي', 'info', 2000);
    }

    showNotification(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `editor-notification ${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="bi bi-${this.getNotificationIcon(type)} me-2"></i>
                ${message}
            </div>
        `;
        
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${this.getNotificationColor(type)};
            color: white;
            padding: 12px 20px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            transition: all 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }

    getNotificationIcon(type) {
        const icons = {
            'success': 'check-circle-fill',
            'error': 'exclamation-triangle-fill',
            'warning': 'exclamation-triangle-fill',
            'info': 'info-circle-fill'
        };
        return icons[type] || 'info-circle-fill';
    }

    getNotificationColor(type) {
        const colors = {
            'success': '#28a745',
            'error': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8'
        };
        return colors[type] || '#17a2b8';
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    destroy() {
        if (typeof tinymce !== 'undefined') {
            tinymce.get(this.textareaId)?.destroy();
        }
        clearTimeout(this.autoSaveTimeout);
    }
}

// تهيئة تلقائية للمحررات
document.addEventListener('DOMContentLoaded', function() {
    // البحث عن textarea مع class "wysiwyg-editor"
    const editors = document.querySelectorAll('textarea.wysiwyg-editor');
    
    editors.forEach(textarea => {
        new AdvancedWYSIWYGEditor(textarea.id, {
            height: textarea.dataset.height || '400px'
        });
    });
});
'''
                    continue
        
        # ترتيب حسب تاريخ التعديل
        files.sort(key=lambda x: x.get('modified_time', ''), reverse=True)
        
        return files
    
    def get_file_info(self, file_path, filename):
        """الحصول على معلومات الملف"""
        try:
            file_url = default_storage.url(file_path)
            file_size = default_storage.size(file_path)
            modified_time = default_storage.get_modified_time(file_path)
            
            # تحديد نوع الملف
            mime_type, _ = mimetypes.guess_type(filename)
            file_type = self.get_file_category(mime_type)
            
            # صورة مصغرة للصور
            thumbnail_url = file_url
            if file_type == 'image':
                thumbnail_url = self.generate_thumbnail(file_path, file_url)
            elif file_type == 'video':
                thumbnail_url = '/static/admin/img/video-thumbnail.png'
            elif file_type == 'audio':
                thumbnail_url = '/static/admin/img/audio-thumbnail.png'
            else:
                thumbnail_url = '/static/admin/img/document-thumbnail.png'
            
            return {
                'filename': filename,
                'file_path': file_path,
                'file_url': file_url,
                'thumbnail_url': thumbnail_url,
                'file_size': self.format_file_size(file_size),
                'file_size_bytes': file_size,
                'type': file_type,
                'mime_type': mime_type,
                'modified_time': modified_time,
                'extension': os.path.splitext(filename)[1].lower()
            }
            
        except Exception as e:
