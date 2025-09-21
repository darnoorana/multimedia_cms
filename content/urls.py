# content/urls.py

from django.urls import path
from django.utils.translation import gettext_lazy as _
from . import views

app_name = 'content'

urlpatterns = [
    # قوائم التشغيل
    path('', views.PlaylistListView.as_view(), name='playlist_list'),
    path(_('category/<slug:category_slug>/'), views.CategoryPlaylistsView.as_view(), name='category_playlists'),
    path(_('playlist/<slug:slug>/'), views.PlaylistDetailView.as_view(), name='playlist_detail'),
    
    # عناصر قوائم التشغيل
    path(_('playlist/<slug:playlist_slug>/<slug:item_slug>/'), 
         views.PlaylistItemDetailView.as_view(), name='item_detail'),
    
    # العلامات
    path(_('tag/<slug:tag_slug>/'), views.TagView.as_view(), name='tag_items'),
    path(_('tags/'), views.TagListView.as_view(), name='tag_list'),
    
    # التفاعل مع المحتوى
    path(_('item/<int:item_id>/download-youtube/'), 
         views.YoutubeDownloadView.as_view(), name='youtube_download'),
    path(_('item/<int:item_id>/download-soundcloud/'), 
         views.SoundcloudDownloadView.as_view(), name='soundcloud_download'),
    path(_('item/<int:item_id>/copy-text/'), 
         views.CopyTextView.as_view(), name='copy_text'),
    path(_('item/<int:item_id>/share/'), 
         views.ShareView.as_view(), name='share'),
    
    # التعليقات
    path(_('item/<int:item_id>/add-comment/'), 
         views.AddCommentView.as_view(), name='add_comment'),
    path(_('comment/<int:comment_id>/delete/'), 
         views.DeleteCommentView.as_view(), name='delete_comment'),
         
    # AJAX Views (للتفاعل السريع)
    path('ajax/increment-view/<int:item_id>/', 
         views.IncrementViewAjax.as_view(), name='increment_view_ajax'),
    path('ajax/toggle-like/<int:item_id>/', 
         views.ToggleLikeAjax.as_view(), name='toggle_like_ajax'),
]
