/* static/js/advanced-media-player.js - مشغل الوسائط المتقدم */

class AdvancedMediaPlayer {
    constructor() {
        this.currentItem = null;
        this.playlist = [];
        this.currentIndex = 0;
        this.isPlaying = false;
        this.autoPlay = false;
        this.shuffle = false;
        this.repeat = 'none'; // none, one, all
        this.volume = 1.0;
        this.playerElement = null;
        this.controlsElement = null;
        this.progressElement = null;
        this.timeElement = null;
        this.durationElement = null;
        this.playerType = null; // 'youtube', 'soundcloud', 'local'
        
        // مشغل YouTube
        this.youtubePlayer = null;
        this.youtubeReady = false;
        
        // مشغل محلي للصوت
        this.audioElement = null;
        
        this.init();
    }

    init() {
        this.createPlayerControls();
        this.loadYouTubeAPI();
        this.setupEventListeners();
    }

    createPlayerControls() {
        const controlsHTML = `
            <div class="advanced-media-controls" id="media-controls" style="display: none;">
                <div class="player-header">
                    <div class="current-track-info">
                        <div class="track-thumbnail">
                            <img id="track-thumb" src="" alt="">
                        </div>
                        <div class="track-details">
                            <div class="track-title" id="track-title">لم يتم تحديد مقطع</div>
                            <div class="track-meta" id="track-meta">اختر مقطعاً للتشغيل</div>
                        </div>
                    </div>
                    
                    <div class="player-actions">
                        <button class="btn-playlist" id="btn-show-playlist" title="قائمة التشغيل">
                            <i class="bi bi-list-ul"></i>
                        </button>
                        <button class="btn-close" id="btn-close-player" title="إغلاق المشغل">
                            <i class="bi bi-x-lg"></i>
                        </button>
                    </div>
                </div>

                <div class="player-main">
                    <div class="player-container" id="player-container">
                        <div class="player-placeholder">
                            <i class="bi bi-music-note-beamed display-1"></i>
                            <p>جاهز للتشغيل</p>
                        </div>
                    </div>
                </div>

                <div class="player-controls">
                    <div class="progress-container">
                        <div class="progress-bar" id="progress-bar">
                            <div class="progress-fill" id="progress-fill"></div>
                            <div class="progress-handle" id="progress-handle"></div>
                        </div>
                        <div class="time-display">
                            <span id="current-time">0:00</span>
                            <span id="total-time">0:00</span>
                        </div>
                    </div>

                    <div class="control-buttons">
                        <div class="playback-controls">
                            <button class="btn-control" id="btn-previous" title="السابق">
                                <i class="bi bi-skip-start-fill"></i>
                            </button>
                            <button class="btn-control btn-play-pause" id="btn-play-pause" title="تشغيل/إيقاف">
                                <i class="bi bi-play-fill"></i>
                            </button>
                            <button class="btn-control" id="btn-next" title="التالي">
                                <i class="bi bi-skip-end-fill"></i>
                            </button>
                        </div>

                        <div class="additional-controls">
                            <button class="btn-control" id="btn-shuffle" title="عشوائي">
                                <i class="bi bi-shuffle"></i>
                            </button>
                            <button class="btn-control" id="btn-repeat" title="تكرار">
                                <i class="bi bi-arrow-repeat"></i>
                            </button>
                            <div class="volume-control">
                                <button class="btn-control" id="btn-volume" title="الصوت">
                                    <i class="bi bi-volume-up-fill"></i>
                                </button>
                                <div class="volume-slider">
                                    <input type="range" id="volume-range" min="0" max="100" value="100">
                                </div>
                            </div>
                            <button class="btn-control" id="btn-fullscreen" title="ملء الشاشة">
                                <i class="bi bi-arrows-fullscreen"></i>
                            </button>
                        </div>
                    </div>
                </div>

                <div class="playlist-sidebar" id="playlist-sidebar">
                    <div class="playlist-header">
                        <h6>قائمة التشغيل</h6>
                        <button class="btn-close-sidebar" id="btn-close-sidebar">
                            <i class="bi bi-x"></i>
                        </button>
                    </div>
                    <div class="playlist-content" id="playlist-content">
                        <!-- سيتم ملؤها ديناميكياً -->
                    </div>
                </div>
            </div>
        `;

        // إضافة المشغل إلى الصفحة
        document.body.insertAdjacentHTML('beforeend', controlsHTML);
        
        // حفظ المراجع
        this.controlsElement = document.getElementById('media-controls');
        this.playerElement = document.getElementById('player-container');
        this.progressElement = document.getElementById('progress-fill');
        this.timeElement = document.getElementById('current-time');
        this.durationElement = document.getElementById('total-time');
    }

