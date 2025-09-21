# content/views/media_views.py

from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse, Http404
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import F
import json
import logging
import os
import mimetypes

from ..models import PlaylistItem, Playlist
from ..utils.media_utils import (
    youtube_handler, soundcloud_handler, media_downloader,
    media_processor, playlist_manager
)

logger = logging.getLogger(__name__)


class YouTubeInfoView(View):
    """الحصول على معلومات فيديو YouTube"""
    
    def get(self, request, video_id):
        try:
            info = youtube_handler.get_video_info(video_id)
            
            if not info:
                return JsonResponse({
                    'success': False,
                    'error': 'فيديو غير موجود أو غير متاح'
                }, status=404)
            
            return JsonResponse({
                'success': True,
                'data': info
            })
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على معلومات YouTube: {e}")
            return JsonResponse({
                'success': False,
                'error': 'حدث خطأ أثناء جلب معلومات الفيديو'
            }, status=500)


class SoundCloudInfoView(View):
    """الحصول على معلومات مقطع SoundCloud"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            url = data.get('url', '').strip()
            
            if not url:
                return JsonResponse({
                    'success': False,
                    'error': 'الرابط مطلوب'
                }, status=400)
            
            info = soundcloud_handler.extract_track_info(url)
            
            return JsonResponse({
                'success': True,
                'data': info
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'بيانات JSON غير صحيحة'
            }, status=400)
        except Exception as e:
            logger.error(f"خطأ في الحصول على معلومات SoundCloud: {e}")
            return JsonResponse({
                'success': False,
                'error': 'حدث خطأ أثناء جلب معلومات المقطع'
            }, status=500)


class MediaDownloadView(LoginRequiredMixin, View):
    """تحميل الوسائط (للمشرفين فقط)"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return JsonResponse({
                'success': False,
                'error': 'غير مسموح لك بتحميل الوسائط'
            }, status=403)
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, item_id):
        try:
            item = get_object_or_404(PlaylistItem, pk=item_id)
            download_type = request.POST.get('type', 'youtube')
            quality = request.POST.get('quality', 'best')
            
            if download_type == 'youtube' and item.youtube_url:
                result = media_downloader.download_youtube_video(
                    item.youtube_video_id, quality
                )
                
                if result['success']:
                    # تحديث إحصائيات التحميل
                    PlaylistItem.objects.filter(pk=item_id).update(
                        youtube_downloads=F('youtube_downloads') + 1
                    )
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'تم تحميل الفيديو بنجاح',
                        'file_info': {
                            'title': result.get('title'),
                            'duration': result.get('duration'),
                            'filesize': result.get('filesize')
                        }
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': result.get('error', 'فشل في تحميل الفيديو')
                    }, status=500)
            
            elif download_type == 'soundcloud' and item.soundcloud_url:
                result = media_downloader.download_soundcloud_track(item.soundcloud_url)
                
                if result['success']:
                    PlaylistItem.objects.filter(pk=item_id).update(
                        soundcloud_downloads=F('soundcloud_downloads') + 1
                    )
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'تم تحميل المقطع الصوتي بنجاح',
                        'file_info': {
                            'title': result.get('title'),
                            'duration': result.get('duration'),
                            'filesize': result.get('filesize')
                        }
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': result.get('error', 'فشل في تحميل المقطع')
                    }, status=500)
            
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'نوع تحميل غير مدعوم أو رابط غير متوفر'
                }, status=400)
                
        except Exception as e:
            logger.error(f"خطأ في تحميل الوسائط: {e}")
            return JsonResponse({
                'success': False,
                'error': 'حدث خطأ أثناء التحميل'
            }, status=500)


