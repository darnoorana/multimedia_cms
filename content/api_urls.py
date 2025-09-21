
from django.urls import path
from .views import media_views

urlpatterns = [
    # API للوسائط
    path('youtube-info/<str:video_id>/', media_views.YouTubeInfoView.as_view()),
    path('soundcloud-info/', media_views.SoundCloudInfoView.as_view()),
    path('media-download/<int:item_id>/', media_views.MediaDownloadView.as_view()),
    path('media-upload/', media_views.MediaUploadView.as_view()),
    path('generate-waveform/<int:item_id>/', media_views.WaveformGeneratorView.as_view()),
    
    # API للتنقل والتصدير
    path('playlist-nav/<int:item_id>/<str:direction>/', media_views.PlaylistNavigationView.as_view()),
    path('media-proxy/<int:item_id>/<str:media_type>/', media_views.MediaProxyView.as_view()),
]