    setupEventListeners() {
        // أزرار التحكم
        document.getElementById('btn-play-pause').addEventListener('click', () => this.togglePlayPause());
        document.getElementById('btn-previous').addEventListener('click', () => this.previousTrack());
        document.getElementById('btn-next').addEventListener('click', () => this.nextTrack());
        document.getElementById('btn-shuffle').addEventListener('click', () => this.toggleShuffle());
        document.getElementById('btn-repeat').addEventListener('click', () => this.toggleRepeat());
        document.getElementById('btn-close-player').addEventListener('click', () => this.closePlayer());
        document.getElementById('btn-show-playlist').addEventListener('click', () => this.togglePlaylistSidebar());
        document.getElementById('btn-close-sidebar').addEventListener('click', () => this.togglePlaylistSidebar());

        // شريط التقدم
        const progressBar = document.getElementById('progress-bar');
        progressBar.addEventListener('click', (e) => this.seekTo(e));

        // التحكم في الصوت
        document.getElementById('volume-range').addEventListener('input', (e) => {
            this.setVolume(e.target.value / 100);
        });

        // اختصارات لوحة المفاتيح
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));

        // الملء الشاشة
        document.getElementById('btn-fullscreen').addEventListener('click', () => this.toggleFullscreen());
    }

    loadYouTubeAPI() {
        // تحميل YouTube API إذا لم يكن محملاً
        if (!window.YT) {
            const script = document.createElement('script');
            script.src = 'https://www.youtube.com/iframe_api';
            document.head.appendChild(script);
            
            window.onYouTubeIframeAPIReady = () => {
                this.youtubeReady = true;
                console.log('YouTube API جاهز');
            };
        } else {
            this.youtubeReady = true;
        }
    }

    playYouTube(videoId, title, thumbnail) {
        this.showPlayer();
        this.playerType = 'youtube';
        
        this.updateTrackInfo(title, 'YouTube', thumbnail);
        
        if (this.youtubeReady) {
            this.createYouTubePlayer(videoId);
        } else {
            // انتظار تحميل API
            const checkAPI = setInterval(() => {
                if (this.youtubeReady) {
                    clearInterval(checkAPI);
                    this.createYouTubePlayer(videoId);
                }
            }, 100);
        }
    }

    createYouTubePlayer(videoId) {
        this.playerElement.innerHTML = '';
        
        const playerDiv = document.createElement('div');
        playerDiv.id = 'youtube-player';
        this.playerElement.appendChild(playerDiv);

        this.youtubePlayer = new YT.Player('youtube-player', {
            height: '100%',
            width: '100%',
            videoId: videoId,
            playerVars: {
                'autoplay': this.autoPlay ? 1 : 0,
                'controls': 0,
                'rel': 0,
                'showinfo': 0,
                'modestbranding': 1,
                'iv_load_policy': 3
            },
            events: {
                'onReady': (event) => this.onYouTubeReady(event),
                'onStateChange': (event) => this.onYouTubeStateChange(event),
                'onError': (event) => this.onYouTubeError(event)
            }
        });
    }

    onYouTubeReady(event) {
        console.log('YouTube Player جاهز');
        this.youtubePlayer.setVolume(this.volume * 100);
        this.updateDuration();
        
        if (this.autoPlay) {
            this.youtubePlayer.playVideo();
        }
    }

    onYouTubeStateChange(event) {
        const playButton = document.getElementById('btn-play-pause');
        const playIcon = playButton.querySelector('i');
        
        switch (event.data) {
            case YT.PlayerState.PLAYING:
                this.isPlaying = true;
                playIcon.className = 'bi bi-pause-fill';
                this.startProgressUpdate();
                break;
            case YT.PlayerState.PAUSED:
                this.isPlaying = false;
                playIcon.className = 'bi bi-play-fill';
                this.stopProgressUpdate();
                break;
            case YT.PlayerState.ENDED:
                this.onTrackEnded();
                break;
        }
    }

    onYouTubeError(event) {
        console.error('خطأ YouTube:', event.data);
        Utils.showAlert('حدث خطأ في تشغيل الفيديو', 'error');
    }

    playSoundCloud(url, title, thumbnail) {
        this.showPlayer();
        this.playerType = 'soundcloud';
        
        this.updateTrackInfo(title, 'SoundCloud', thumbnail);
        
        const encodedUrl = encodeURIComponent(url);
        const embedUrl = `https://w.soundcloud.com/player/?url=${encodedUrl}&auto_play=${this.autoPlay}&hide_related=true&show_comments=false&show_user=false&show_reposts=false&visual=false`;
        
        this.playerElement.innerHTML = `
            <iframe width="100%" height="100%" 
                    src="${embedUrl}" 
                    frameborder="no" 
                    allow="autoplay">
            </iframe>
        `;
    }

    playLocal(audioSrc, title, thumbnail) {
        this.showPlayer();
        this.playerType = 'local';
        
        this.updateTrackInfo(title, 'محلي', thumbnail);
        
        if (this.audioElement) {
            this.audioElement.pause();
            this.audioElement.removeEventListener('timeupdate', this.updateProgressBound);
            this.audioElement.removeEventListener('ended', this.onTrackEndedBound);
        }
        
        this.audioElement = document.createElement('audio');
        this.audioElement.src = audioSrc;
        this.audioElement.volume = this.volume;
        
        // ربط الأحداث
        this.updateProgressBound = () => this.updateProgress();
        this.onTrackEndedBound = () => this.onTrackEnded();
        
        this.audioElement.addEventListener('loadedmetadata', () => {
            this.updateDuration();
        });
        
        this.audioElement.addEventListener('timeupdate', this.updateProgressBound);
        this.audioElement.addEventListener('ended', this.onTrackEndedBound);
        
        this.playerElement.innerHTML = `
            <div class="audio-visualizer">
                <div class="audio-info">
                    <div class="audio-icon">
                        <i class="bi bi-music-note-beamed display-1"></i>
                    </div>
                    <div class="audio-title">${title}</div>
                </div>
                <div class="audio-waveform" id="audio-waveform">
                    <!-- يمكن إضافة waveform هنا -->
                </div>
            </div>
        `;
        
        if (this.autoPlay) {
            this.audioElement.play();
        }
    }

    updateTrackInfo(title, source, thumbnail) {
        document.getElementById('track-title').textContent = title;
        document.getElementById('track-meta').textContent = source;
        
        const thumbImg = document.getElementById('track-thumb');
        if (thumbnail) {
            thumbImg.src = thumbnail;
            thumbImg.style.display = 'block';
        } else {
            thumbImg.style.display = 'none';
        }
    }

    showPlayer() {
        this.controlsElement.style.display = 'block';
        document.body.classList.add('media-player-open');
        
        // تأثير الظهور
        setTimeout(() => {
            this.controlsElement.classList.add('active');
        }, 10);
    }

    closePlayer() {
        this.stopPlayback();
        
        this.controlsElement.classList.remove('active');
        
        setTimeout(() => {
            this.controlsElement.style.display = 'none';
            document.body.classList.remove('media-player-open');
        }, 300);
    }

    togglePlayPause() {
        if (this.playerType === 'youtube' && this.youtubePlayer) {
            const duration = this.youtubePlayer.getDuration();
            const seekTime = duration * percentage;
            this.youtubePlayer.seekTo(seekTime, true);
        } else if (this.playerType === 'local' && this.audioElement) {
            const seekTime = this.audioElement.duration * percentage;
            this.audioElement.currentTime = seekTime;
        }
    }

    setVolume(volume) {
        this.volume = Math.max(0, Math.min(1, volume));
        
        if (this.playerType === 'youtube' && this.youtubePlayer) {
            this.youtubePlayer.setVolume(this.volume * 100);
        } else if (this.playerType === 'local' && this.audioElement) {
            this.audioElement.volume = this.volume;
        }
        
        // تحديث أيقونة الصوت
        const volumeIcon = document.querySelector('#btn-volume i');
        if (this.volume === 0) {
            volumeIcon.className = 'bi bi-volume-mute-fill';
        } else if (this.volume < 0.5) {
            volumeIcon.className = 'bi bi-volume-down-fill';
        } else {
            volumeIcon.className = 'bi bi-volume-up-fill';
        }
    }

    updateProgress() {
        let currentTime = 0;
        let duration = 0;
        
        if (this.playerType === 'youtube' && this.youtubePlayer) {
            currentTime = this.youtubePlayer.getCurrentTime();
            duration = this.youtubePlayer.getDuration();
        } else if (this.playerType === 'local' && this.audioElement) {
            currentTime = this.audioElement.currentTime;
            duration = this.audioElement.duration || 0;
        }
        
        if (duration > 0) {
            const percentage = (currentTime / duration) * 100;
            this.progressElement.style.width = percentage + '%';
            
            this.timeElement.textContent = this.formatTime(currentTime);
            this.durationElement.textContent = this.formatTime(duration);
        }
    }

    updateDuration() {
        let duration = 0;
        
        if (this.playerType === 'youtube' && this.youtubePlayer) {
            duration = this.youtubePlayer.getDuration();
        } else if (this.playerType === 'local' && this.audioElement) {
            duration = this.audioElement.duration || 0;
        }
        
        this.durationElement.textContent = this.formatTime(duration);
    }

    startProgressUpdate() {
        this.stopProgressUpdate(); // تنظيف أي interval سابق
        this.progressInterval = setInterval(() => {
            this.updateProgress();
        }, 1000);
    }

    stopProgressUpdate() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
    }

    formatTime(seconds) {
        if (!seconds || isNaN(seconds)) return '0:00';
        
        const minutes = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }

    toggleShuffle() {
        this.shuffle = !this.shuffle;
        const shuffleBtn = document.getElementById('btn-shuffle');
        
        if (this.shuffle) {
            shuffleBtn.classList.add('active');
            Utils.showAlert('تم تفعيل التشغيل العشوائي', 'info');
        } else {
            shuffleBtn.classList.remove('active');
            Utils.showAlert('تم إلغاء التشغيل العشوائي', 'info');
        }
    }

    toggleRepeat() {
        const repeatModes = ['none', 'one', 'all'];
        const currentIndex = repeatModes.indexOf(this.repeat);
        this.repeat = repeatModes[(currentIndex + 1) % repeatModes.length];
        
        const repeatBtn = document.getElementById('btn-repeat');
        const repeatIcon = repeatBtn.querySelector('i');
        
        repeatBtn.classList.remove('active', 'repeat-one');
        
        switch (this.repeat) {
            case 'none':
                repeatIcon.className = 'bi bi-arrow-repeat';
                Utils.showAlert('تم إلغاء التكرار', 'info');
                break;
            case 'one':
                repeatIcon.className = 'bi bi-arrow-repeat';
                repeatBtn.classList.add('active', 'repeat-one');
                Utils.showAlert('تكرار المقطع الحالي', 'info');
                break;
            case 'all':
                repeatIcon.className = 'bi bi-arrow-repeat';
                repeatBtn.classList.add('active');
                Utils.showAlert('تكرار كامل القائمة', 'info');
                break;
        }
    }

    previousTrack() {
        if (this.playlist.length === 0) return;
        
        if (this.shuffle) {
            this.currentIndex = Math.floor(Math.random() * this.playlist.length);
        } else {
            this.currentIndex = (this.currentIndex - 1 + this.playlist.length) % this.playlist.length;
        }
        
        this.playCurrentTrack();
    }

    nextTrack() {
        if (this.playlist.length === 0) return;
        
        if (this.shuffle) {
            this.currentIndex = Math.floor(Math.random() * this.playlist.length);
        } else {
            this.currentIndex = (this.currentIndex + 1) % this.playlist.length;
        }
        
        this.playCurrentTrack();
    }

    onTrackEnded() {
        this.isPlaying = false;
        this.updatePlayButton();
        
        switch (this.repeat) {
            case 'one':
                // إعادة تشغيل نفس المقطع
                setTimeout(() => {
                    this.playCurrentTrack();
                }, 1000);
                break;
            case 'all':
                // الانتقال للمقطع التالي
                this.nextTrack();
                break;
            default:
                // إيقاف التشغيل أو الانتقال للتالي إذا كان هناك autoPlay
                if (this.autoPlay && this.currentIndex < this.playlist.length - 1) {
                    this.nextTrack();
                }
                break;
        }
    }

    playCurrentTrack() {
        if (this.playlist.length === 0 || !this.playlist[this.currentIndex]) return;
        
        const track = this.playlist[this.currentIndex];
        this.currentItem = track;
        
        // تحديث قائمة التشغيل المرئية
        this.updatePlaylistUI();
        
        // تشغيل المقطع
        if (track.youtube_video_id) {
            this.playYouTube(track.youtube_video_id, track.title, track.thumbnail);
        } else if (track.soundcloud_url) {
            this.playSoundCloud(track.soundcloud_url, track.title, track.thumbnail);
        } else if (track.audio_url) {
            this.playLocal(track.audio_url, track.title, track.thumbnail);
        }
        
        // تسجيل المشاهدة
        if (track.id) {
            this.recordView(track.id);
        }
    }

    loadPlaylist(items, startIndex = 0) {
        this.playlist = items;
        this.currentIndex = startIndex;
        this.updatePlaylistUI();
        
        if (items.length > 0) {
            this.playCurrentTrack();
        }
    }

    updatePlaylistUI() {
        const playlistContent = document.getElementById('playlist-content');
        
        if (this.playlist.length === 0) {
            playlistContent.innerHTML = '<div class="playlist-empty">لا توجد مقاطع في القائمة</div>';
            return;
        }
        
        playlistContent.innerHTML = '';
        
        this.playlist.forEach((track, index) => {
            const trackElement = document.createElement('div');
            trackElement.className = `playlist-item ${index === this.currentIndex ? 'active' : ''}`;
            trackElement.innerHTML = `
                <div class="track-thumbnail">
                    ${track.thumbnail ? 
                        `<img src="${track.thumbnail}" alt="${track.title}">` : 
                        '<i class="bi bi-music-note"></i>'
                    }
                </div>
                <div class="track-info">
                    <div class="track-title">${track.title}</div>
                    <div class="track-meta">${this.getTrackTypeIcon(track)} ${track.duration || ''}</div>
                </div>
                <div class="track-actions">
                    <button class="btn-track-play" data-index="${index}">
                        <i class="bi bi-play-fill"></i>
                    </button>
                </div>
            `;
            
            // إضافة مستمع الحدث
            trackElement.querySelector('.btn-track-play').addEventListener('click', () => {
                this.currentIndex = index;
                this.playCurrentTrack();
            });
            
            trackElement.addEventListener('dblclick', () => {
                this.currentIndex = index;
                this.playCurrentTrack();
            });
            
            playlistContent.appendChild(trackElement);
        });
    }

    getTrackTypeIcon(track) {
        if (track.youtube_video_id) return '<i class="fab fa-youtube text-danger"></i>';
        if (track.soundcloud_url) return '<i class="fab fa-soundcloud text-warning"></i>';
        if (track.audio_url) return '<i class="bi bi-file-music"></i>';
        return '<i class="bi bi-music-note"></i>';
    }

    togglePlaylistSidebar() {
        const sidebar = document.getElementById('playlist-sidebar');
        sidebar.classList.toggle('open');
    }

    toggleFullscreen() {
        if (!document.fullscreenElement) {
            this.controlsElement.requestFullscreen?.() ||
            this.controlsElement.webkitRequestFullscreen?.() ||
            this.controlsElement.msRequestFullscreen?.();
        } else {
            document.exitFullscreen?.() ||
            document.webkitExitFullscreen?.() ||
            document.msExitFullscreen?.();
        }
    }

    handleKeyboard(event) {
        // التحقق من أن المشغل مفتوح
        if (!this.controlsElement || this.controlsElement.style.display === 'none') return;
        
        // تجاهل الاختصارات إذا كان هناك input مُركز عليه
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') return;
        
        switch (event.code) {
            case 'Space':
                event.preventDefault();
                this.togglePlayPause();
                break;
            case 'ArrowLeft':
                event.preventDefault();
                this.previousTrack();
                break;
            case 'ArrowRight':
                event.preventDefault();
                this.nextTrack();
                break;
            case 'ArrowUp':
                event.preventDefault();
                this.setVolume(Math.min(1, this.volume + 0.1));
                document.getElementById('volume-range').value = this.volume * 100;
                break;
            case 'ArrowDown':
                event.preventDefault();
                this.setVolume(Math.max(0, this.volume - 0.1));
                document.getElementById('volume-range').value = this.volume * 100;
                break;
            case 'KeyM':
                event.preventDefault();
                this.setVolume(this.volume === 0 ? this.previousVolume || 1 : 0);
                if (this.volume === 0) {
                    this.previousVolume = this.volume;
                }
                document.getElementById('volume-range').value = this.volume * 100;
                break;
            case 'KeyF':
                event.preventDefault();
                this.toggleFullscreen();
                break;
            case 'KeyS':
                event.preventDefault();
                this.toggleShuffle();
                break;
            case 'KeyR':
                event.preventDefault();
                this.toggleRepeat();
                break;
            case 'Escape':
                event.preventDefault();
                if (document.fullscreenElement) {
                    this.toggleFullscreen();
                } else {
                    this.closePlayer();
                }
                break;
        }
    }

    async recordView(itemId) {
        try {
            await fetch(`/ajax/increment-view/${itemId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': Utils.getCSRFToken()
                }
            });
        } catch (error) {
            console.error('خطأ في تسجيل المشاهدة:', error);
        }
    }

    // دوال مساعدة للتكامل مع الصفحة
    static playYouTubeVideo(videoId, title = '', thumbnail = '') {
        if (!window.advancedPlayer) {
            window.advancedPlayer = new AdvancedMediaPlayer();
        }
        
        window.advancedPlayer.autoPlay = true;
        window.advancedPlayer.playYouTube(videoId, title, thumbnail);
    }

    static playSoundCloudTrack(url, title = '', thumbnail = '') {
        if (!window.advancedPlayer) {
            window.advancedPlayer = new AdvancedMediaPlayer();
        }
        
        window.advancedPlayer.autoPlay = true;
        window.advancedPlayer.playSoundCloud(url, title, thumbnail);
    }

    static playLocalAudio(audioSrc, title = '', thumbnail = '') {
        if (!window.advancedPlayer) {
            window.advancedPlayer = new AdvancedMediaPlayer();
        }
        
        window.advancedPlayer.autoPlay = true;
        window.advancedPlayer.playLocal(audioSrc, title, thumbnail);
    }

    static loadPlaylist(items, startIndex = 0) {
        if (!window.advancedPlayer) {
            window.advancedPlayer = new AdvancedMediaPlayer();
        }
        
        window.advancedPlayer.autoPlay = true;
        window.advancedPlayer.loadPlaylist(items, startIndex);
    }
}

// تهيئة المشغل عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    // إنشاء مشغل عمومي
    window.advancedPlayer = new AdvancedMediaPlayer();
    
    // ربط الدوال مع MediaPlayer الأصلي للتوافق
    const originalMediaPlayer = window.MediaPlayer;
    
    window.MediaPlayer = {
        ...originalMediaPlayer,
        
        playYoutube: (videoId, containerId, title = '', thumbnail = '') => {
            if (containerId === 'main-player' || containerId.startsWith('advanced-')) {
                AdvancedMediaPlayer.playYouTubeVideo(videoId, title, thumbnail);
            } else {
                // استخدام الطريقة الأصلية للتشغيل المدمج
                originalMediaPlayer.playYoutube(videoId, containerId);
            }
        },
        
        playSoundcloud: (trackUrl, containerId, title = '', thumbnail = '') => {
            if (containerId === 'main-player' || containerId.startsWith('advanced-')) {
                AdvancedMediaPlayer.playSoundCloudTrack(trackUrl, title, thumbnail);
            } else {
                // استخدام الطريقة الأصلية
                originalMediaPlayer.playSoundcloud(trackUrl, containerId);
            }
        },
        
        // الاحتفاظ بالوظائف الأصلية
        copyText: originalMediaPlayer.copyText,
        recordInteraction: originalMediaPlayer.recordInteraction,
        scrollToPlayer: originalMediaPlayer.scrollToPlayer
    };
});

// CSS للمشغل المتقدم
const advancedPlayerCSS = `
<style>
.advanced-media-controls {
    position: fixed;
    bottom: -100%;
    left: 0;
    right: 0;
    height: 400px;
    background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
    color: white;
    z-index: 10000;
    transition: all 0.3s ease;
    border-top: 2px solid #007bff;
    box-shadow: 0 -10px 30px rgba(0,0,0,0.3);
}

.advanced-media-controls.active {
    bottom: 0;
}

.advanced-media-controls .player-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 15px 20px;
    border-bottom: 1px solid #444;
}

.advanced-media-controls .current-track-info {
    display: flex;
    align-items: center;
    gap: 15px;
}

.advanced-media-controls .track-thumbnail img {
    width: 50px;
    height: 50px;
    border-radius: 8px;
    object-fit: cover;
}

.advanced-media-controls .track-title {
    font-weight: 600;
    font-size: 1.1rem;
    margin-bottom: 2px;
}

.advanced-media-controls .track-meta {
    color: #aaa;
    font-size: 0.9rem;
}

.advanced-media-controls .player-actions {
    display: flex;
    gap: 10px;
}

.advanced-media-controls .btn-playlist,
.advanced-media-controls .btn-close {
    background: none;
    border: none;
    color: #aaa;
    font-size: 1.2rem;
    padding: 8px;
    border-radius: 6px;
    transition: all 0.2s;
}

.advanced-media-controls .btn-playlist:hover,
.advanced-media-controls .btn-close:hover {
    background: #444;
    color: white;
}

.advanced-media-controls .player-main {
    height: 200px;
    position: relative;
    background: #000;
}

.advanced-media-controls .player-container {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
}

.advanced-media-controls .player-placeholder {
    text-align: center;
    color: #666;
}

.advanced-media-controls .player-controls {
    padding: 20px;
    background: #222;
}

.advanced-media-controls .progress-container {
    margin-bottom: 15px;
}

.advanced-media-controls .progress-bar {
    height: 6px;
    background: #444;
    border-radius: 3px;
    cursor: pointer;
    position: relative;
}

.advanced-media-controls .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #007bff, #0056b3);
    border-radius: 3px;
    transition: width 0.1s ease;
    width: 0%;
}

.advanced-media-controls .time-display {
    display: flex;
    justify-content: space-between;
    font-size: 0.9rem;
    color: #aaa;
    margin-top: 5px;
}

.advanced-media-controls .control-buttons {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.advanced-media-controls .playback-controls {
    display: flex;
    gap: 10px;
    align-items: center;
}

.advanced-media-controls .btn-control {
    background: none;
    border: none;
    color: white;
    font-size: 1.2rem;
    padding: 10px;
    border-radius: 50%;
    transition: all 0.2s;
    width: 45px;
    height: 45px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.advanced-media-controls .btn-play-pause {
    background: #007bff;
    font-size: 1.4rem;
    width: 55px;
    height: 55px;
}

.advanced-media-controls .btn-control:hover {
    background: #444;
    transform: scale(1.1);
}

.advanced-media-controls .btn-play-pause:hover {
    background: #0056b3;
}

.advanced-media-controls .btn-control.active {
    background: #007bff;
    color: white;
}

.advanced-media-controls .additional-controls {
    display: flex;
    gap: 5px;
    align-items: center;
}

.advanced-media-controls .volume-control {
    display: flex;
    align-items: center;
    gap: 10px;
}

.advanced-media-controls .volume-slider {
    width: 80px;
}

.advanced-media-controls .volume-slider input {
    width: 100%;
    height: 4px;
    background: #444;
    outline: none;
    border-radius: 2px;
}

.advanced-media-controls .playlist-sidebar {
    position: absolute;
    top: 0;
    right: -300px;
    width: 300px;
    height: 100%;
    background: #333;
    transition: right 0.3s ease;
    border-left: 1px solid #444;
}

.advanced-media-controls .playlist-sidebar.open {
    right: 0;
}

.advanced-media-controls .playlist-header {
    padding: 15px 20px;
    border-bottom: 1px solid #444;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.advanced-media-controls .playlist-content {
    height: calc(100% - 60px);
    overflow-y: auto;
    padding: 10px;
}

.advanced-media-controls .playlist-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.2s;
    margin-bottom: 5px;
}

.advanced-media-controls .playlist-item:hover {
    background: #444;
}

.advanced-media-controls .playlist-item.active {
    background: #007bff;
}

.advanced-media-controls .playlist-item .track-thumbnail {
    width: 40px;
    height: 40px;
    border-radius: 6px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #444;
}

.advanced-media-controls .playlist-item .track-thumbnail img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.advanced-media-controls .playlist-item .track-info {
    flex: 1;
    min-width: 0;
}

.advanced-media-controls .playlist-item .track-title {
    font-size: 0.9rem;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.advanced-media-controls .playlist-item .track-meta {
    font-size: 0.8rem;
    color: #aaa;
    display: flex;
    align-items: center;
    gap: 5px;
}

.advanced-media-controls .btn-track-play {
    background: none;
    border: none;
    color: #aaa;
    font-size: 1rem;
    padding: 5px;
    border-radius: 4px;
    transition: all 0.2s;
}

.advanced-media-controls .btn-track-play:hover {
    background: #555;
    color: white;
}

.advanced-media-controls .audio-visualizer {
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    background: linear-gradient(135deg, #1a1a2e, #16213e);
}

.advanced-media-controls .audio-info {
    margin-bottom: 20px;
}

.advanced-media-controls .audio-icon {
    margin-bottom: 15px;
    opacity: 0.7;
}

.advanced-media-controls .audio-title {
    font-size: 1.2rem;
    font-weight: 600;
}

body.media-player-open {
    padding-bottom: 400px;
    transition: padding-bottom 0.3s ease;
}

/* تجاوب للشاشات الصغيرة */
@media (max-width: 768px) {
    .advanced-media-controls {
        height: 350px;
    }
    
    .advanced-media-controls .player-main {
        height: 150px;
    }
    
    .advanced-media-controls .additional-controls {
        display: none;
    }
    
    .advanced-media-controls .playlist-sidebar {
        width: 100%;
        right: -100%;
    }
    
    body.media-player-open {
        padding-bottom: 350px;
    }
}
</style>
`;

// إضافة الـ CSS إلى الصفحة
document.head.insertAdjacentHTML('beforeend', advancedPlayerCSS);youtubePlayer) {
            if (this.isPlaying) {
                this.youtubePlayer.pauseVideo();
            } else {
                this.youtubePlayer.playVideo();
            }
        } else if (this.playerType === 'local' && this.audioElement) {
            if (this.isPlaying) {
                this.audioElement.pause();
                this.isPlaying = false;
            } else {
                this.audioElement.play();
                this.isPlaying = true;
            }
            
            this.updatePlayButton();
        }
    }

    updatePlayButton() {
        const playButton = document.getElementById('btn-play-pause');
        const playIcon = playButton.querySelector('i');
        
        if (this.isPlaying) {
            playIcon.className = 'bi bi-pause-fill';
        } else {
            playIcon.className = 'bi bi-play-fill';
        }
    }

    stopPlayback() {
        if (this.playerType === 'youtube' && this.youtubePlayer) {
            this.youtubePlayer.stopVideo();
        } else if (this.playerType === 'local' && this.audioElement) {
            this.audioElement.pause();
            this.audioElement.currentTime = 0;
        }
        
        this.isPlaying = false;
        this.stopProgressUpdate();
        this.updatePlayButton();
    }

    seekTo(event) {
        const progressBar = event.currentTarget;
        const rect = progressBar.getBoundingClientRect();
        const percentage = (event.clientX - rect.left) / rect.width;
        
        if (this.playerType === 'youtube' && this.