# content/utils/media_utils.py

import requests
import re
import json
from urllib.parse import urlparse, parse_qs
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import tempfile
import os
from PIL import Image
import subprocess
import logging

logger = logging.getLogger(__name__)


class YouTubeHandler:
    """معالج YouTube المتقدم"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'YOUTUBE_API_KEY', '')
        self.api_base_url = 'https://www.googleapis.com/youtube/v3'
    
    def extract_video_id(self, url):
        """استخراج معرف الفيديو من رابط YouTube"""
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^&\n?#]+)',
            r'(?:https?://)?(?:www\.)?youtu\.be/([^&\n?#]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([^&\n?#]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/v/([^&\n?#]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_video_info(self, video_id):
        """الحصول على معلومات الفيديو من YouTube API"""
        if not self.api_key:
            return self._get_basic_video_info(video_id)
        
        try:
            url = f"{self.api_base_url}/videos"
            params = {
                'part': 'snippet,statistics,contentDetails',
                'id': video_id,
                'key': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('items'):
                return None
            
            item = data['items'][0]
            snippet = item.get('snippet', {})
            statistics = item.get('statistics', {})
            content_details = item.get('contentDetails', {})
            
            return {
                'id': video_id,
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'thumbnail_url': self._get_best_thumbnail(snippet.get('thumbnails', {})),
                'channel_title': snippet.get('channelTitle', ''),
                'duration': self._parse_duration(content_details.get('duration', '')),
                'view_count': int(statistics.get('viewCount', 0)),
                'like_count': int(statistics.get('likeCount', 0)),
                'published_at': snippet.get('publishedAt', ''),
                'embed_url': f"https://www.youtube.com/embed/{video_id}",
                'watch_url': f"https://www.youtube.com/watch?v={video_id}"
            }
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على معلومات YouTube: {e}")
            return self._get_basic_video_info(video_id)
    
    def _get_basic_video_info(self, video_id):
        """معلومات أساسية بدون API"""
        return {
            'id': video_id,
            'title': f'فيديو YouTube {video_id}',
            'description': '',
            'thumbnail_url': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            'embed_url': f"https://www.youtube.com/embed/{video_id}",
            'watch_url': f"https://www.youtube.com/watch?v={video_id}"
        }
    
    def _get_best_thumbnail(self, thumbnails):
        """اختيار أفضل جودة للصورة المصغرة"""
        quality_order = ['maxres', 'high', 'medium', 'default']
        
        for quality in quality_order:
            if quality in thumbnails:
                return thumbnails[quality]['url']
        
        return thumbnails.get('default', {}).get('url', '')
    
    def _parse_duration(self, duration_str):
        """تحويل مدة الفيديو من ISO 8601 إلى ثواني"""
        if not duration_str:
            return 0
        
        # PT4M13S -> 4*60 + 13 = 253 ثانية
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if not match:
            return 0
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds
    
    def download_thumbnail(self, video_id, save_path):
        """تحميل الصورة المصغرة"""
        try:
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            
            response = requests.get(thumbnail_url, timeout=10)
            response.raise_for_status()
            
            # التحقق من أن الصورة موجودة (ليست الصورة الافتراضية للأخطاء)
            if len(response.content) < 1000:  # الصور الافتراضية صغيرة جداً
                thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                response = requests.get(thumbnail_url, timeout=10)
                response.raise_for_status()
            
            # حفظ الصورة
            image_content = ContentFile(response.content)
            filename = f"youtube_thumbnails/{video_id}.jpg"
            
            saved_path = default_storage.save(filename, image_content)
            return saved_path
            
        except Exception as e:
            logger.error(f"خطأ في تحميل صورة YouTube {video_id}: {e}")
            return None


class SoundCloudHandler:
    """معالج SoundCloud المتقدم"""
    
    def __init__(self):
        self.client_id = getattr(settings, 'SOUNDCLOUD_CLIENT_ID', '')
        self.api_base_url = 'https://api.soundcloud.com'
    
    def extract_track_info(self, url):
        """استخراج معلومات المقطع من رابط SoundCloud"""
        try:
            # استخدام resolve API للحصول على معلومات من الرابط
            if not self.client_id:
                return self._get_basic_soundcloud_info(url)
            
            resolve_url = f"{self.api_base_url}/resolve"
            params = {
                'url': url,
                'client_id': self.client_id
            }
            
            response = requests.get(resolve_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'id': data.get('id'),
                'title': data.get('title', ''),
                'description': data.get('description', ''),
                'artwork_url': data.get('artwork_url', '').replace('large', 't500x500') if data.get('artwork_url') else '',
                'user_name': data.get('user', {}).get('username', ''),
                'duration': data.get('duration', 0),  # بالميلي ثانية
                'play_count': data.get('playback_count', 0),
                'like_count': data.get('favoritings_count', 0),
                'permalink_url': data.get('permalink_url', url),
                'stream_url': data.get('stream_url', ''),
                'waveform_url': data.get('waveform_url', ''),
                'created_at': data.get('created_at', '')
            }
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على معلومات SoundCloud: {e}")
            return self._get_basic_soundcloud_info(url)
    
    def _get_basic_soundcloud_info(self, url):
        """معلومات أساسية بدون API"""
        # محاولة استخراج اسم المستخدم والمقطع من الرابط
        parts = url.rstrip('/').split('/')
        if len(parts) >= 2:
            user = parts[-2]
            track = parts[-1]
            title = f"{user} - {track}".replace('-', ' ').title()
        else:
            title = "مقطع SoundCloud"
        
        return {
            'id': None,
            'title': title,
            'description': '',
            'permalink_url': url,
            'embed_url': self._generate_embed_url(url)
        }
    
    def _generate_embed_url(self, url):
        """إنشاء رابط التضمين"""
        encoded_url = requests.utils.quote(url, safe='')
        return f"https://w.soundcloud.com/player/?url={encoded_url}&auto_play=false&hide_related=true&show_comments=false&show_user=true&show_reposts=false&visual=true"
    
    def download_artwork(self, artwork_url, save_path):
        """تحميل صورة المقطع"""
        try:
            if not artwork_url:
                return None
            
            response = requests.get(artwork_url, timeout=10)
            response.raise_for_status()
            
            image_content = ContentFile(response.content)
            filename = f"soundcloud_artworks/{save_path}.jpg"
            
            saved_path = default_storage.save(filename, image_content)
            return saved_path
            
        except Exception as e:
            logger.error(f"خطأ في تحميل صورة SoundCloud: {e}")
            return None


class MediaDownloader:
    """نظام تحميل الوسائط المتقدم"""
    
    @staticmethod
    def download_youtube_video(video_id, quality='best'):
        """تحميل فيديو YouTube (يتطلب youtube-dl أو yt-dlp)"""
        try:
            import yt_dlp
            
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            # إعدادات التحميل
            ydl_opts = {
                'format': f'{quality}[ext=mp4]/best[ext=mp4]/best',
                'outtmpl': os.path.join(settings.MEDIA_ROOT, 'downloads', 'youtube', f'{video_id}.%(ext)s'),
                'writeinfojson': True,
                'writedescription': True,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'ignoreerrors': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                return {
                    'success': True,
                    'file_path': ydl.prepare_filename(info),
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'filesize': info.get('filesize')
                }
                
        except ImportError:
            logger.error("yt-dlp غير مثبت. استخدم: pip install yt-dlp")
            return {'success': False, 'error': 'yt-dlp غير متوفر'}
        except Exception as e:
            logger.error(f"خطأ في تحميل فيديو YouTube: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def download_soundcloud_track(url):
        """تحميل مقطع SoundCloud"""
        try:
            import yt_dlp
            
            ydl_opts = {
                'format': 'best[ext=mp3]/best',
                'outtmpl': os.path.join(settings.MEDIA_ROOT, 'downloads', 'soundcloud', '%(title)s.%(ext)s'),
                'writeinfojson': True,
                'ignoreerrors': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                return {
                    'success': True,
                    'file_path': ydl.prepare_filename(info),
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'filesize': info.get('filesize')
                }
                
        except ImportError:
            logger.error("yt-dlp غير مثبت")
            return {'success': False, 'error': 'yt-dlp غير متوفر'}
        except Exception as e:
            logger.error(f"خطأ في تحميل SoundCloud: {e}")
            return {'success': False, 'error': str(e)}


class MediaProcessor:
    """معالج الوسائط المحلية"""
    
    @staticmethod
    def generate_waveform(audio_file_path, output_path):
        """إنشاء waveform للملفات الصوتية"""
        try:
            # استخدام ffmpeg لإنشاء waveform
            cmd = [
                'ffmpeg',
                '-i', audio_file_path,
                '-filter_complex', '[0:a]aformat=channel_layouts=mono,compand,showwavespic=s=1200x200:colors=blue[v]',
                '-map', '[v]',
                '-frames:v', '1',
                '-y', output_path
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"خطأ في إنشاء waveform: {e}")
            return False
        except FileNotFoundError:
            logger.error("ffmpeg غير مثبت")
            return False
    
    @staticmethod
    def extract_video_thumbnail(video_file_path, output_path, timestamp='00:00:05'):
        """استخراج صورة مصغرة من فيديو"""
        try:
            cmd = [
                'ffmpeg',
                '-i', video_file_path,
                '-ss', timestamp,
                '-vframes', '1',
                '-q:v', '2',
                '-y', output_path
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"خطأ في استخراج الصورة المصغرة: {e}")
            return False
        except FileNotFoundError:
            logger.error("ffmpeg غير مثبت")
            return False
    
    @staticmethod
    def get_media_info(file_path):
        """الحصول على معلومات الوسائط"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"خطأ في الحصول على معلومات الوسائط: {e}")
            return None
        except FileNotFoundError:
            logger.error("ffprobe غير مثبت")
            return None