class PlaylistNavigationView(View):
    """التنقل في قائمة التشغيل"""
    
    def get(self, request, item_id, direction):
        try:
            current_item = get_object_or_404(PlaylistItem, pk=item_id)
            
            if direction == 'next':
                shuffle = request.GET.get('shuffle', 'false').lower() == 'true'
                next_item = playlist_manager.get_next_item(current_item, shuffle)
                
                if next_item:
                    return JsonResponse({
                        'success': True,
                        'item': {
                            'id': next_item.id,
                            'title': next_item.title,
                            'url': next_item.get_absolute_url(),
                            'has_video': next_item.has_video,
                            'has_audio': next_item.has_audio,
                            'youtube_video_id': next_item.youtube_video_id,
                            'soundcloud_url': next_item.soundcloud_url,
                            'thumbnail': next_item.thumbnail.url if next_item.thumbnail else None
                        }
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'لا يوجد عنصر تالي',
                        'is_end': True
                    })
            
            elif direction == 'previous':
                previous_item = playlist_manager.get_previous_item(current_item)
                
                if previous_item:
                    return JsonResponse({
                        'success': True,
                        'item': {
                            'id': previous_item.id,
                            'title': previous_item.title,
                            'url': previous_item.get_absolute_url(),
                            'has_video': previous_item.has_video,
                            'has_audio': previous_item.has_audio,
                            'youtube_video_id': previous_item.youtube_video_id,
                            'soundcloud_url': previous_item.soundcloud_url,
                            'thumbnail': previous_item.thumbnail.url if previous_item.thumbnail else None
                        }
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'لا يوجد عنصر سابق',
                        'is_start': True
                    })
            
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'اتجاه غير صحيح'
                }, status=400)
                
        except Exception as e:
            logger.error(f"خطأ في التنقل: {e}")
            return JsonResponse({
                'success': False,
                'error': 'حدث خطأ أثناء التنقل'
            }, status=500)


class PlaylistExportView(View):
    """تصدير قائمة التشغيل بصيغ مختلفة"""
    
    def get(self, request, playlist_slug, format_type):
        try:
            playlist = get_object_or_404(
                Playlist,
                slug=playlist_slug,
                is_published=True
            )
            
            items = playlist.playlistitem_set.filter(
                is_published=True
            ).order_by('order', 'created_at')
            
            if format_type == 'm3u':
                content = playlist_manager.create_m3u_playlist(items, playlist.title)
                response = HttpResponse(content, content_type='audio/x-mpegurl')
                response['Content-Disposition'] = f'attachment; filename="{playlist.slug}.m3u"'
                return response
            
            elif format_type == 'json':
                data = {
                    'playlist': {
                        'id': playlist.id,
                        'title': playlist.title,
                        'description': playlist.description,
                        'category': playlist.category.name,
                        'created_at': playlist.created_at.isoformat(),
                        'total_items': items.count()
                    },
                    'items': [
                        {
                            'id': item.id,
                            'title': item.title,
                            'content_type': item.content_type,
                            'youtube_url': item.youtube_url,
                            'soundcloud_url': item.soundcloud_url,
                            'content_text': item.content_text,
                            'thumbnail': item.thumbnail.url if item.thumbnail else None,
                            'views_count': item.views_count,
                            'created_at': item.created_at.isoformat()
                        }
                        for item in items
                    ]
                }
                
                response = JsonResponse(data)
                response['Content-Disposition'] = f'attachment; filename="{playlist.slug}.json"'
                return response
            
            elif format_type == 'rss':
                return self._generate_rss_feed(playlist, items, request)
            
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'صيغة غير مدعومة'
                }, status=400)
                
        except Exception as e:
            logger.error(f"خطأ في التصدير: {e}")
            return JsonResponse({
                'success': False,
                'error': 'حدث خطأ أثناء التصدير'
            }, status=500)
    
    def _generate_rss_feed(self, playlist, items, request):
        """إنشاء RSS feed للقائمة"""
        from django.utils import timezone
        from django.urls import reverse
        
        base_url = request.build_absolute_uri('/').rstrip('/')
        playlist_url = base_url + playlist.get_absolute_url()
        
        rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
