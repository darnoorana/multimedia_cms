/* static/js/main.js - الوظائف التفاعلية للموقع */

// إعدادات عامة
const CONFIG = {
    CSRF_TOKEN: document.querySelector('[name=csrfmiddlewaretoken]')?.value,
    API_BASE_URL: '/api/',
    LANGUAGE: document.documentElement.lang || 'ar',
    IS_RTL: document.documentElement.dir === 'rtl'
};

// وظائف المساعدة (Helper Functions)
const Utils = {
    // الحصول على CSRF Token
    getCSRFToken() {
        return CONFIG.CSRF_TOKEN || document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    },

    // عرض التنبيهات
    showAlert(message, type = 'info', duration = 5000) {
        const alertClass = {
            'success': 'alert-success',
            'error': 'alert-danger', 
            'warning': 'alert-warning',
            'info': 'alert-info'
        }[type] || 'alert-info';

        const alertId = 'alert-' + Date.now();
        const alertHTML = `
            <div id="${alertId}" class="alert ${alertClass} alert-dismissible fade show position-fixed" 
                 style="top: 20px; ${CONFIG.IS_RTL ? 'left' : 'right'}: 20px; z-index: 9999; min-width: 300px;" 
                 role="alert">
                <i class="bi bi-${this.getAlertIcon(type)} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', alertHTML);

        // إزالة التنبيه تلقائياً
        if (duration > 0) {
            setTimeout(() => {
                const alert = document.getElementById(alertId);
                if (alert) {
                    const bsAlert = new bootstrap.Alert(alert);
                    bsAlert.close();
                }
            }, duration);
        }
    },

    getAlertIcon(type) {
        const icons = {
            'success': 'check-circle-fill',
            'error': 'exclamation-triangle-fill',
            'warning': 'exclamation-triangle-fill',
            'info': 'info-circle-fill'
        };
        return icons[type] || 'info-circle-fill';
    },

    // نسخ النص
    async copyToClipboard(text) {
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(text);
                return true;
            } else {
                // Fallback للمتصفحات القديمة
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.left = '-999999px';
                textArea.style.top = '-999999px';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                
                const successful = document.execCommand('copy');
                document.body.removeChild(textArea);
                return successful;
            }
        } catch (err) {
            console.error('فشل في نسخ النص:', err);
            return false;
        }
    },

    // المشاركة الاجتماعية
    shareContent(title, text, url) {
        if (navigator.share && /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
            // استخدام Web Share API للأجهزة المحمولة
            navigator.share({
                title: title,
                text: text,
                url: url
            }).catch(err => console.error('خطأ في المشاركة:', err));
        } else {
            // عرض خيارات المشاركة للأجهزة المكتبية
            this.showShareModal(title, text, url);
        }
    },

    showShareModal(title, text, url) {
        const fullUrl = window.location.origin + url;
        const encodedText = encodeURIComponent(`${text}\n${fullUrl}`);
        
        const shareLinks = {
            whatsapp: `https://wa.me/?text=${encodedText}`,
            facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(fullUrl)}`,
            twitter: `https://twitter.com/intent/tweet?text=${encodedText}`,
            telegram: `https://t.me/share/url?url=${encodeURIComponent(fullUrl)}&text=${encodeURIComponent(text)}`,
            linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(fullUrl)}`
        };

        const modalHTML = `
            <div class="modal fade" id="shareModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">مشاركة المحتوى</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body text-center">
                            <p class="mb-3">اختر طريقة المشاركة:</p>
                            <div class="d-flex justify-content-center gap-3 flex-wrap">
                                <a href="${shareLinks.whatsapp}" target="_blank" class="btn btn-success">
                                    <i class="fab fa-whatsapp me-2"></i>واتساب
                                </a>
                                <a href="${shareLinks.facebook}" target="_blank" class="btn btn-primary">
                                    <i class="fab fa-facebook me-2"></i>فيسبوك
                                </a>
                                <a href="${shareLinks.twitter}" target="_blank" class="btn btn-info">
                                    <i class="fab fa-twitter me-2"></i>تويتر
                                </a>
                                <a href="${shareLinks.telegram}" target="_blank" class="btn btn-primary">
                                    <i class="fab fa-telegram me-2"></i>تيليجرام
                                </a>
                            </div>
                            <hr>
                            <div class="input-group">
                                <input type="text" class="form-control" id="shareUrl" value="${fullUrl}" readonly>
                                <button class="btn btn-outline-secondary" type="button" onclick="MediaPlayer.copyShareUrl()">
                                    <i class="bi bi-copy"></i> نسخ
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // إزالة المودال السابق إن وجد
        const existingModal = document.getElementById('shareModal');
        if (existingModal) {
            existingModal.remove();
        }

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        const shareModal = new bootstrap.Modal(document.getElementById('shareModal'));
        shareModal.show();

        // إزالة المودال بعد الإغلاق
        document.getElementById('shareModal').addEventListener('hidden.bs.modal', function () {
            this.remove();
        });
    },

    // طلبات AJAX
    async makeRequest(url, method = 'GET', data = null) {
        const config = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            }
        };

        if (data) {
            config.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(url, config);
            const responseData = await response.json();
            
            if (!response.ok) {
                throw new Error(responseData.message || 'حدث خطأ في الطلب');
            }
            
            return responseData;
        } catch (error) {
            console.error('خطأ في AJAX:', error);
            throw error;
        }
    }
};