class PlaylistManager:
    """مدير قوائم التشغيل المتقدم"""
    
    @staticmethod
    def create_m3u_playlist(playlist_items, playlist_title):
        """إنشاء ملف M3U لقائمة التشغيل"""
        content = ['#EXTM3U']
        content.append(f'#PLAYLIST:{playlist_title}')
        
        for item in playlist_items:
            if item.youtube_url:
                content.append(f'#EXTINF:-1,{item.title}')
                content.append(item.youtube_url)
            elif item.soundcloud_url:
                content.append(f'#EXTINF:-1,{item.title}')
                content.append(item.soundcloud_url)
        
        return '\n'.join(content)
    
    @staticmethod
    def get_next_item(current_item, shuffle=False):
        """الحصول على العنصر التالي في القائمة"""
        playlist = current_item.playlist
        items = playlist.playlistitem_set.filter(is_published=True).order_by('order', 'created_at')
        
        if shuffle:
            import random
            items_list = list(items.exclude(id=current_item.id))
            return random.choice(items_list) if items_list else None
        
        try:
            current_index = list(items).index(current_item)
            next_index = current_index + 1
            if next_index < len(items):
                return items[next_index]
        except (ValueError, IndexError):
            pass
        
        return None
    
    @staticmethod
    def get_previous_item(current_item):
        """الحصول على العنصر السابق في القائمة"""
        playlist = current_item.playlist
        items = playlist.playlistitem_set.filter(is_published=True).order_by('order', 'created_at')
        
        try:
            current_index = list(items).index(current_item)
            if current_index > 0:
                return items[current_index - 1]
        except (ValueError, IndexError):
            pass
        
        return None


# إنشاء instances للاستخدام
youtube_handler = YouTubeHandler()
soundcloud_handler = SoundCloudHandler()
media_downloader = MediaDownloader()
media_processor = MediaProcessor()
playlist_manager = PlaylistManager()