<channel>
    <title><![CDATA[{playlist.title}]]></title>
    <description><![CDATA[{playlist.description or 'قائمة تشغيل من منصة المحتوى'}]]></description>
    <link>{playlist_url}</link>
    <language>ar</language>
    <lastBuildDate>{timezone.now().strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>
    <generator>منصة المحتوى المتعدد الوسائط</generator>
    <itunes:author>د. علي بشير أحمد</itunes:author>
    <itunes:category text="Education" />
"""
        
        for item in items:
            item_url = base_url + item.get_absolute_url()
            pub_date = item.created_at.strftime('%a, %d %b %Y %H:%M:%S +0000')
            
            rss_content += f"""
    <item>
        <title><![CDATA[{item.title}]]></title>
        <description><![CDATA[{item.content_text[:200] if item.content_text else item.title}]]></description>
        <link>{item_url}</link>
        <guid>{item_url}</guid>
        <pubDate>{pub_date}</pubDate>
    </item>"""
        
        rss_content += """
</channel>
</rss>"""
        
        response = HttpResponse(rss_content, content_type='application/rss+xml')
        response['Content-Disposition'] = f'attachment; filename="{playlist.slug}.xml"'
        return response


class MediaProxyView(View):
    """بروكسي للوسائط المحمية"""
    
    def get(self, request, item_id, media_type):
        try:
            item = get_object_or_404(PlaylistItem, pk=item_id, is_published=True)
            
            if media_type == 'thumbnail':
                if item.thumbnail:
                    file_path = item.thumbnail.path
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            content = f.read()
                        
                        content_type = mimetypes.guess_type(file_path)[0] or 'image/jpeg'
                        response = HttpResponse(content, content_type=content_type)
                        response['Cache-Control'] = 'max-age=3600'  # cache لساعة
                        return response
                
                # إذا لم تكن هناك صورة، جرب الحصول على صورة من YouTube أو SoundCloud
                if item.youtube_video_id:
                    thumbnail_url = f"https://img.youtube.com/vi/{item.youtube_video_id}/maxresdefault.jpg"
                    try:
                        import requests
                        response = requests.get(thumbnail_url, timeout=5)
                        if response.status_code == 200:
                            http_response = HttpResponse(response.content, content_type='image/jpeg')
                            http_response['Cache-Control'] = 'max-age=3600'
                            return http_response
                    except:
                        pass
                
                # صورة افتراضية
                placeholder_path = os.path.join(settings.STATIC_ROOT, 'images', 'placeholder.jpg')
                if os.path.exists(placeholder_path):
                    with open(placeholder_path, 'rb') as f:
                        content = f.read()
                    return HttpResponse(content, content_type='image/jpeg')
                
                raise Http404("صورة غير موجودة")
            
            else:
                raise Http404("نوع وسائط غير مدعوم")
                
        except Exception as e:
            logger.error(f"خطأ في بروكسي الوسائط: {e}")
            raise Http404("وسائط غير متوفرة")


@method_decorator(csrf_exempt, name='dispatch')
class MediaUploadView(LoginRequiredMixin, View):
    """رفع الوسائط المحلية"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return JsonResponse({
                'success': False,
                'error': 'غير مسموح لك برفع الوسائط'
            }, status=403)
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request):
        try:
            uploaded_file = request.FILES.get('media_file')
            media_type = request.POST.get('media_type', 'auto')  # auto, video, audio, image
            
            if not uploaded_file:
                return JsonResponse({
                    'success': False,
                    'error': 'لم يتم اختيار ملف'
                }, status=400)
            
            # التحقق من نوع الملف
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            
            # أنواع الملفات المدعومة
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
            audio_extensions = ['.mp3', '.wav', '.m4a', '.ogg', '.flac']
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            
            if media_type == 'auto':
                if file_extension in video_extensions:
                    media_type = 'video'
                elif file_extension in audio_extensions:
                    media_type = 'audio'
                elif file_extension in image_extensions:
                    media_type = 'image'
                else:
                    return JsonResponse({
                        'success': False,
                        'error': f'نوع الملف {file_extension} غير مدعوم'
                    }, status=400)
            
            # حفظ الملف
            upload_path = f'uploads/{media_type}s/'
            file_path = default_storage.save(
                upload_path + uploaded_file.name,
                uploaded_file
            )
            
            # معلومات الملف
            file_info = {
                'original_name': uploaded_file.name,
                'file_path': file_path,
                'file_url': default_storage.url(file_path),
                'file_size': uploaded_file.size,
                'media_type': media_type,
                'mime_type': uploaded_file.content_type
            }
            
            # معالجة إضافية حسب نوع الملف
            full_file_path = default_storage.path(file_path)
            
            if media_type == 'video':
                # استخراج صورة مصغرة
                thumbnail_path = upload_path + 'thumbnails/' + os.path.splitext(uploaded_file.name)[0] + '.jpg'
                thumbnail_full_path = default_storage.path(thumbnail_path)
                
                os.makedirs(os.path.dirname(thumbnail_full_path), exist_ok=True)
                
                if media_processor.extract_video_thumbnail(full_file_path, thumbnail_full_path):
                    file_info['thumbnail_url'] = default_storage.url(thumbnail_path)
                
                # معلومات الفيديو
                media_info = media_processor.get_media_info(full_file_path)
                if media_info:
                    file_info['duration'] = media_info.get('format', {}).get('duration')
                    file_info['resolution'] = self._get_video_resolution(media_info)
            
            elif media_type == 'audio':
                # إنشاء waveform
                waveform_path = upload_path + 'waveforms/' + os.path.splitext(uploaded_file.name)[0] + '.png'
                waveform_full_path = default_storage.path(waveform_path)
                
                os.makedirs(os.path.dirname(waveform_full_path), exist_ok=True)
                
                if media_processor.generate_waveform(full_file_path, waveform_full_path):
                    file_info['waveform_url'] = default_storage.url(waveform_path)
                
                # معلومات الصوت
                media_info = media_processor.get_media_info(full_file_path)
                if media_info:
                    file_info['duration'] = media_info.get('format', {}).get('duration')
                    file_info['bitrate'] = media_info.get('format', {}).get('bit_rate')
            
            return JsonResponse({
                'success': True,
                'message': 'تم رفع الملف بنجاح',
                'file_info': file_info
            })
            
        except Exception as e:
            logger.error(f"خطأ في رفع الوسائط: {e}")
            return JsonResponse({
                'success': False,
                'error': 'حدث خطأ أثناء رفع الملف'
            }, status=500)
    
    def _get_video_resolution(self, media_info):
        """استخراج دقة الفيديو"""
        try:
            for stream in media_info.get('streams', []):
                if stream.get('codec_type') == 'video':
                    width = stream.get('width')
                    height = stream.get('height')
                    if width and height:
                        return f"{width}x{height}"
            return None
        except:
            return None