// مشغل الوسائط المتعددة
const MediaPlayer = {
    // تشغيل فيديو YouTube
    playYoutube(videoId, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const embedUrl = `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0&modestbranding=1`;
        container.innerHTML = `
            <div class="media-embed">
                <iframe src="${embedUrl}" 
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                        allowfullscreen>
                </iframe>
            </div>
        `;
        
        this.scrollToPlayer(containerId);
    },

    // تشغيل صوت SoundCloud
    playSoundcloud(trackUrl, containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const encodedUrl = encodeURIComponent(trackUrl);
        const embedUrl = `https://w.soundcloud.com/player/?url=${encodedUrl}&auto_play=true&hide_related=true&show_comments=false&show_user=true&show_reposts=false&visual=true`;
        
        container.innerHTML = `
            <div class="media-embed">
                <iframe src="${embedUrl}"></iframe>
            </div>
        `;
        
        this.scrollToPlayer(containerId);
    },

    // التمرير إلى المشغل
    scrollToPlayer(containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center' 
            });
        }
    },

    // نسخ نص المحتوى
    async copyText(text, buttonElement) {
        const success = await Utils.copyToClipboard(text);
        
        if (success) {
            Utils.showAlert('تم نسخ النص بنجاح!', 'success');
            
            // تغيير النص مؤقتاً
            if (buttonElement) {
                const originalText = buttonElement.innerHTML;
                buttonElement.innerHTML = '<i class="bi bi-check me-2"></i>تم النسخ!';
                buttonElement.classList.add('btn-success');
                
                setTimeout(() => {
                    buttonElement.innerHTML = originalText;
                    buttonElement.classList.remove('btn-success');
                }, 2000);
            }
        } else {
            Utils.showAlert('فشل في نسخ النص. يرجى المحاولة مرة أخرى.', 'error');
        }
    },

    // نسخ رابط المشاركة
    async copyShareUrl() {
        const shareUrlInput = document.getElementById('shareUrl');
        if (shareUrlInput) {
            const success = await Utils.copyToClipboard(shareUrlInput.value);
            if (success) {
                Utils.showAlert('تم نسخ الرابط بنجاح!', 'success');
            } else {
                Utils.showAlert('فشل في نسخ الرابط.', 'error');
            }
        }
    },

    // تسجيل تفاعل المستخدم (AJAX)
    async recordInteraction(type, itemId) {
        try {
            const url = `/ajax/${type}/${itemId}/`;
            await Utils.makeRequest(url, 'POST');
        } catch (error) {
            console.error('فشل في تسجيل التفاعل:', error);
        }
    }
};

// نظام البحث التفاعلي
const SearchSystem = {
    init() {
        const searchInput = document.querySelector('input[name="q"]');
        if (searchInput) {
            // البحث أثناء الكتابة (debounced)
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.performLiveSearch(e.target.value);
                }, 500);
            });
        }
    },

    async performLiveSearch(query) {
        if (query.length < 2) return;

        try {
            const response = await Utils.makeRequest(`/api/search/?q=${encodeURIComponent(query)}`);
            this.displaySearchSuggestions(response.results);
        } catch (error) {
            console.error('خطأ في البحث المباشر:', error);
        }
    },

    displaySearchSuggestions(results) {
        // تنفيذ عرض اقتراحات البحث
        console.log('نتائج البحث:', results);
    }
};

