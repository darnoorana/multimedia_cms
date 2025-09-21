
# Create your views here.



# blog/views.py - مشاهد المدونة

from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Q, F
from .models import Post

class PostListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Post.objects.filter(is_published=True).select_related('author')
        
        # البحث
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(content__icontains=search_query) |
                Q(tags__icontains=search_query)
            )
        
        return queryset.order_by('-is_featured', '-published_at')

class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_object(self):
        obj = get_object_or_404(Post, slug=self.kwargs['slug'], is_published=True)
        # زيادة عدد المشاهدات
        Post.objects.filter(pk=obj.pk).update(views_count=F('views_count') + 1)
        return obj