class WaveformGeneratorView(LoginRequiredMixin, View):
    """إنشاء waveform للملفات الصوتية"""
    
    def post(self, request, item_id):
        try:
            if not request.user.is_staff:
                return JsonResponse({
                    'success': False,
                    'error': 'غير مسموح لك بهذه العملية'
                }, status=403)
            
            item = get_object_or_404(PlaylistItem, pk=item_id)
            
            # البحث عن ملف صوتي محلي أو استخدام SoundCloud
            if item.soundcloud_url:
                # محاولة تحميل المقطع أولاً
                download_result = media_downloader.download_soundcloud_track(item.soundcloud_url)
                
                if not download_result['success']:
                    return JsonResponse({
                        'success': False,
                        'error': 'فشل في تحميل المقطع الصوتي'
                    })
                
                audio_file_path = download_result['file_path']
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'لا يوجد ملف صوتي لهذا العنصر'
                })
            
            # إنشاء waveform
            waveform_filename = f"waveforms/{item.id}_{item.slug}.png"
            waveform_path = os.path.join(settings.MEDIA_ROOT, waveform_filename)
            
            os.makedirs(os.path.dirname(waveform_path), exist_ok=True)
            
            if media_processor.generate_waveform(audio_file_path, waveform_path):
                waveform_url = settings.MEDIA_URL + waveform_filename
                
                return JsonResponse({
                    'success': True,
                    'waveform_url': waveform_url,
                    'message': 'تم إنشاء الـ waveform بنجاح'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'فشل في إنشاء الـ waveform'
                })
                
        except Exception as e:
            logger.error(f"خطأ في إنشاء waveform: {e}")
            return JsonResponse({
                'success': False,
                'error': 'حدث خطأ أثناء إنشاء الـ waveform'
            }, status=500)