// نظام التعليقات
const CommentSystem = {
    init() {
        // إضافة مستمعي الأحداث لنماذج التعليقات
        document.addEventListener('submit', (e) => {
            if (e.target.classList.contains('comment-form')) {
                e.preventDefault();
                this.submitComment(e.target);
            }
        });
    },

    async submitComment(form) {
        const formData = new FormData(form);
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;

        try {
            // إظهار حالة التحميل
            submitBtn.innerHTML = '<i class="spinner-border spinner-border-sm me-2"></i>جاري الإرسال...';
            submitBtn.disabled = true;

            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': Utils.getCSRFToken()
                }
            });

            const result = await response.json();

            if (response.ok) {
                Utils.showAlert('تم إرسال التعليق بنجاح. سيظهر بعد الموافقة عليه.', 'success');
                form.reset();
            } else {
                Utils.showAlert(result.message || 'حدث خطأ أثناء إرسال التعليق.', 'error');
            }
        } catch (error) {
            console.error('خطأ في إرسال التعليق:', error);
            Utils.showAlert('حدث خطأ في الاتصال. يرجى المحاولة مرة أخرى.', 'error');
        } finally {
            // استعادة الزر
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }
    }
};

// نظام النشرة الإخبارية
const NewsletterSystem = {
    init() {
        // معالجة نماذج الاشتراك في النشرة
        document.addEventListener('submit', (e) => {
            if (e.target.action && e.target.action.includes('newsletter/subscribe')) {
                e.preventDefault();
                this.subscribe(e.target);
            }
        });
    },

    async subscribe(form) {
        const email = form.querySelector('input[name="email"]').value;
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;

        if (!email || !this.validateEmail(email)) {
            Utils.showAlert('يرجى إدخال بريد إلكتروني صحيح.', 'warning');
            return;
        }

        try {
            submitBtn.innerHTML = '<i class="spinner-border spinner-border-sm me-2"></i>جاري الاشتراك...';
            submitBtn.disabled = true;

            const formData = new FormData(form);
            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': Utils.getCSRFToken()
                }
            });

            if (response.ok) {
                Utils.showAlert('تم اشتراكك في النشرة الإخبارية بنجاح!', 'success');
                form.reset();
            } else {
                Utils.showAlert('حدث خطأ أثناء الاشتراك. يرجى المحاولة مرة أخرى.', 'error');
            }
        } catch (error) {
            console.error('خطأ في الاشتراك:', error);
            Utils.showAlert('حدث خطأ في الاتصال. يرجى المحاولة مرة أخرى.', 'error');
        } finally {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }
    },

    validateEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
};

// نظام التحليلات والإحصائيات
const Analytics = {
    init() {
        // تسجيل مشاهدة الصفحة
        this.trackPageView();
        
        // تسجيل التفاعل مع المحتوى
        this.trackContentInteraction();
    },

    trackPageView() {
        // يمكن دمج Google Analytics أو أي نظام تحليلات آخر هنا
        if (typeof gtag !== 'undefined') {
            gtag('config', 'GA_MEASUREMENT_ID', {
                page_title: document.title,
                page_location: window.location.href
            });
        }
    },

    async trackContentInteraction() {
        // تسجيل الوقت المقضي في الصفحة
        let startTime = Date.now();
        let isActive = true;

        // تتبع النشاط
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden' && isActive) {
                const timeSpent = Date.now() - startTime;
                this.sendTimeSpent(timeSpent);
                isActive = false;
            } else if (document.visibilityState === 'visible' && !isActive) {
                startTime = Date.now();
                isActive = true;
            }
        });

        // تسجيل النقرات على الروابط المهمة
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (link && this.isImportantLink(link)) {
                this.trackLinkClick(link);
            }
        });
    },

    isImportantLink(link) {
        return link.href.includes('youtube.com') || 
               link.href.includes('soundcloud.com') ||
               link.classList.contains('action-btn');
    },

    async trackLinkClick(link) {
        try {
            await Utils.makeRequest('/api/analytics/link-click/', 'POST', {
                url: link.href,
                text: link.textContent.trim(),
                page: window.location.pathname
            });
        } catch (error) {
            console.error('خطأ في تسجيل النقرة:', error);
        }
    },

    async sendTimeSpent(timeSpent) {
        if (timeSpent > 5000) { // أكثر من 5 ثوانٍ
            try {
                await Utils.makeRequest('/api/analytics/time-spent/', 'POST', {
                    time_spent: timeSpent,
                    page: window.location.pathname
                });
            } catch (error) {
                console.error('خطأ في تسجيل الوقت:', error);
            }
        }
    }
};

// نظام التحسين التقدمي (Progressive Enhancement)
const ProgressiveEnhancement = {
    init() {
        // تحسين النماذج
        this.enhanceForms();
        
        // تحسين التنقل
        this.enhanceNavigation();
        
        // تحسين الصور
        this.enhanceImages();
    },

    enhanceForms() {
        // إضافة التحقق المباشر للنماذج
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            const inputs = form.querySelectorAll('input[required], textarea[required]');
            inputs.forEach(input => {
                input.addEventListener('blur', () => {
                    this.validateField(input);
                });
            });
        });
    },

    validateField(field) {
        const isValid = field.checkValidity();
        
        // إزالة الرسائل السابقة
        const existingMessage = field.parentNode.querySelector('.field-error');
        if (existingMessage) {
            existingMessage.remove();
        }

        if (!isValid) {
            field.classList.add('is-invalid');
            const errorMessage = document.createElement('div');
            errorMessage.className = 'field-error text-danger small mt-1';
            errorMessage.textContent = field.validationMessage;
            field.parentNode.appendChild(errorMessage);
        } else {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
        }
    },

    enhanceNavigation() {
        // تمييز الرابط النشط في القائمة
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
        
        navLinks.forEach(link => {
            if (link.getAttribute('href') === currentPath) {
                link.classList.add('active');
            }
        });

        // تحسين القائمة المنسدلة للجوال
        const navbarToggler = document.querySelector('.navbar-toggler');
        const navbarCollapse = document.querySelector('.navbar-collapse');
        
        if (navbarToggler && navbarCollapse) {
            // إغلاق القائمة عند النقر على رابط
            navbarCollapse.addEventListener('click', (e) => {
                if (e.target.classList.contains('nav-link')) {
                    const collapse = bootstrap.Collapse.getInstance(navbarCollapse);
                    if (collapse) {
                        collapse.hide();
                    }
                }
            });
        }
    },

    enhanceImages() {
        // التحميل البطيء للصور (Lazy Loading)
        if ('IntersectionObserver' in window) {
            const images = document.querySelectorAll('img[data-src]');
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                        imageObserver.unobserve(img);
                    }
                });
            });

            images.forEach(img => imageObserver.observe(img));
        }

        // تحسين عرض الصور
        const images = document.querySelectorAll('img');
        images.forEach(img => {
            img.addEventListener('error', function() {
                this.src = '/static/images/placeholder.jpg'; // صورة افتراضية
                this.alt = 'صورة غير متوفرة';
            });
        });
    }
};

// نظام الإشعارات المباشرة (إذا كان متاحاً)
const NotificationSystem = {
    init() {
        if ('Notification' in window && 'serviceWorker' in navigator) {
            this.requestPermission();
        }
    },

    async requestPermission() {
        const permission = await Notification.requestPermission();
        if (permission === 'granted') {
            console.log('تم السماح بالإشعارات');
        }
    },

    showNotification(title, options = {}) {
        if (Notification.permission === 'granted') {
            new Notification(title, {
                icon: '/static/images/icon-192.png',
                badge: '/static/images/badge-72.png',
                ...options
            });
        }
    }
};

// تهيئة النظام عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    // تهيئة الأنظمة المختلفة
    SearchSystem.init();
    CommentSystem.init();
    NewsletterSystem.init();
    Analytics.init();
    ProgressiveEnhancement.init();
    NotificationSystem.init();

    // إضافة تأثيرات الحركة
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    if ('IntersectionObserver' in window) {
        const fadeObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                    fadeObserver.unobserve(entry.target);
                }
            });
        }, observerOptions);

        // مراقبة العناصر التي تحتاج تأثير الظهور
        document.querySelectorAll('.playlist-card, .playlist-item, .sidebar-widget').forEach(el => {
            fadeObserver.observe(el);
        });
    }

    // تسجيل Service Worker للتحسين المتقدم
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js').catch(err => {
            console.log('Service Worker registration failed:', err);
        });
    }
});

// دوال مفيدة للاستخدام العام
window.MediaPlayer = MediaPlayer;
window.Utils = Utils;

// معالجة الأخطاء العامة
window.addEventListener('error', function(e) {
    console.error('خطأ JavaScript:', e.error);
    // يمكن إرسال تقرير الخطأ إلى الخادم هنا
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('Promise rejection غير معالج:', e.reason);
    e.preventDefault();
});

// تحسين الأداء - تأخير تحميل الموارد غير الأساسية
setTimeout(() => {
    // تحميل Google Analytics إذا كان متاحاً
    if (typeof gtag !== 'undefined') {
        Analytics.trackPageView();
    }
}, 2000);
